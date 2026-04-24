from __future__ import annotations

from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import WebDriver

from src.core.enums import BrowserType
from src.core.logger import get_logger

logger = get_logger("driver_factory")


class DriverFactory:
    """Creates configured WebDriver instances.

    Supports Chrome (default), Firefox, and Edge.
    Uses webdriver-manager for automatic driver binary resolution when
    ``driver_path`` is not provided.
    """

    @classmethod
    def create(
        cls,
        browser: str = BrowserType.CHROME,
        headless: bool = False,
        window_width: int = 1920,
        window_height: int = 1080,
        page_load_timeout: int = 30,
        implicit_wait: int = 0,
        driver_path: Optional[str] = None,
        binary_path: Optional[str] = None,
    ) -> WebDriver:
        """Create and return a configured WebDriver.

        Args:
            browser: Browser name — ``'chrome'``, ``'firefox'``, or ``'edge'``.
            headless: Run without a visible browser window.
            window_width: Viewport width in pixels.
            window_height: Viewport height in pixels.
            page_load_timeout: Seconds before a page load is considered timed out.
            implicit_wait: Implicit wait seconds (keep at 0 for explicit-only strategy).
            driver_path: Optional path to the WebDriver binary. If omitted,
                         webdriver-manager resolves it automatically.
            binary_path: Optional path to the browser binary. If omitted, the
                         browser installed in the default system location is used.

        Returns:
            A ready-to-use :class:`WebDriver` instance.
        """
        browser_type = BrowserType(browser.lower())
        logger.info(
            "Creating %s driver (headless=%s, %dx%d)",
            browser_type.value, headless, window_width, window_height,
        )

        if browser_type == BrowserType.CHROME:
            driver = cls._create_chrome(headless, window_width, window_height, driver_path, binary_path)
        elif browser_type == BrowserType.FIREFOX:
            driver = cls._create_firefox(headless, window_width, window_height, driver_path, binary_path)
        elif browser_type == BrowserType.EDGE:
            driver = cls._create_edge(headless, window_width, window_height, driver_path, binary_path)
        else:
            raise ValueError(f"Unsupported browser: {browser}")

        driver.set_page_load_timeout(page_load_timeout)
        driver.implicitly_wait(implicit_wait)

        if not headless:
            driver.set_window_size(window_width, window_height)

        return driver

    @classmethod
    def _create_chrome(
        cls,
        headless: bool,
        width: int,
        height: int,
        driver_path: Optional[str],
        binary_path: Optional[str],
    ) -> WebDriver:
        options = ChromeOptions()
        if binary_path:
            options.binary_location = binary_path
        if headless:
            options.add_argument("--headless=new")
        options.add_argument(f"--window-size={width},{height}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        if driver_path:
            service = ChromeService(executable_path=driver_path)
        else:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = ChromeService(ChromeDriverManager().install())
            except ImportError:
                service = ChromeService()

        return webdriver.Chrome(service=service, options=options)

    @classmethod
    def _create_firefox(
        cls,
        headless: bool,
        width: int,
        height: int,
        driver_path: Optional[str],
        binary_path: Optional[str],
    ) -> WebDriver:
        options = FirefoxOptions()
        if binary_path:
            options.binary_location = binary_path
        if headless:
            options.add_argument("--headless")
        options.add_argument(f"--width={width}")
        options.add_argument(f"--height={height}")

        if driver_path:
            service = FirefoxService(executable_path=driver_path)
        else:
            try:
                from webdriver_manager.firefox import GeckoDriverManager
                service = FirefoxService(GeckoDriverManager().install())
            except ImportError:
                service = FirefoxService()

        return webdriver.Firefox(service=service, options=options)

    @classmethod
    def _create_edge(
        cls,
        headless: bool,
        width: int,
        height: int,
        driver_path: Optional[str],
        binary_path: Optional[str],
    ) -> WebDriver:
        options = EdgeOptions()
        if binary_path:
            options.binary_location = binary_path
        if headless:
            options.add_argument("--headless=new")
        options.add_argument(f"--window-size={width},{height}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        if driver_path:
            service = EdgeService(executable_path=driver_path)
        else:
            try:
                from webdriver_manager.microsoft import EdgeChromiumDriverManager
                service = EdgeService(EdgeChromiumDriverManager().install())
            except ImportError:
                service = EdgeService()

        return webdriver.Edge(service=service, options=options)
