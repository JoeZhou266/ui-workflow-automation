"""Unit tests for log constants, AppConfig.log_file_path, and configure_logging.

Covers LOG-01 through LOG-12.
"""
from __future__ import annotations

import logging
import logging.handlers
import os

import pytest
import yaml


FRAMEWORK = "workflow_framework"


@pytest.fixture(autouse=True)
def reset_framework_logger():
    """Remove all handlers from the framework logger before and after each test.

    Required because configure_logging mutates the root framework logger in-process.
    Without cleanup, handlers accumulate across tests causing false-positives.
    """
    root = logging.getLogger(FRAMEWORK)
    for h in list(root.handlers):
        h.close()
        root.removeHandler(h)
    yield
    for h in list(root.handlers):
        h.close()
        root.removeHandler(h)


# ---------------------------------------------------------------------------
# LOG-12: Constants
# ---------------------------------------------------------------------------

class TestLogConstants:
    """LOG-12: LOG_DIR and LOG_FILE_NAME constants exist and are importable."""

    def test_constants_importable(self):
        from src.core.constants import LOG_DIR, LOG_FILE_NAME

        assert LOG_DIR == "logs"
        assert LOG_FILE_NAME == "workflow.log"


# ---------------------------------------------------------------------------
# LOG-08..LOG-11: AppConfig.log_file_path field
# ---------------------------------------------------------------------------

class TestLogFilePathConfig:
    """LOG-08..LOG-11: AppConfig.log_file_path resolution from env var and YAML."""

    def _write_yaml(self, tmp_path, data: dict) -> str:
        f = tmp_path / "env.test.yaml"
        f.write_text(yaml.dump(data), encoding="utf-8")
        return str(tmp_path)

    def test_defaults_to_none(self, tmp_path):
        """LOG-08: log_file_path is None when not configured."""
        from src.core.config import AppConfig

        config = AppConfig(env="test", config_dir=str(tmp_path))
        assert config.log_file_path is None

    def test_from_yaml(self, tmp_path):
        """LOG-09: log_file_path is read from YAML key 'log_file_path'."""
        from src.core.config import AppConfig

        config_dir = self._write_yaml(tmp_path, {"log_file_path": "logs/workflow.log"})
        config = AppConfig(env="test", config_dir=config_dir)
        assert config.log_file_path == "logs/workflow.log"

    def test_from_env_var(self, tmp_path, monkeypatch):
        """LOG-10: log_file_path is read from env var LOG_FILE_PATH."""
        from src.core.config import AppConfig

        monkeypatch.setenv("LOG_FILE_PATH", "/tmp/test_workflow.log")
        config = AppConfig(env="test", config_dir=str(tmp_path))
        assert config.log_file_path == "/tmp/test_workflow.log"

    def test_env_beats_yaml(self, tmp_path, monkeypatch):
        """LOG-11: env var LOG_FILE_PATH takes priority over YAML log_file_path."""
        from src.core.config import AppConfig

        config_dir = self._write_yaml(tmp_path, {"log_file_path": "logs/yaml.log"})
        monkeypatch.setenv("LOG_FILE_PATH", "/tmp/env.log")
        config = AppConfig(env="test", config_dir=config_dir)
        assert config.log_file_path == "/tmp/env.log"


# ---------------------------------------------------------------------------
# LOG-01..LOG-07: configure_logging handler behaviour
# ---------------------------------------------------------------------------

class TestConfigureLogging:
    """LOG-01..LOG-07: configure_logging handler addition and idempotency."""

    def test_stream_handler_added(self):
        """LOG-01: configure_logging adds exactly one StreamHandler."""
        from src.core.logger import configure_logging

        configure_logging("INFO")
        root = logging.getLogger(FRAMEWORK)
        stream_handlers = [h for h in root.handlers if type(h) is logging.StreamHandler]
        assert len(stream_handlers) == 1

    def test_stream_handler_idempotent(self):
        """LOG-02: calling configure_logging twice does not add duplicate StreamHandler."""
        from src.core.logger import configure_logging

        configure_logging("INFO")
        configure_logging("INFO")
        root = logging.getLogger(FRAMEWORK)
        stream_handlers = [h for h in root.handlers if type(h) is logging.StreamHandler]
        assert len(stream_handlers) == 1

    def test_no_file_handler_when_path_none(self):
        """LOG-03: no TimedRotatingFileHandler added when log_file_path is None."""
        from src.core.logger import configure_logging

        configure_logging("INFO", log_file_path=None)
        root = logging.getLogger(FRAMEWORK)
        file_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]
        assert len(file_handlers) == 0

    def test_file_handler_added_when_path_set(self, tmp_path):
        """LOG-04: TimedRotatingFileHandler added when log_file_path is set."""
        from src.core.logger import configure_logging

        path = str(tmp_path / "workflow.log")
        configure_logging("INFO", log_file_path=path)
        root = logging.getLogger(FRAMEWORK)
        file_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]
        assert len(file_handlers) == 1

    def test_file_handler_rotation_params(self, tmp_path):
        """LOG-05: File handler has when='MIDNIGHT', backupCount=30, encoding='utf-8'."""
        from src.core.logger import configure_logging

        path = str(tmp_path / "workflow.log")
        configure_logging("INFO", log_file_path=path)
        root = logging.getLogger(FRAMEWORK)
        fh = next(
            h for h in root.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        )
        assert fh.when == "MIDNIGHT"
        assert fh.backupCount == 30
        assert fh.encoding == "utf-8"

    def test_file_handler_idempotent(self, tmp_path):
        """LOG-06: calling configure_logging twice does not add duplicate file handler."""
        from src.core.logger import configure_logging

        path = str(tmp_path / "workflow.log")
        configure_logging("INFO", log_file_path=path)
        configure_logging("INFO", log_file_path=path)
        root = logging.getLogger(FRAMEWORK)
        file_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]
        assert len(file_handlers) == 1

    def test_log_dir_auto_created(self, tmp_path):
        """LOG-07: parent directory of log_file_path is auto-created if it does not exist."""
        from src.core.logger import configure_logging

        # Use a nested directory that does not exist yet
        nested = tmp_path / "deep" / "nested"
        path = str(nested / "workflow.log")
        assert not nested.exists(), "Pre-condition: nested dir must not exist before configure_logging"
        configure_logging("INFO", log_file_path=path)
        assert nested.exists(), "Post-condition: nested dir must be created by configure_logging"
