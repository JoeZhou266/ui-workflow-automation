# Local Driver & Browser Binary Configuration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose `driver_path` and `browser_binary_path` as optional config fields (YAML + env var) so any browser's WebDriver binary and browser binary can be pointed at local installs without touching Python.

**Architecture:** Add `_resolve_optional` to `AppConfig` for nullable fields; thread both paths through `DriverManager` → `DriverFactory`; each `_create_*` method sets `options.binary_location` when the path is provided. All three browsers (Chrome, Firefox, Edge) use Selenium 4's uniform `binary_location` property.

**Tech Stack:** Python 3.9.13, selenium 4, pytest, PyYAML, python-dotenv, `unittest.mock`

---

## File Map

| File | Action | What changes |
|---|---|---|
| `src/core/config.py` | Modify | Add `_resolve_optional()`; add `driver_path` and `browser_binary_path` fields |
| `src/driver/driver_factory.py` | Modify | Add `binary_path` param to `create()` and all three `_create_*` methods; set `options.binary_location` |
| `src/driver/driver_manager.py` | Modify | Read `driver_path` + `browser_binary_path` from config; pass `binary_path` to factory |
| `configs/env.dev.yaml` | Modify | Add commented-out `driver_path` and `browser_binary_path` keys |
| `configs/env.qa.yaml` | Modify | Same |
| `configs/env.prod.yaml` | Modify | Same |
| `tests/unit/test_app_config.py` | Create | Unit tests for new AppConfig fields (YAML + env var resolution) |
| `tests/unit/test_driver_factory.py` | Create | Unit tests for `binary_path` applied to browser options |
| `tests/unit/test_driver_manager.py` | Create | Unit tests for path threading from config to factory |

---

### Task 1: AppConfig — `_resolve_optional` + new fields

**Files:**
- Modify: `src/core/config.py`
- Create: `tests/unit/test_app_config.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_app_config.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_app_config.py -v
```

Expected: `AttributeError: 'AppConfig' object has no attribute 'driver_path'` (or similar FAIL on every test).

- [ ] **Step 3: Add `_resolve_optional` and new fields to `AppConfig`**

In `src/core/config.py`, add the helper method after `_resolve_bool`:

```python
def _resolve_optional(self, env_key: str, yaml_key: str) -> Optional[str]:
    env_val = os.environ.get(env_key)
    if env_val is not None and env_val != "":
        return env_val
    yaml_val = self._data.get(yaml_key)
    if yaml_val is not None:
        return str(yaml_val)
    return None
```

In `AppConfig.__init__`, append after the `window_height` line:

```python
self.driver_path: Optional[str] = self._resolve_optional("DRIVER_PATH", "driver_path")
self.browser_binary_path: Optional[str] = self._resolve_optional("BROWSER_BINARY_PATH", "browser_binary_path")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_app_config.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/core/config.py tests/unit/test_app_config.py
git commit -m "feat: add driver_path and browser_binary_path to AppConfig"
```

---

### Task 2: DriverFactory — `binary_path` parameter

**Files:**
- Modify: `src/driver/driver_factory.py`
- Create: `tests/unit/test_driver_factory.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_driver_factory.py`:

