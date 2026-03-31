from __future__ import annotations

# Default timeouts (seconds)
DEFAULT_PAGE_LOAD_TIMEOUT: int = 30
DEFAULT_EXPLICIT_WAIT_TIMEOUT: int = 10
DEFAULT_AJAX_IDLE_TIMEOUT: int = 15
DEFAULT_ELEMENT_WAIT_TIMEOUT: int = 10
DEFAULT_POLL_FREQUENCY_MS: int = 500

# Browser window
DEFAULT_WINDOW_WIDTH: int = 1920
DEFAULT_WINDOW_HEIGHT: int = 1080

# Screenshot
SCREENSHOT_DIR: str = "reports/screenshots"
SCREENSHOT_DATE_FORMAT: str = "%Y%m%d_%H%M%S"

# Retry
DEFAULT_STALE_RETRY_COUNT: int = 3

# AJAX check JS snippets (kept minimal and defensive)
JS_DOCUMENT_READY: str = "return document.readyState === 'complete';"
JS_JQUERY_ACTIVE: str = (
    "return (typeof jQuery !== 'undefined') ? jQuery.active === 0 : true;"
)

# Config
DEFAULT_ENV: str = "dev"
CONFIGS_DIR: str = "configs"
TESTDATA_DIR: str = "testdata/workflows"
