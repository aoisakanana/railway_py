"""Tests for Settings management."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestSettingsBasic:
    """Test basic Settings functionality."""

    def test_settings_creation(self):
        """Should create Settings instance."""
        from railway.core.settings import Settings

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "development.yaml"
            config_file.write_text(
                """
app:
  name: test_app
api:
  base_url: https://api.example.com
"""
            )
            with patch.dict(os.environ, {"RAILWAY_ENV": "development"}):
                settings = Settings(_config_dir=str(config_dir))

            assert settings is not None

    def test_settings_default_env(self):
        """Should default to development environment."""
        from railway.core.settings import Settings

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            (config_dir / "development.yaml").write_text("app:\n  name: dev")

            settings = Settings(_config_dir=str(config_dir))
            assert settings.railway_env == "development"

    def test_settings_env_override(self):
        """Should respect RAILWAY_ENV environment variable."""
        from railway.core.settings import Settings

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            (config_dir / "production.yaml").write_text("app:\n  name: prod")

            with patch.dict(os.environ, {"RAILWAY_ENV": "production"}):
                settings = Settings(_config_dir=str(config_dir))

            assert settings.railway_env == "production"


class TestAPISettings:
    """Test API settings."""

    def test_api_settings_loaded(self):
        """Should load API settings from YAML."""
        from railway.core.settings import Settings

        yaml_content = """
api:
  base_url: https://api.test.com
  timeout: 60
  max_retries: 5
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            (config_dir / "development.yaml").write_text(yaml_content)

            settings = Settings(_config_dir=str(config_dir))

            assert settings.api is not None
            assert settings.api.base_url == "https://api.test.com"
            assert settings.api.timeout == 60
            assert settings.api.max_retries == 5

    def test_api_settings_defaults(self):
        """Should use defaults for optional API settings."""
        from railway.core.settings import Settings

        yaml_content = """
api:
  base_url: https://api.test.com
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            (config_dir / "development.yaml").write_text(yaml_content)

            settings = Settings(_config_dir=str(config_dir))

            assert settings.api.timeout == 30  # default
            assert settings.api.max_retries == 3  # default


class TestRetrySettings:
    """Test retry settings."""

    def test_retry_default_settings(self):
        """Should load default retry settings."""
        from railway.core.settings import Settings

        yaml_content = """
retry:
  default:
    max_attempts: 5
    min_wait: 1
    max_wait: 30
    multiplier: 2
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            (config_dir / "development.yaml").write_text(yaml_content)

            settings = Settings(_config_dir=str(config_dir))

            assert settings.retry.default.max_attempts == 5
            assert settings.retry.default.min_wait == 1

    def test_retry_node_specific_settings(self):
        """Should load node-specific retry settings."""
        from railway.core.settings import Settings

        yaml_content = """
retry:
  default:
    max_attempts: 3
  nodes:
    fetch_data:
      max_attempts: 10
      min_wait: 5
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            (config_dir / "development.yaml").write_text(yaml_content)

            settings = Settings(_config_dir=str(config_dir))

            # Get retry settings for specific node
            retry_config = settings.get_retry_settings("fetch_data")
            assert retry_config.max_attempts == 10
            assert retry_config.min_wait == 5

    def test_get_retry_settings_fallback(self):
        """Should fallback to default for unknown nodes."""
        from railway.core.settings import Settings

        yaml_content = """
retry:
  default:
    max_attempts: 3
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            (config_dir / "development.yaml").write_text(yaml_content)

            settings = Settings(_config_dir=str(config_dir))

            retry_config = settings.get_retry_settings("unknown_node")
            assert retry_config.max_attempts == 3


class TestLoggingSettings:
    """Test logging settings."""

    def test_logging_settings_loaded(self):
        """Should load logging settings."""
        from railway.core.settings import Settings

        yaml_content = """
logging:
  level: DEBUG
  format: "{time} | {level} | {message}"
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            (config_dir / "development.yaml").write_text(yaml_content)

            settings = Settings(_config_dir=str(config_dir))

            assert settings.logging.level == "DEBUG"
            assert "{time}" in settings.logging.format

    def test_logging_handlers(self):
        """Should load logging handlers."""
        from railway.core.settings import Settings

        yaml_content = """
logging:
  level: INFO
  handlers:
    - type: console
      level: DEBUG
    - type: file
      path: logs/app.log
      level: INFO
      rotation: "1 day"
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            (config_dir / "development.yaml").write_text(yaml_content)

            settings = Settings(_config_dir=str(config_dir))

            assert len(settings.logging.handlers) == 2
            assert settings.logging.handlers[0].type == "console"
            assert settings.logging.handlers[1].type == "file"


class TestSettingsEnvOverride:
    """Test environment variable overrides."""

    def test_log_level_override(self):
        """Should override log level from environment."""
        from railway.core.settings import Settings

        yaml_content = """
logging:
  level: INFO
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            (config_dir / "development.yaml").write_text(yaml_content)

            with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
                settings = Settings(_config_dir=str(config_dir))

            assert settings.logging.level == "DEBUG"


class TestSettingsMissingConfig:
    """Test behavior with missing config."""

    def test_missing_config_file(self):
        """Should handle missing config file gracefully."""
        from railway.core.settings import Settings

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            # No config file created

            settings = Settings(_config_dir=str(config_dir))

            # Should have defaults
            assert settings.retry.default.max_attempts == 3

    def test_invalid_yaml(self):
        """Should raise error for invalid YAML."""
        from railway.core.settings import Settings

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            (config_dir / "development.yaml").write_text("invalid: yaml: content:")

            with pytest.raises(Exception):  # YAML parse error
                Settings(_config_dir=str(config_dir))
