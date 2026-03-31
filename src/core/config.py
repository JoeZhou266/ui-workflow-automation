from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

from src.core.constants import (
    CONFIGS_DIR,
    DEFAULT_AJAX_IDLE_TIMEOUT,
    DEFAULT_ENV,
    DEFAULT_EXPLICIT_WAIT_TIMEOUT,
    DEFAULT_PAGE_LOAD_TIMEOUT,
    DEFAULT_POLL_FREQUENCY_MS,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    SCREENSHOT_DIR,
)


class AppConfig:
    """Holds resolved runtime configuration merged from YAML and environment variables."""

    def __init__(
        self,
        env: str = DEFAULT_ENV,
        config_dir: str = CONFIGS_DIR,
    ) -> None:
        load_dotenv()
        self._data = self._load_yaml(env, config_dir)

        self.base_url: str = self._resolve("BASE_URL", "base_url", "")
        self.browser: str = self._resolve("BROWSER", "browser", "chrome").lower()
        self.headless: bool = self._resolve_bool("HEADLESS", "headless", False)
        self.implicit_wait: int = int(self._resolve("IMPLICIT_WAIT", "implicit_wait", 0))
        self.page_load_timeout: int = int(
            self._resolve("PAGE_LOAD_TIMEOUT", "page_load_timeout", DEFAULT_PAGE_LOAD_TIMEOUT)
        )
        self.explicit_wait_timeout: int = int(
            self._resolve("EXPLICIT_WAIT_TIMEOUT", "explicit_wait_timeout", DEFAULT_EXPLICIT_WAIT_TIMEOUT)
        )
        self.ajax_idle_timeout: int = int(
            self._resolve("AJAX_IDLE_TIMEOUT", "ajax_idle_timeout", DEFAULT_AJAX_IDLE_TIMEOUT)
        )
        self.poll_frequency_ms: int = int(
            self._resolve("POLL_FREQUENCY_MS", "poll_frequency_ms", DEFAULT_POLL_FREQUENCY_MS)
        )
        self.screenshots_dir: str = self._resolve("SCREENSHOTS_DIR", "screenshots_dir", SCREENSHOT_DIR)
        self.log_level: str = self._resolve("LOG_LEVEL", "log_level", "INFO").upper()
        self.window_width: int = int(
            self._resolve("WINDOW_WIDTH", "window_width", DEFAULT_WINDOW_WIDTH)
        )
        self.window_height: int = int(
            self._resolve("WINDOW_HEIGHT", "window_height", DEFAULT_WINDOW_HEIGHT)
        )

    def _load_yaml(self, env: str, config_dir: str) -> dict:
        path = Path(config_dir) / f"env.{env}.yaml"
        if path.exists():
            with path.open() as f:
                return yaml.safe_load(f) or {}
        return {}

    def _resolve(self, env_key: str, yaml_key: str, default) -> str:
        env_val = os.environ.get(env_key)
        if env_val is not None and env_val != "":
            return env_val
        yaml_val = self._data.get(yaml_key)
        if yaml_val is not None:
            return str(yaml_val)
        return str(default)

    def _resolve_bool(self, env_key: str, yaml_key: str, default: bool) -> bool:
        raw = self._resolve(env_key, yaml_key, str(default))
        return raw.lower() in ("true", "1", "yes")
