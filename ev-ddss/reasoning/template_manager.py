"""Template Manager — loads and renders Jinja2 prompt templates.

Templates are loaded from the configured template directory and cached
in memory.  Each intent type maps to a separate template file.

All templates are editable without modifying Python code.
"""

import re
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError

from backend.logger import logger


class TemplateManager:
    """Manages Jinja2 prompt templates for the reasoning engine.

    Parameters
    ----------
    template_dir : str or Path
        Directory containing ``.jinja`` template files.
    cache_enabled : bool
        Whether to cache loaded templates (default True).
    """

    def __init__(
        self,
        template_dir: Path,
        cache_enabled: bool = True,
    ) -> None:
        self._template_dir = Path(template_dir).resolve()
        self._cache_enabled = cache_enabled

        if not self._template_dir.exists():
            logger.warning("TemplateManager: template directory does not exist: {}", self._template_dir)

        self._env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            enable_async=False,
            cache_size=50 if cache_enabled else 0,
        )
        self._loaded: Dict[str, bool] = {}
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}

    # ── Public API ──────────────────────────────

    @property
    def template_dir(self) -> Path:
        return self._template_dir

    def list_templates(self) -> list:
        if not self._template_dir.exists():
            return []
        return sorted(f.name for f in self._template_dir.glob("*.jinja") if f.is_file())

    def render(self, template_name: str, **variables: Any) -> str:
        """Render a template with the given variables.

        Parameters
        ----------
        template_name : str
            Filename of the Jinja2 template (e.g. ``"error_code.jinja"``).
        **variables
            Template variables (context, query, intent, etc.).

        Returns
        -------
        str
            Rendered prompt text.

        Raises
        ------
        FileNotFoundError
            If the template file does not exist.
        ValueError
            If template syntax is invalid.
        """
        try:
            template = self._env.get_template(template_name)
            rendered = template.render(**variables)
            self._loaded[template_name] = True
            return rendered
        except TemplateNotFound:
            raise FileNotFoundError(
                f"Template '{template_name}' not found in {self._template_dir}. "
                f"Available: {', '.join(self.list_templates()) or '(none)'}"
            )
        except TemplateSyntaxError as exc:
            raise ValueError(f"Template syntax error in '{template_name}' line {exc.lineno}: {exc.message}")
        except Exception as exc:
            raise RuntimeError(f"Failed to render template '{template_name}': {exc}")

    def get_metadata(self, template_name: str) -> Dict[str, Any]:
        """Parse and return metadata from a template file.

        Metadata is read from the template's first line as a YAML-like
        frontmatter or a structured comment::

            {# template_name: error_code, template_version: 1.0.0, ... #}

        Returns a dict with defaults for missing fields.
        """
        if template_name in self._metadata_cache:
            return dict(self._metadata_cache[template_name])

        defaults: Dict[str, Any] = {
            "template_name": template_name,
            "template_version": "1.0.0",
            "description": "",
            "supported_intents": [],
        }

        path = self._template_dir / template_name
        if not path.exists():
            return defaults

        try:
            raw = path.read_text("utf-8")
        except OSError:
            return defaults

        meta = self._parse_frontmatter(raw)
        defaults.update(meta)
        self._metadata_cache[template_name] = dict(defaults)
        return defaults

    def exists(self, template_name: str) -> bool:
        return (self._template_dir / template_name).is_file()

    def health_check(self) -> Dict[str, Any]:
        templates = self.list_templates()
        return {
            "directory": str(self._template_dir),
            "exists": self._template_dir.exists(),
            "template_count": len(templates),
            "templates": templates,
            "healthy": self._template_dir.exists() and len(templates) > 0,
        }

    # ── Metadata parsing ────────────────────────

    @staticmethod
    def _parse_frontmatter(raw: str) -> Dict[str, Any]:
        """Parse metadata from template frontmatter.

        Supports two formats:

        1. HTML/XML comment on first line:
           ``<!-- template_name: error_code, version: 1.0.0 -->``

        2. Jinja comment on first line:
           ``{# template_name: error_code, version: 1.0.0 #}``
        """
        meta: Dict[str, Any] = {}
        first_line = raw.lstrip().split("\n", 1)[0].strip()

        patterns = [
            r"<!--\s*(.*?)\s*-->",
            r"{#\s*(.*?)\s*#}",
        ]

        match = None
        for pat in patterns:
            m = re.match(pat, first_line)
            if m:
                match = m.group(1)
                break

        if not match:
            return meta

        for part in match.split(","):
            part = part.strip()
            if ":" not in part:
                continue
            key, _, value = part.partition(":")
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()

            if key == "supported_intents":
                meta[key] = [v.strip() for v in value.split("/")]
            elif key == "template_version":
                meta[key] = value
            elif key in ("template_name", "description"):
                meta[key] = value
            else:
                meta[key] = value

        return meta
