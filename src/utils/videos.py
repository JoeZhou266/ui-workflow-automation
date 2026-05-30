from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core.constants import VIDEO_DATE_FORMAT, VIDEO_DIR
from src.core.logger import get_logger
from src.utils.files import ensure_dir, safe_filename

logger = get_logger("videos")


class VideoManager:
    """Manages ffmpeg screen recording for smoke tests.

    Mirrors the ScreenshotManager interface shape: __init__(base_dir),
    start(name, headless) -> Optional[str], stop() -> None, delete(path) -> None.
    """

    def __init__(self, base_dir: str = VIDEO_DIR) -> None:
        self._base_dir = Path(base_dir)
        self._proc: Optional[subprocess.Popen] = None
        self._current_path: Optional[str] = None

    def start(self, name: str, headless: bool = False) -> Optional[str]:
        """Start ffmpeg recording; return output path, or None if unavailable.

        Guards (all return None + log WARNING):
          - headless=True: no display to capture
          - ffmpeg not on PATH
          - Linux without $DISPLAY set (Wayland or no X server)
          - unsupported platform (Windows)
        """
        if headless:
            logger.warning("Video recording skipped: headless mode active")
            return None

        if shutil.which("ffmpeg") is None:
            logger.warning("ffmpeg not found on PATH — video recording disabled")
            return None

        system = platform.system()
        cmd = self._build_cmd(system)
        if cmd is None:
            return None

        timestamp = datetime.now().strftime(VIDEO_DATE_FORMAT)
        safe_name = safe_filename(name)
        filename = f"{timestamp}_{safe_name}.mp4"
        ensure_dir(self._base_dir)
        file_path = self._base_dir / filename

        full_cmd = cmd + [str(file_path)]

        try:
            self._proc = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._current_path = str(file_path)
            logger.info("Video recording started: %s", file_path)
            return self._current_path
        except FileNotFoundError:
            logger.warning("ffmpeg not found — video recording disabled")
            return None
        except Exception as exc:
            logger.warning("Failed to start video recording '%s': %s", name, exc)
            return None

    def stop(self) -> None:
        """Stop the ffmpeg subprocess gracefully via stdin 'q' signal."""
        if self._proc is None:
            return
        if self._proc.poll() is not None:
            self._proc = None
            return
        try:
            self._proc.stdin.write(b"q")
            self._proc.stdin.flush()
            self._proc.stdin.close()
            self._proc.wait(timeout=10)
        except (BrokenPipeError, OSError):
            # Process died before we could write; reap it to avoid zombie.
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        except subprocess.TimeoutExpired:
            logger.warning("ffmpeg did not exit cleanly — killing process")
            self._proc.kill()
            self._proc.wait()
        finally:
            self._proc = None

    def delete(self, path: str) -> None:
        """Delete a video file (called on test pass to discard the recording)."""
        try:
            os.remove(path)
            logger.info("Video deleted (test passed): %s", path)
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.warning("Failed to delete video '%s': %s", path, exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_cmd(self, system: str) -> Optional[list]:
        """Return the platform-specific ffmpeg command prefix (without output path).

        Returns None if the platform is unsupported or missing required env.
        """
        if system == "Darwin":
            screen_index = _find_macos_screen_index()
            return [
                "ffmpeg", "-y",
                "-f", "avfoundation",
                "-framerate", "15",
                "-i", screen_index,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-pix_fmt", "yuv420p",
            ]

        if system == "Linux":
            display = os.environ.get("DISPLAY")
            if not display:
                logger.warning(
                    "No DISPLAY env var — video recording disabled (Wayland or no X server)"
                )
                return None
            wayland = os.environ.get("WAYLAND_DISPLAY")
            if wayland:
                logger.warning(
                    "Wayland detected ($WAYLAND_DISPLAY=%s) — x11grab not supported; "
                    "video recording disabled",
                    wayland,
                )
                return None
            return [
                "ffmpeg", "-y",
                "-f", "x11grab",
                "-framerate", "15",
                "-video_size", "1920x1080",
                "-i", os.environ.get("DISPLAY", ":0.0"),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-pix_fmt", "yuv420p",
            ]

        logger.warning(
            "Video recording not supported on platform '%s'", system
        )
        return None


def _find_macos_screen_index() -> str:
    """Return the AVFoundation screen capture device index.

    Parses `ffmpeg -f avfoundation -list_devices true -i ""` stderr output
    for a line matching `[N] Capture screen`. Falls back to "1" (typical
    primary display index on macOS — index 0 is often FaceTime camera).
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
            capture_output=True,
            text=True,
            timeout=5,
        )
        combined = result.stdout + result.stderr
        match = re.search(r"\[(\d+)\]\s+Capture screen", combined)
        if match:
            return match.group(1)
    except Exception:
        pass
    return "1"
