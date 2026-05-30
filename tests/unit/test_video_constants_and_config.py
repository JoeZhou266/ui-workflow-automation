"""Unit tests for video constants and AppConfig.record_video field.

TDD RED phase — these tests must fail before implementation.
Covers: VID-02, VID-06
"""
from __future__ import annotations

import yaml
import pytest


class TestVideoConstants:
    """VIDEO_DIR and VIDEO_DATE_FORMAT constants exist in src/core/constants.py."""

    def test_video_dir_importable(self):
        from src.core.constants import VIDEO_DIR
        assert VIDEO_DIR == "reports/videos"

    def test_video_date_format_importable(self):
        from src.core.constants import VIDEO_DATE_FORMAT
        assert VIDEO_DATE_FORMAT == "%Y%m%d_%H%M%S"


class TestAppConfigRecordVideo:
    """AppConfig.record_video bool field reads from YAML and env var."""

    def _write_yaml(self, tmp_path, data: dict) -> str:
        f = tmp_path / "env.test.yaml"
        f.write_text(yaml.dump(data), encoding="utf-8")
        return str(tmp_path)

    def test_record_video_defaults_to_false(self, tmp_path):
        from src.core.config import AppConfig
        config = AppConfig(env="test", config_dir=str(tmp_path))
        assert config.record_video is False

    def test_record_video_from_yaml_true(self, tmp_path):
        from src.core.config import AppConfig
        config_dir = self._write_yaml(tmp_path, {"record_video": True})
        config = AppConfig(env="test", config_dir=config_dir)
        assert config.record_video is True

    def test_record_video_from_yaml_false(self, tmp_path):
        from src.core.config import AppConfig
        config_dir = self._write_yaml(tmp_path, {"record_video": False})
        config = AppConfig(env="test", config_dir=config_dir)
        assert config.record_video is False

    def test_record_video_from_env_var_true(self, tmp_path, monkeypatch):
        from src.core.config import AppConfig
        monkeypatch.setenv("RECORD_VIDEO", "true")
        config = AppConfig(env="test", config_dir=str(tmp_path))
        assert config.record_video is True

    def test_record_video_env_var_beats_yaml(self, tmp_path, monkeypatch):
        from src.core.config import AppConfig
        config_dir = self._write_yaml(tmp_path, {"record_video": False})
        monkeypatch.setenv("RECORD_VIDEO", "true")
        config = AppConfig(env="test", config_dir=config_dir)
        assert config.record_video is True

    def test_record_video_has_attribute(self, tmp_path):
        from src.core.config import AppConfig
        config = AppConfig(env="test", config_dir=str(tmp_path))
        assert hasattr(config, "record_video")
