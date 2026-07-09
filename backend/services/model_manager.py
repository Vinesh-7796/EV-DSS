"""Model Manager Service — handles runtime model discovery, downloading/pulling
via Ollama, recommendation logic based on hardware, and active model switching.
"""

import os
import subprocess
import httpx
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent / "ev-ddss"
_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.yaml"

class ModelManager:
    """Handles Ollama model detection, downloads/pulls, and configuration switching."""

    def __init__(self, ollama_url: str = "http://localhost:11434") -> None:
        self.ollama_url = ollama_url

    def get_hardware_info(self) -> Dict[str, Any]:
        """Return target hardware profile configuration."""
        return {
            "ram_gb": 16,
            "gpu_vram_gb": 4.0,
            "gpu_name": "RTX 3050 Ti Laptop GPU",
            "recommendation": "Models <= 8B parameters are supported. 3B models are recommended for optimal speed and VRAM footprint."
        }

    def list_installed_models(self) -> List[Dict[str, Any]]:
        """Run `ollama list` or call the local API to get installed models."""
        try:
            # Try API first as it's cleaner
            resp = httpx.get(f"{self.ollama_url}/api/tags", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("models", []):
                    name = m.get("name", "")
                    size_bytes = m.get("size", 0)
                    size_gb = size_bytes / (1024 ** 3)
                    details = m.get("details", {})
                    quant = details.get("quantization_level", "Unknown")
                    family = details.get("family", "")
                    modified = m.get("modified_at", "")
                    
                    is_recommended = self._is_model_recommended(name, size_gb)
                    
                    models.append({
                        "name": name,
                        "size_bytes": size_bytes,
                        "size_formatted": f"{size_gb:.2f} GB",
                        "quantization": quant,
                        "family": family,
                        "modified_date": modified,
                        "is_recommended": is_recommended
                    })
                return models
        except Exception as exc:
            logger.warning("Failed to connect to Ollama API for model listing: {}. Falling back to CLI.", exc)

        # Fallback to CLI
        try:
            res = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
            lines = res.stdout.strip().split("\n")
            if len(lines) <= 1:
                return []
            
            models = []
            # First line is header: NAME, ID, SIZE, MODIFIED
            for line in lines[1:]:
                parts = [p.strip() for p in line.split() if p.strip()]
                if not parts:
                    continue
                name = parts[0]
                # Fallback attributes if we parsed via CLI
                models.append({
                    "name": name,
                    "size_formatted": parts[2] if len(parts) > 2 else "Unknown",
                    "quantization": "Q4_0" if "q4" in name.lower() or "instruct" in name.lower() else "Unknown",
                    "family": "llama" if "llama" in name.lower() else "qwen",
                    "modified_date": " ".join(parts[3:]) if len(parts) > 3 else "Unknown",
                    "is_recommended": self._is_model_recommended(name, 4.0)
                })
            return models
        except Exception as exc:
            logger.error("Failed to run ollama list: {}", exc)
            return []

    def _is_model_recommended(self, name: str, size_gb: float) -> bool:
        """Recommend models suitable for 16GB RAM + 4GB VRAM (GPU)."""
        name_lower = name.lower()
        # 3B instructs (like llama3.2:3b) fit easily in 4GB VRAM.
        # 8B instructs (like qwen3:8b, llama3.1:8b) run but may spill to CPU.
        # Highlight these as green recommendations.
        if "3b" in name_lower or "2b" in name_lower or "1.5b" in name_lower:
            return True
        if "qwen" in name_lower and ("7b" in name_lower or "8b" in name_lower or "3b" in name_lower):
            return True
        if "llama3.1:8b" in name_lower or "llama3.2:3b" in name_lower or "qwen3:8b" in name_lower:
            return True
        # If size is less than 6GB, suggest it
        if size_gb > 0.0 and size_gb < 6.0:
            return True
        return False

    def pull_model_stream(self, model_name: str) -> Generator[str, None, None]:
        """Pull a model via Ollama API and stream the progress as SSE."""
        try:
            logger.info("Starting pull for model: {}", model_name)
            # Call Ollama pull endpoint
            with httpx.stream("POST", f"{self.ollama_url}/api/pull", json={"name": model_name}, timeout=None) as response:
                for line in response.iter_lines():
                    if not line.strip():
                        continue
                    # Yield raw line to the route to be passed as SSE event
                    yield line
        except Exception as exc:
            logger.error("Error during model pull stream: {}", exc)
            yield f'{{"status": "error", "error": "{str(exc)}"}}'

    def verify_model_exists(self, model_name: str) -> bool:
        """Check if the model is locally installed."""
        installed = self.list_installed_models()
        return any(m["name"] == model_name or m["name"].split(":")[0] == model_name for m in installed)

    def activate_model(self, model_name: str) -> bool:
        """Switch reasoning model in config.yaml and update active runtime config."""
        if not self.verify_model_exists(model_name):
            logger.error("Cannot activate model {} - not installed", model_name)
            return False

        try:
            # 1. Update config.yaml physically
            if _CONFIG_PATH.exists():
                with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}

                if "reasoning" not in config_data:
                    config_data["reasoning"] = {}
                config_data["reasoning"]["model"] = model_name

                with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
                    yaml.safe_dump(config_data, f, default_flow_style=False)
                logger.info("Updated model in config.yaml to {}", model_name)

            # 2. Update environment variable override (for current process)
            os.environ["REASONING_MODEL"] = model_name

            # 3. Reload settings singleton
            from config import get_settings
            settings = get_settings(reload=True)
            logger.info("Settings reloaded. Active reasoning model is now: {}", settings.reasoning.model)
            
            return True
        except Exception as exc:
            logger.error("Failed to activate model {}: {}", model_name, exc)
            return False

_manager_instance: Optional[ModelManager] = None

def get_model_manager() -> ModelManager:
    global _manager_instance
    if _manager_instance is None:
        from config import get_settings
        settings = get_settings()
        _manager_instance = ModelManager(ollama_url=settings.reasoning.ollama_url)
    return _manager_instance