```python
"""Unit tests for DriverFactory binary_path — no browser required."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.driver.driver_factory import DriverFactory


class TestDriverFactoryBinaryPath:
    """Verify options.binary_location is set iff binary_path is provided."""

    # --- Chrome ---

    @patch("selenium.webdriver.Chrome")
    @patch("src.driver.driver_factory.ChromeService")
    def test_chrome_sets_binary_location_when_provided(self, mock_service, mock_chrome):
        mock_chrome.return_value = MagicMock()
        DriverFactory._create_chrome(
            headless=False, width=1920, height=1080,
            driver_path="/fake/chromedriver", binary_path="/opt/chrome",
        )
        options = mock_chrome.call_args.kwargs["options"]
        assert options.binary_location == "/opt/chrome"

    @patch("selenium.webdriver.Chrome")
    @patch("src.driver.driver_factory.ChromeService")
    def test_chrome_binary_location_unchanged_when_none(self, mock_service, mock_chrome):
        mock_chrome.return_value = MagicMock()
        DriverFactory._create_chrome(
            headless=False, width=1920, height=1080,
            driver_path="/fake/chromedriver", binary_path=None,
        )
        options = mock_chrome.call_args.kwargs["options"]
        assert options.binary_location == ""  # Selenium 4 default

    # --- Firefox ---

    @patch("selenium.webdriver.Firefox")
    @patch("src.driver.driver_factory.FirefoxService")
    def test_firefox_sets_binary_location_when_provided(self, mock_service, mock_firefox):
        mock_firefox.return_value = MagicMock()
        DriverFactory._create_firefox(
            headless=False, width=1920, height=1080,
            driver_path="/fake/geckodriver", binary_path="/usr/bin/firefox",
        )
        options = mock_firefox.call_args.kwargs["options"]
        assert options.binary_location == "/usr/bin/firefox"

    @patch("selenium.webdriver.Firefox")
    @patch("src.driver.driver_factory.FirefoxService")
    def test_firefox_binary_location_unchanged_when_none(self, mock_service, mock_firefox):
        mock_firefox.return_value = MagicMock()
        DriverFactory._create_firefox(
            headless=False, width=1920, height=1080,
            driver_path="/fake/geckodriver", binary_path=None,
        )
        options = mock_firefox.call_args.kwargs["options"]
        assert options.binary_location == ""

    # --- Edge ---

    @patch("selenium.webdriver.Edge")
    @patch("src.driver.driver_factory.EdgeService")
    def test_edge_sets_binary_location_when_provided(self, mock_service, mock_edge):
        mock_edge.return_value = MagicMock()
        DriverFactory._create_edge(
            headless=False, width=1920, height=1080,
            driver_path="/fake/msedgedriver", binary_path="/usr/bin/msedge",
        )
        options = mock_edge.call_args.kwargs["options"]
        assert options.binary_location == "/usr/bin/msedge"

    @patch("selenium.webdriver.Edge")
    @patch("src.driver.driver_factory.EdgeService")
    def test_edge_binary_location_unchanged_when_none(self, mock_service, mock_edge):
        mock_edge.return_value = MagicMock()
        DriverFactory._create_edge(
            headless=False, width=1920, height=1080,
            driver_path="/fake/msedgedriver", binary_path=None,
        )
        options = mock_edge.call_args.kwargs["options"]
        assert options.binary_location == ""

    # --- create() dispatches binary_path ---

    @patch("selenium.webdriver.Chrome")
    @patch("src.driver.driver_factory.ChromeService")
    def test_create_passes_binary_path_to_chrome(self, mock_service, mock_chrome):
        mock_instance = MagicMock()
        mock_chrome.return_value = mock_instance
        mock_instance.set_page_load_timeout = MagicMock()
        mock_instance.implicitly_wait = MagicMock()
        mock_instance.set_window_size = MagicMock()

        DriverFactory.create(
            browser="chrome",
            driver_path="/fake/chromedriver",
            binary_path="/opt/chrome",
        )
        options = mock_chrome.call_args.kwargs["options"]
        assert options.binary_location == "/opt/chrome"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_driver_factory.py -v
```

Expected: `TypeError` on `_create_chrome` (unexpected keyword argument `binary_path`) or similar FAIL on every test.

- [ ] **Step 3: Update `DriverFactory`**

In `src/driver/driver_factory.py`:

**3a. Add `binary_path` to `create()`** — insert after `driver_path: Optional[str] = None,`:

```python
binary_path: Optional[str] = None,
```

**3b. Update all three dispatch calls in `create()`:**

```python
if browser_type == BrowserType.CHROME:
    driver = cls._create_chrome(headless, window_width, window_height, driver_path, binary_path)
elif browser_type == BrowserType.FIREFOX:
    driver = cls._create_firefox(headless, window_width, window_height, driver_path, binary_path)
elif browser_type == BrowserType.EDGE:
    driver = cls._create_edge(headless, window_width, window_height, driver_path, binary_path)
```

**3c. Update `_create_chrome` signature and body:**

```python
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
```

**3d. Update `_create_firefox` signature and body:**

```python
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
```

