"""Settings management for Railway Framework."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseModel):
    """API configuration."""

    base_url: str = ""
    timeout: int = 30
    max_retries: int = 3


class DatabaseSettings(BaseModel):
    """Database configuration."""

    host: str = "localhost"
    port: int = 5432
    name: str = "db"
    user: str | None = None
    password: str | None = None


class RetryNodeSettings(BaseModel):
    """Per-node retry settings."""

    max_attempts: int = 3
    min_wait: int = 2
    max_wait: int = 10
    multiplier: int = 1


class RetrySettings(BaseModel):
    """Retry policy configuration."""

    default: RetryNodeSettings = Field(default_factory=RetryNodeSettings)
    nodes: dict[str, RetryNodeSettings] = Field(default_factory=dict)


class LoggingHandlerSettings(BaseModel):
    """Logging handler configuration."""

    type: str  # file, console
    level: str = "INFO"
    path: str | None = None
    rotation: str | None = None
    retention: str | None = None


class LoggingSettings(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "{time:HH:mm:ss} | {level} | {message}"
    handlers: list[LoggingHandlerSettings] = Field(default_factory=list)


def _load_yaml_config(config_dir: Path, env: str) -> dict[str, Any]:
    """
    Load YAML configuration file.

    Args:
        config_dir: Directory containing config files
        env: Environment name (development, production, etc.)

    Returns:
        Configuration dictionary
    """
    config_file = config_dir / f"{env}.yaml"

    if not config_file.exists():
        return {}

    with open(config_file, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _parse_api_settings(config: dict[str, Any]) -> APISettings:
    """Parse API settings from config dict."""
    api_config = config.get("api", {})
    return APISettings(**api_config) if api_config else APISettings()


def _parse_database_settings(config: dict[str, Any]) -> DatabaseSettings:
    """Parse database settings from config dict."""
    db_config = config.get("database", {})
    return DatabaseSettings(**db_config) if db_config else DatabaseSettings()


def _parse_retry_settings(config: dict[str, Any]) -> RetrySettings:
    """Parse retry settings from config dict."""
    retry_config = config.get("retry", {})
    if not retry_config:
        return RetrySettings()

    default_retry = RetryNodeSettings(**retry_config.get("default", {}))
    nodes_retry = {
        name: RetryNodeSettings(**settings)
        for name, settings in retry_config.get("nodes", {}).items()
    }
    return RetrySettings(default=default_retry, nodes=nodes_retry)


def _parse_logging_settings(config: dict[str, Any]) -> LoggingSettings:
    """Parse logging settings from config dict."""
    log_config = config.get("logging", {})
    if not log_config:
        return LoggingSettings()

    handlers = [
        LoggingHandlerSettings(**h) for h in log_config.get("handlers", [])
    ]
    return LoggingSettings(
        level=log_config.get("level", "INFO"),
        format=log_config.get("format", "{time:HH:mm:ss} | {level} | {message}"),
        handlers=handlers,
    )


def _apply_env_overrides(
    logging_settings: LoggingSettings,
    log_level: str | None,
) -> LoggingSettings:
    """
    Apply environment variable overrides to logging settings.

    Returns new LoggingSettings with overrides applied.
    """
    if log_level:
        return LoggingSettings(
            level=log_level,
            format=logging_settings.format,
            handlers=logging_settings.handlers,
        )
    return logging_settings


class Settings(BaseSettings):
    """
    Application settings.

    Loads configuration from:
    1. Environment variables (.env file)
    2. YAML config file (config/{env}.yaml)

    Environment variables override YAML config values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # Environment variables
    railway_env: str = "development"
    app_name: str = "railway_app"
    log_level: str | None = None  # Override from .env

    # Configuration from YAML (will be populated after init)
    api: APISettings = Field(default_factory=APISettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    retry: RetrySettings = Field(default_factory=RetrySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    def __init__(self, _config_dir: str | None = None, **kwargs: Any) -> None:
        """Initialize settings and load YAML config."""
        super().__init__(**kwargs)

        # Determine config directory
        config_dir = self._resolve_config_dir(_config_dir)

        # Load and parse YAML configuration
        config = _load_yaml_config(config_dir, self.railway_env)

        # Parse individual sections (functional approach)
        self.api = _parse_api_settings(config)
        self.database = _parse_database_settings(config)
        self.retry = _parse_retry_settings(config)
        self.logging = _parse_logging_settings(config)

        # Apply environment variable overrides
        self.logging = _apply_env_overrides(self.logging, self.log_level)

    def _resolve_config_dir(self, config_dir: str | None) -> Path:
        """Resolve the configuration directory path."""
        if config_dir:
            return Path(config_dir)

        # Default: look for config/ in current directory or parent
        cwd_config = Path.cwd() / "config"
        if cwd_config.exists():
            return cwd_config

        return Path(__file__).parent.parent.parent / "config"

    def get_retry_settings(self, node_name: str) -> RetryNodeSettings:
        """
        Get retry settings for a specific node.

        Args:
            node_name: Name of the node

        Returns:
            RetryNodeSettings for the node, or default if not specified
        """
        return self.retry.nodes.get(node_name, self.retry.default)


# Global settings instance (lazy initialization)
_settings: Settings | None = None


def get_settings(_config_dir: str | None = None) -> Settings:
    """
    Get the global settings instance.

    Creates a new instance on first call, returns cached instance thereafter.

    Args:
        _config_dir: Optional config directory (only used on first call)

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings(_config_dir=_config_dir)
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance (for testing)."""
    global _settings
    _settings = None
