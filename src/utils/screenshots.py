from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver

from src.core.constants import SCREENSHOT_DATE_FORMAT, SCREENSHOT_DIR
from src.core.logger import get_logger
from src.utils.files import ensure_dir, safe_filename

logger = get_logger("screenshots")


class ScreenshotManager:
    """Captures screenshots to a timestamped directory."""

    def __init__(self, base_dir: str = SCREENSHOT_DIR) -> None:
        self._base_dir = Path(base_dir)

    def capture(
        self,
        driver: WebDriver,
        name: str,
        subdirectory: str = "",
    ) -> Optional[str]:
        """Take a screenshot and save it.

        Args:
            driver: The active WebDriver instance.
            name: Descriptive name for the screenshot (used in filename).
            subdirectory: Optional subdirectory under the base screenshots dir.

        Returns:
            The saved file path string, or ``None`` if capture failed.
        """
        timestamp = datetime.now().strftime(SCREENSHOT_DATE_FORMAT)
        safe_name = safe_filename(name)
        filename = f"{timestamp}_{safe_name}.png"

        target_dir = self._base_dir / subdirectory if subdirectory else self._base_dir
        ensure_dir(target_dir)
        file_path = target_dir / filename

        try:
            driver.save_screenshot(str(file_path))
            logger.info("Screenshot saved: %s", file_path)
            return str(file_path)
        except Exception as exc:
            logger.warning("Failed to capture screenshot '%s': %s", name, exc)
            return None