**3e. Update `_create_edge` signature and body:**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_driver_factory.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/driver/driver_factory.py tests/unit/test_driver_factory.py
git commit -m "feat: add binary_path to DriverFactory, set options.binary_location for all browsers"
```

---

### Task 3: DriverManager — thread paths from config to factory

**Files:**
- Modify: `src/driver/driver_manager.py`
- Create: `tests/unit/test_driver_manager.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_driver_manager.py`:

```python
"""Unit tests for DriverManager path threading — no browser required."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.driver.driver_manager import DriverManager


def _make_config(driver_path=None, binary_path=None):
    config = MagicMock()
    config.browser = "chrome"
    config.headless = False
    config.window_width = 1920
    config.window_height = 1080
    config.page_load_timeout = 30
    config.implicit_wait = 0
    config.driver_path = driver_path
    config.browser_binary_path = binary_path
    return config


class TestDriverManagerPaths:

    @patch("src.driver.driver_manager.DriverFactory.create")
    def test_driver_path_from_config_is_passed_to_factory(self, mock_create):
        mock_create.return_value = MagicMock()
        manager = DriverManager(_make_config(driver_path="/usr/local/bin/chromedriver"))
        manager.start()
        assert mock_create.call_args.kwargs["driver_path"] == "/usr/local/bin/chromedriver"

    @patch("src.driver.driver_manager.DriverFactory.create")
    def test_constructor_driver_path_takes_priority_over_config(self, mock_create):
        mock_create.return_value = MagicMock()
        config = _make_config(driver_path="/config/chromedriver")
        manager = DriverManager(config, driver_path="/explicit/chromedriver")
        manager.start()
        assert mock_create.call_args.kwargs["driver_path"] == "/explicit/chromedriver"

    @patch("src.driver.driver_manager.DriverFactory.create")
    def test_binary_path_from_config_is_passed_to_factory(self, mock_create):
        mock_create.return_value = MagicMock()
        manager = DriverManager(_make_config(binary_path="/opt/google/chrome"))
        manager.start()
        assert mock_create.call_args.kwargs["binary_path"] == "/opt/google/chrome"

    @patch("src.driver.driver_manager.DriverFactory.create")
    def test_none_paths_when_config_has_none(self, mock_create):
        mock_create.return_value = MagicMock()
        manager = DriverManager(_make_config())
        manager.start()
        assert mock_create.call_args.kwargs["driver_path"] is None
        assert mock_create.call_args.kwargs["binary_path"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_driver_manager.py -v
```

Expected: `AssertionError` — `binary_path` not in kwargs, and `driver_path` not reading from config.

- [ ] **Step 3: Update `DriverManager`**

Replace the `__init__` body in `src/driver/driver_manager.py`:

```python
def __init__(self, config: AppConfig, driver_path: Optional[str] = None) -> None:
    self._config = config
    self._driver_path = driver_path or config.driver_path
    self._binary_path = config.browser_binary_path
    self._driver: Optional[WebDriver] = None
```

Replace the `start()` body:

```python
def start(self) -> WebDriver:
    """Create the driver. Called automatically by the context manager."""
    self._driver = DriverFactory.create(
        browser=self._config.browser,
        headless=self._config.headless,
        window_width=self._config.window_width,
        window_height=self._config.window_height,
        page_load_timeout=self._config.page_load_timeout,
        implicit_wait=self._config.implicit_wait,
        driver_path=self._driver_path,
        binary_path=self._binary_path,
    )
    logger.info("WebDriver started: %s", self._config.browser)
    return self._driver
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_driver_manager.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Run all unit tests to confirm no regressions**

```bash
pytest tests/unit/ -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/driver/driver_manager.py tests/unit/test_driver_manager.py
git commit -m "feat: thread driver_path and browser_binary_path from AppConfig through DriverManager"
```

---

### Task 4: YAML env files — add discoverable commented keys

**Files:**
- Modify: `configs/env.dev.yaml`
- Modify: `configs/env.qa.yaml`
- Modify: `configs/env.prod.yaml`

- [ ] **Step 1: Update `configs/env.dev.yaml`**

Append to the end of the file:

```yaml
# driver_path:          # e.g. /usr/local/bin/chromedriver  (leave commented to use webdriver-manager)
# browser_binary_path:  # e.g. /opt/google/chrome/chrome    (leave commented to use system default)
```

- [ ] **Step 2: Update `configs/env.qa.yaml`**

Append to the end of the file:

```yaml
# driver_path:          # e.g. /usr/local/bin/chromedriver  (leave commented to use webdriver-manager)
# browser_binary_path:  # e.g. /opt/google/chrome/chrome    (leave commented to use system default)
```

- [ ] **Step 3: Update `configs/env.prod.yaml`**

Append to the end of the file:

```yaml
# driver_path:          # e.g. /usr/local/bin/chromedriver  (leave commented to use webdriver-manager)
# browser_binary_path:  # e.g. /opt/google/chrome/chrome    (leave commented to use system default)
```

- [ ] **Step 4: Run the full unit suite to confirm nothing broke**

```bash
pytest tests/unit/ -v
```

Expected: all tests PASS. (Commented-out YAML keys parse as absent — `_resolve_optional` returns `None` as before.)

- [ ] **Step 5: Commit**

```bash
git add configs/env.dev.yaml configs/env.qa.yaml configs/env.prod.yaml
git commit -m "docs: add commented driver_path and browser_binary_path to all env YAML files"
```
