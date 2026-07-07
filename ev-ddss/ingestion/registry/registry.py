"""Parser registry that maps file extensions to parser classes.

Registration is explicit — parsers register themselves for the
extensions they handle. Lookup is O(1) via a dict. No if/else chains.
"""

from typing import Dict, List, Optional, Type

from backend.logger import logger
from ingestion.base.parser import BaseParser


class ParserRegistry:
    """Maps file extensions to parser classes.

    Extensions are stored in lowercase ('.pdf', '.xlsx', etc.).
    Registration is done via:
        registry.register(PDFParser)
        parser = registry.lookup('.pdf')  # returns PDFParser instance
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Type[BaseParser]] = {}
        self._instances: Dict[str, BaseParser] = {}

    def register(self, parser_cls: Type[BaseParser]) -> None:
        """Register a parser class for all its supported extensions.

        Args:
            parser_cls: A concrete BaseParser subclass. Its
                supported_extensions property determines which
                extensions it handles.
        """
        instantiated = parser_cls()
        for ext in instantiated.supported_extensions:
            ext_lower = ext.lower()
            if ext_lower in self._registry:
                existing = self._registry[ext_lower].__name__
                logger.warning(
                    "Overriding parser for '{}': {} -> {}",
                    ext_lower,
                    existing,
                    parser_cls.__name__,
                )
            self._registry[ext_lower] = parser_cls
            self._instances[ext_lower] = instantiated
        logger.debug(
            "Registered {} (extensions: {})",
            parser_cls.__name__,
            instantiated.supported_extensions,
        )

    def lookup(self, extension: str) -> Optional[BaseParser]:
        """Find the parser for a given file extension.

        Args:
            extension: File extension including the dot (e.g. '.pdf').

        Returns:
            An instance of the matching parser, or None if no parser
            is registered for this extension.
        """
        ext_lower = extension.lower()
        instance = self._instances.get(ext_lower)
        if instance is None:
            logger.debug("No parser registered for extension '{}'", ext_lower)
        return instance

    @property
    def supported_extensions(self) -> List[str]:
        """All registered extensions."""
        return list(self._registry.keys())

    @property
    def parser_names(self) -> List[str]:
        """Human-readable names of all registered parsers."""
        return list({cls.__name__ for cls in self._registry.values()})

    def __repr__(self) -> str:
        return f"ParserRegistry({len(self._registry)} extensions, {len(self.parser_names)} parsers)"
