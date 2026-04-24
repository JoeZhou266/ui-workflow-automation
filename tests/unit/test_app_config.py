"""Unit tests for AppConfig driver path fields — no browser required."""
from __future__ import annotations

import pytest

from src.core.config import AppConfig


class TestAppConfigDriverPaths:
    """driver_path and browser_binary_path resolution from YAML and env vars."""

    def _yaml(self, tmp_path, data: dict):
        """Write a minimal env.test.yaml and return the config dir."""
        import yaml
        f = tmp_path / "env.test.yaml"
        f.write_text(yaml.dump(data), encoding="utf-8")
        return str(tmp_path)

    # --- defaults ---

    def test_driver_path_defaults_to_none(self, tmp_path):
        config = AppConfig(env="test", config_dir=str(tmp_path))
        assert config.driver_path is None

    def test_browser_binary_path_defaults_to_none(self, tmp_path):
        config = AppConfig(env="test", config_dir=str(tmp_path))
        assert config.browser_binary_path is None

    # --- YAML ---

    def test_driver_path_from_yaml(self, tmp_path):
        config_dir = self._yaml(tmp_path, {"driver_path": "/usr/local/bin/chromedriver"})
        config = AppConfig(env="test", config_dir=config_dir)
        assert config.driver_path == "/usr/local/bin/chromedriver"

    def test_browser_binary_path_from_yaml(self, tmp_path):
        config_dir = self._yaml(tmp_path, {"browser_binary_path": "/opt/google/chrome/chrome"})
        config = AppConfig(env="test", config_dir=config_dir)
        assert config.browser_binary_path == "/opt/google/chrome/chrome"

    # --- env vars ---

    def test_driver_path_from_env_var(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DRIVER_PATH", "/tmp/chromedriver")
        config = AppConfig(env="test", config_dir=str(tmp_path))
        assert config.driver_path == "/tmp/chromedriver"

    def test_browser_binary_path_from_env_var(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BROWSER_BINARY_PATH", "/tmp/chrome")
        config = AppConfig(env="test", config_dir=str(tmp_path))
        assert config.browser_binary_path == "/tmp/chrome"

    # --- env var beats YAML ---

    def test_env_var_takes_priority_over_yaml_for_driver_path(self, tmp_path, monkeypatch):
        config_dir = self._yaml(tmp_path, {"driver_path": "/yaml/chromedriver"})
        monkeypatch.setenv("DRIVER_PATH", "/env/chromedriver")
        config = AppConfig(env="test", config_dir=config_dir)
        assert config.driver_path == "/env/chromedriver"

    def test_env_var_takes_priority_over_yaml_for_binary_path(self, tmp_path, monkeypatch):
        config_dir = self._yaml(tmp_path, {"browser_binary_path": "/yaml/chrome"})
        monkeypatch.setenv("BROWSER_BINARY_PATH", "/env/chrome")
        config = AppConfig(env="test", config_dir=config_dir)
        assert config.browser_binary_path == "/env/chrome"
