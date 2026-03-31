from __future__ import annotations

from selenium.webdriver.remote.webdriver import WebDriver

from src.core.constants import JS_DOCUMENT_READY, JS_JQUERY_ACTIVE
from src.core.logger import get_logger

logger = get_logger("ajax_monitor")


class AjaxMonitor:
    """Provides JavaScript-based browser readiness checks.

    All checks are defensive — they return ``True`` gracefully when the
    required global (e.g. ``jQuery``) does not exist on the page.
    """

    def __init__(self, driver: WebDriver) -> None:
        self._driver = driver

    def is_document_ready(self) -> bool:
        """Return ``True`` when ``document.readyState === 'complete'``."""
        try:
            result = self._driver.execute_script(JS_DOCUMENT_READY)
            return bool(result)
        except Exception as exc:
            logger.debug("document.readyState check failed (non-critical): %s", exc)
            return True  # fail open — don't block on script errors

    def is_jquery_idle(self) -> bool:
        """Return ``True`` when jQuery has no active AJAX requests.

        Returns ``True`` immediately if jQuery is not present on the page.
        """
        try:
            result = self._driver.execute_script(JS_JQUERY_ACTIVE)
            return bool(result)
        except Exception as exc:
            logger.debug("jQuery.active check failed (non-critical): %s", exc)
            return True

    def is_ajax_idle(self) -> bool:
        """Combine all available idle checks into one boolean."""
        return self.is_document_ready() and self.is_jquery_idle()

    def document_ready_condition(self):
        """Return a callable usable as a WebDriverWait expected condition."""
        def _cond(driver: WebDriver) -> bool:
            try:
                return bool(driver.execute_script(JS_DOCUMENT_READY))
            except Exception:
                return True
        return _cond

    def ajax_idle_condition(self):
        """Return a callable usable as a WebDriverWait expected condition."""
        def _cond(driver: WebDriver) -> bool:
            try:
                doc_ready = bool(driver.execute_script(JS_DOCUMENT_READY))
                jquery_idle = bool(driver.execute_script(JS_JQUERY_ACTIVE))
                return doc_ready and jquery_idle
            except Exception:
                return True
        return _cond
