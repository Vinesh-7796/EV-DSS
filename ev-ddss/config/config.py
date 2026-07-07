"""Configuration management for EV-DDSS.

Resolves settings from config.yaml with environment variable overrides.
Uses Pydantic Settings for validation and type coercion.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_project_root() -> Path:
    """Locate the project root directory by walking up from this file."""
    return Path(__file__).resolve().parent.parent


class DatabaseSettings(BaseSettings):
    """PostgreSQL database connection settings."""

    url: str = Field(
        default="postgresql://user:password@localhost:5432/ev_ddss",
        description="PostgreSQL connection string",
    )
    pool_size: int = Field(default=10, ge=1, description="Connection pool size")
    max_overflow: int = Field(default=20, ge=0, description="Max pool overflow connections")
    pool_pre_ping: bool = Field(default=True, description="Enable connection health checks")
    echo: bool = Field(default=False, description="Log SQL statements")


class QdrantSettings(BaseSettings):
    """Qdrant vector database connection settings."""

    url: str = Field(default="http://localhost:6333", description="Qdrant server URL")
    api_key: Optional[str] = Field(default=None, description="Qdrant API key")
    timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")
    prefer_grpc: bool = Field(default=False, description="Prefer gRPC protocol")


class LoggingSettings(BaseSettings):
    """Structured logging configuration."""

    level: str = Field(default="INFO", description="Logging level")
    console: bool = Field(default=True, description="Enable console logging")
    file: bool = Field(default=True, description="Enable file logging")
    file_path: str = Field(default="logs/ev-ddss.log", description="Log file path")
    rotation: str = Field(default="10 MB", description="Log rotation size")
    retention: str = Field(default="30 days", description="Log retention period")
    format: str = Field(
        default=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        description="Log message format",
    )


class ApplicationSettings(BaseSettings):
    """Core application settings."""

    name: str = Field(default="EV-DDSS", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8000, ge=1024, le=65535, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Application log level")


class EmbeddingSettings(BaseSettings):
    """Future: embedding model settings (placeholder for Phase 1+)."""

    model: str = Field(default="text-embedding-3-small", description="Embedding model name")
    dimension: int = Field(default=1536, ge=64, description="Embedding vector dimension")
    device: str = Field(default="cpu", description="Inference device (cpu/cuda)")


class LLMSettings(BaseSettings):
    """Future: LLM settings (placeholder for Phase 2+)."""

    model: str = Field(default="llama-3.2-3b-instruct", description="LLM model name")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=2048, ge=64, description="Maximum output tokens")
    device: str = Field(default="cpu", description="Inference device (cpu/cuda)")
    context_length: int = Field(default=8192, ge=1024, description="Model context window")


class StoreSettings(BaseSettings):
    """Knowledge store configuration."""

    json_enabled: bool = Field(default=True, description="Enable JSON filesystem store")
    json_path: str = Field(default="./data/store/json", description="JSON store directory")
    sql_enabled: bool = Field(default=False, description="Enable PostgreSQL store")
    image_enabled: bool = Field(default=True, description="Enable image store")
    image_path: str = Field(default="./data/store/images", description="Image store directory")


class DataSettings(BaseSettings):
    """Data path settings for file-based storage."""

    raw: str = Field(default="./data/raw", description="Raw data directory")
    processed: str = Field(default="./data/processed", description="Processed data directory")
    embeddings: str = Field(default="./data/embeddings", description="Embedding storage directory")
    images: str = Field(default="./data/images", description="Image data directory")
    cache: str = Field(default="./data/cache", description="Cache directory")


class RetrievalSettings(BaseSettings):
    """Retrieval engine settings."""

    chunk_size: int = Field(default=512, ge=64, description="Target tokens per chunk")
    chunk_overlap: int = Field(default=32, ge=0, description="Overlap between adjacent chunks")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", description="Sentence transformer model name")
    embedding_dimension: int = Field(default=384, ge=64, description="Embedding vector dimension")
    top_k_vector: int = Field(default=10, ge=1, description="Default top-k for vector search")
    top_k_graph: int = Field(default=10, ge=1, description="Default top-k for graph traversal")
    top_k_sql: int = Field(default=10, ge=1, description="Default top-k for SQL lookup")
    top_k_image: int = Field(default=5, ge=1, description="Default top-k for image search")
    max_context_tokens: int = Field(default=4096, ge=256, description="Max tokens in context package")
    enable_vector: bool = Field(default=True, description="Enable vector search")
    enable_graph: bool = Field(default=True, description="Enable graph traversal")
    enable_sql: bool = Field(default=True, description="Enable SQL lookup")
    enable_image: bool = Field(default=True, description="Enable image retrieval")
    vector_score_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Min vector score threshold")


class ReasoningSettings(BaseSettings):
    """LLM orchestration engine settings."""

    runtime: str = Field(default="ollama", description="LLM runtime (ollama, openai, vllm)")
    model: str = Field(default="qwen3:8b", description="Model name/tag for the runtime")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    max_tokens: int = Field(default=2048, ge=64, description="Maximum output tokens")
    context_window: int = Field(default=8192, ge=1024, description="Model context window")
    system_prompt: str = Field(
        default="You are an expert automotive diagnostic assistant focused on EVs.",
        description="Base system prompt for the LLM",
    )
    max_context_tokens: int = Field(default=4096, ge=256, description="Max tokens after context optimization")
    deduplicate_context: bool = Field(default=True, description="Deduplicate retrieved context")
    ollama_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    openai_url: str = Field(default="", description="OpenAI-compatible endpoint URL")
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="", description="OpenAI model override")
    request_timeout_s: int = Field(default=120, ge=10, description="LLM request timeout")
    strict_validation: bool = Field(default=True, description="Strict JSON response validation")
    retry_on_parse_failure: bool = Field(default=True, description="Retry on malformed JSON")
    max_retries: int = Field(default=2, ge=0, description="Max parse retry attempts")
    template_directory: str = Field(default="", description="Override template directory path")


class Settings(BaseSettings):
    """Top-level settings aggregating all sub-settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    application: ApplicationSettings = ApplicationSettings()
    database: DatabaseSettings = DatabaseSettings()
    qdrant: QdrantSettings = QdrantSettings()
    logging: LoggingSettings = LoggingSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    llm: LLMSettings = LLMSettings()
    store: StoreSettings = StoreSettings()
    data: DataSettings = DataSettings()
    retrieval: RetrievalSettings = RetrievalSettings()
    reasoning: ReasoningSettings = ReasoningSettings()

    @classmethod
    def from_yaml(cls, yaml_path: Optional[Path] = None) -> "Settings":
        """Load settings from a YAML file with environment variable interpolation.

        Args:
            yaml_path: Path to the YAML configuration file.
                       Defaults to config/config.yaml relative to project root.

        Returns:
            Populated Settings instance with YAML + env overrides.
        """
        if yaml_path is None:
            yaml_path = find_project_root() / "config" / "config.yaml"

        if not yaml_path.exists():
            return cls()

        with open(yaml_path, "r") as f:
            raw = f.read()

        # Simple ${VAR:-default} environment variable interpolation
        import re

        def _replace_env(match: re.Match) -> str:
            var = match.group(1)
            default = match.group(2) or ""
            return os.environ.get(var, default)

        interpolated = re.sub(r"\$\{([^:}]+):-([^}]*)\}", _replace_env, raw)
        data: Dict[str, Any] = yaml.safe_load(interpolated) or {}

        return cls(**data)

    @field_validator("application", mode="before")
    @classmethod
    def _validate_application(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return v
        return v


# Module-level cache for the singleton settings instance
_settings: Optional[Settings] = None


def get_settings(reload: bool = False) -> Settings:
    """Return the application settings singleton.

    Args:
        reload: Force reload from YAML and environment.

    Returns:
        The global Settings instance.
    """
    global _settings
    if _settings is None or reload:
        _settings = Settings.from_yaml()
    return _settings
