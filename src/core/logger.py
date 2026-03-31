from __future__ import annotations

import logging
import sys
from typing import Optional


_FRAMEWORK_LOGGER_NAME = "workflow_framework"

_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a child logger under the framework root logger.

    Args:
        name: Sub-name appended to the framework root, e.g. ``'workflow_engine'``.
              If ``None`` the root framework logger is returned.
    """
    if name:
        return logging.getLogger(f"{_FRAMEWORK_LOGGER_NAME}.{name}")
    return logging.getLogger(_FRAMEWORK_LOGGER_NAME)


def configure_logging(level: str = "INFO") -> None:
    """Configure the root framework logger with a stream handler.

    Should be called once at startup (e.g. in conftest or CLI entry point).
    Subsequent calls are idempotent — handlers are not added twice.
    """
    root = logging.getLogger(_FRAMEWORK_LOGGER_NAME)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(numeric_level)

    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
        handler.setFormatter(formatter)
        root.addHandler(handler)
