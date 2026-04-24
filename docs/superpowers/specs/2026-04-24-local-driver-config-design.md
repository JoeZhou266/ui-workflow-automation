# Local Driver & Browser Binary Configuration

**Date:** 2026-04-24
**Status:** Approved

## Goal

Enable users to run browser tests against a locally installed WebDriver and/or a non-default browser binary by configuring paths through YAML env files or environment variables — without touching Python code.

## Scope

Applies generically to all three supported browsers: Chrome, Firefox, and Edge.

## Decisions

- **Approach:** Flat config fields, consistent with every other `AppConfig` field.
- **CLI flags:** Out of scope. YAML + env vars are sufficient.
- **Backward compat:** `DriverManager(config, driver_path=...)` constructor arg is kept; it takes priority over the config field.

---

## Section 1 — Configuration Layer

### New `AppConfig` fields

| Field | Type | Env var | YAML key | Default |
|---|---|---|---|---|
| `driver_path` | `Optional[str]` | `DRIVER_PATH` | `driver_path` | `None` |
| `browser_binary_path` | `Optional[str]` | `BROWSER_BINARY_PATH` | `browser_binary_path` | `None` |

A new private helper `_resolve_optional(env_key, yaml_key) -> Optional[str]` returns `None` when neither source provides a value, avoiding the empty-string sentinel that `_resolve()` would return.

### YAML env files

All three files (`env.dev.yaml`, `env.qa.yaml`, `env.prod.yaml`) receive the two keys as commented-out lines for discoverability:

```yaml
# driver_path:          # e.g. /usr/local/bin/chromedriver
# browser_binary_path:  # e.g. /opt/google/chrome/chrome
```

---

## Section 2 — `DriverFactory` Changes

`DriverFactory.create()` gains one new parameter:

```python
binary_path: Optional[str] = None
```

It is forwarded to all three `_create_*` methods. Each method applies it with:

```python
if binary_path:
    options.binary_location = binary_path
```

`binary_location` is available on `ChromeOptions`, `FirefoxOptions`, and `EdgeOptions` in Selenium 4.

Existing `driver_path` parameter and webdriver-manager fallback logic are **unchanged**.

---

## Section 3 — `DriverManager` Changes

`DriverManager.__init__` keeps its `driver_path: Optional[str] = None` constructor arg. Effective path resolution:

```
effective_driver_path  = constructor driver_path  OR  config.driver_path
effective_binary_path  = config.browser_binary_path
```

`DriverManager.start()` passes both to `DriverFactory.create()`.

---

## Files Changed

| File | Change |
|---|---|
| `src/core/config.py` | Add `_resolve_optional()`, add `driver_path` and `browser_binary_path` fields |
| `src/driver/driver_factory.py` | Add `binary_path` param to `create()` and all three `_create_*` methods; set `options.binary_location` |
| `src/driver/driver_manager.py` | Read `driver_path` and `browser_binary_path` from config; pass both to factory |
| `configs/env.dev.yaml` | Add commented-out `driver_path` and `browser_binary_path` keys |
| `configs/env.qa.yaml` | Same |
| `configs/env.prod.yaml` | Same |

---

## Testing

- **Unit tests** (no browser): verify `AppConfig` resolves `driver_path` and `browser_binary_path` from both YAML and env vars; verify `None` when absent.
- **Unit test for factory**: mock `webdriver.Chrome` and assert `binary_location` is set on options when `binary_path` is provided; assert it is absent when not.
- **Smoke test**: existing smoke tests continue to pass unchanged (both fields default to `None`, behaviour identical to before).
