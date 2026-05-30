"""Unit tests for VideoManager class.

TDD RED phase — these tests must fail before implementation.
Covers: VID-01, VID-03, VID-04, VID-05
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestVideoManagerImport:
    """VideoManager and _find_macos_screen_index are importable from src.utils.videos."""

    def test_video_manager_importable(self):
        from src.utils.videos import VideoManager  # noqa: F401

    def test_find_macos_screen_index_importable(self):
        from src.utils.videos import _find_macos_screen_index  # noqa: F401


class TestVideoManagerInterface:
    """VideoManager has required interface: __init__, start, stop, delete, _build_cmd."""

    def _get_manager(self):
        from src.utils.videos import VideoManager
        return VideoManager

    def test_has_start_method(self):
        assert hasattr(self._get_manager(), "start")

    def test_has_stop_method(self):
        assert hasattr(self._get_manager(), "stop")

    def test_has_delete_method(self):
        assert hasattr(self._get_manager(), "delete")

    def test_has_build_cmd_method(self):
        assert hasattr(self._get_manager(), "_build_cmd")

    def test_default_base_dir_is_video_dir(self):
        from src.utils.videos import VideoManager
        from src.core.constants import VIDEO_DIR
        m = VideoManager()
        assert str(m._base_dir) == VIDEO_DIR


class TestVideoManagerHeadless:
    """VideoManager.start() returns None when headless=True."""

    def test_start_returns_none_when_headless(self):
        from src.utils.videos import VideoManager
        m = VideoManager()
        result = m.start("test_foo", headless=True)
        assert result is None

    def test_start_headless_does_not_spawn_process(self):
        from src.utils.videos import VideoManager
        m = VideoManager()
        m.start("test_foo", headless=True)
        # No subprocess should have been created
        assert m._proc is None


class TestVideoManagerNoFfmpeg:
    """VideoManager.start() returns None when ffmpeg not on PATH."""

    def test_start_returns_none_when_ffmpeg_not_found(self):
        from src.utils.videos import VideoManager
        m = VideoManager()
        with patch("shutil.which", return_value=None):
            result = m.start("test_foo", headless=False)
        assert result is None

    def test_start_no_proc_when_ffmpeg_not_found(self):
        from src.utils.videos import VideoManager
        m = VideoManager()
        with patch("shutil.which", return_value=None):
            m.start("test_foo", headless=False)
        assert m._proc is None


class TestVideoManagerLinuxNoDisplay:
    """VideoManager.start() returns None on Linux when DISPLAY env var is absent."""

    def test_start_returns_none_on_linux_without_display(self, monkeypatch):
        from src.utils.videos import VideoManager
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        m = VideoManager()
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("platform.system", return_value="Linux"):
            result = m.start("test_foo", headless=False)
        assert result is None


class TestVideoManagerStart:
    """VideoManager.start() returns file path string when ffmpeg is available."""

    def test_start_returns_mp4_path_on_macos(self, tmp_path, monkeypatch):
        from src.utils.videos import VideoManager

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.stdin = MagicMock()

        m = VideoManager(base_dir=str(tmp_path))
        with patch("shutil.which", return_value="/usr/local/bin/ffmpeg"), \
             patch("platform.system", return_value="Darwin"), \
             patch("src.utils.videos._find_macos_screen_index", return_value="1"), \
             patch("subprocess.Popen", return_value=mock_proc):
            result = m.start("test_foo", headless=False)

        assert result is not None
        assert result.endswith(".mp4")

    def test_start_sets_current_path(self, tmp_path, monkeypatch):
        from src.utils.videos import VideoManager

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.stdin = MagicMock()

        m = VideoManager(base_dir=str(tmp_path))
        with patch("shutil.which", return_value="/usr/local/bin/ffmpeg"), \
             patch("platform.system", return_value="Darwin"), \
             patch("src.utils.videos._find_macos_screen_index", return_value="1"), \
             patch("subprocess.Popen", return_value=mock_proc):
            result = m.start("test_bar", headless=False)

        assert m._current_path == result

    def test_start_returns_none_on_windows(self, tmp_path):
        from src.utils.videos import VideoManager

        m = VideoManager(base_dir=str(tmp_path))
        with patch("shutil.which", return_value="C:\\ffmpeg\\bin\\ffmpeg.exe"), \
             patch("platform.system", return_value="Windows"):
            result = m.start("test_foo", headless=False)

        assert result is None


class TestVideoManagerStop:
    """VideoManager.stop() gracefully stops ffmpeg via stdin 'q' signal."""

    def test_stop_is_noop_when_no_proc(self):
        from src.utils.videos import VideoManager
        m = VideoManager()
        m._proc = None
        # Should not raise
        m.stop()

    def test_stop_sends_q_to_stdin(self):
        from src.utils.videos import VideoManager

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None  # process still running
        mock_proc.stdin = MagicMock()
        mock_proc.wait.return_value = 0

        m = VideoManager()
        m._proc = mock_proc
        m.stop()

        mock_proc.stdin.write.assert_called_once_with(b"q")

    def test_stop_calls_wait_with_timeout(self):
        from src.utils.videos import VideoManager

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.wait.return_value = 0

        m = VideoManager()
        m._proc = mock_proc
        m.stop()

        mock_proc.wait.assert_called_once_with(timeout=10)

    def test_stop_kills_on_timeout_expired(self):
        from src.utils.videos import VideoManager

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        # Only raise on first call (timeout=10); bare wait() after kill should succeed
        mock_proc.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="ffmpeg", timeout=10),
            None,
        ]

        m = VideoManager()
        m._proc = mock_proc
        m.stop()

        mock_proc.kill.assert_called_once()

    def test_stop_clears_proc_reference(self):
        from src.utils.videos import VideoManager

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.stdin = MagicMock()
        mock_proc.wait.return_value = 0

        m = VideoManager()
        m._proc = mock_proc
        m.stop()

        assert m._proc is None

    def test_stop_noop_when_already_terminated(self):
        from src.utils.videos import VideoManager

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = 0  # already terminated

        m = VideoManager()
        m._proc = mock_proc
        m.stop()

        # Process already terminated — _proc should be cleared, wait not called
        assert m._proc is None
        mock_proc.wait.assert_not_called()


class TestVideoManagerDelete:
    """VideoManager.delete() removes the file from the filesystem."""

    def test_delete_removes_existing_file(self, tmp_path):
        from src.utils.videos import VideoManager

        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"fake mp4 content")
        assert video_file.exists()

        m = VideoManager()
        m.delete(str(video_file))

        assert not video_file.exists()

    def test_delete_noop_when_file_not_found(self, tmp_path):
        from src.utils.videos import VideoManager

        missing_path = str(tmp_path / "nonexistent.mp4")
        m = VideoManager()
        # Should not raise
        m.delete(missing_path)

    def test_delete_calls_os_remove(self, tmp_path):
        from src.utils.videos import VideoManager

        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"fake mp4 content")

        m = VideoManager()
        with patch("os.remove") as mock_remove:
            m.delete(str(video_file))
        mock_remove.assert_called_once_with(str(video_file))


class TestVideoManagerBuildCmd:
    """VideoManager._build_cmd() returns platform-appropriate command or None."""

    def test_build_cmd_darwin_returns_list(self):
        from src.utils.videos import VideoManager
        m = VideoManager()
        with patch("src.utils.videos._find_macos_screen_index", return_value="1"):
            cmd = m._build_cmd("Darwin")
        assert cmd is not None
        assert isinstance(cmd, list)
        assert "ffmpeg" in cmd

    def test_build_cmd_darwin_uses_avfoundation(self):
        from src.utils.videos import VideoManager
        m = VideoManager()
        with patch("src.utils.videos._find_macos_screen_index", return_value="1"):
            cmd = m._build_cmd("Darwin")
        assert "-f" in cmd
        idx = cmd.index("-f")
        assert cmd[idx + 1] == "avfoundation"

    def test_build_cmd_linux_returns_list_when_display_set(self, monkeypatch):
        from src.utils.videos import VideoManager
        monkeypatch.setenv("DISPLAY", ":0.0")
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        m = VideoManager()
        cmd = m._build_cmd("Linux")
        assert cmd is not None
        assert isinstance(cmd, list)

    def test_build_cmd_linux_returns_none_without_display(self, monkeypatch):
        from src.utils.videos import VideoManager
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        m = VideoManager()
        cmd = m._build_cmd("Linux")
        assert cmd is None

    def test_build_cmd_windows_returns_none(self):
        from src.utils.videos import VideoManager
        m = VideoManager()
        cmd = m._build_cmd("Windows")
        assert cmd is None

    def test_build_cmd_uses_x11grab_on_linux(self, monkeypatch):
        from src.utils.videos import VideoManager
        monkeypatch.setenv("DISPLAY", ":0.0")
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        m = VideoManager()
        cmd = m._build_cmd("Linux")
        assert "-f" in cmd
        idx = cmd.index("-f")
        assert cmd[idx + 1] == "x11grab"
