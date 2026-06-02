from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from src.utils.files import ensure_dir


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


def configure_logging(
    level: str = "INFO",
    log_file_path: Optional[str] = None,
) -> None:
    """Configure the root framework logger with a stream handler and optional rotating file handler.

    When log_file_path is None (default), only a StreamHandler writing to stdout is added.
    When log_file_path is set, a TimedRotatingFileHandler is added alongside the StreamHandler.

    Idempotent: each handler type is added at most once. Calling again with a
    different log_file_path has no effect (path is not hot-swapped).
    """
    root = logging.getLogger(_FRAMEWORK_LOGGER_NAME)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(numeric_level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Stream handler — always present, added at most once.
    # IMPORTANT: use exact type check (type(h) is logging.StreamHandler), NOT isinstance,
    # because TimedRotatingFileHandler inherits from StreamHandler via FileHandler.
    # isinstance would false-positive when only a file handler is present.
    if not any(type(h) is logging.StreamHandler for h in root.handlers):
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(numeric_level)
        sh.setFormatter(formatter)
        root.addHandler(sh)

    # File handler — only when path is configured, added at most once.
    if log_file_path and not any(
        isinstance(h, logging.handlers.TimedRotatingFileHandler) for h in root.handlers
    ):
        ensure_dir(Path(log_file_path).parent)
        fh = logging.handlers.TimedRotatingFileHandler(
            log_file_path,
            when="midnight",
            backupCount=30,
            encoding="utf-8",
        )
        fh.setLevel(numeric_level)
        fh.setFormatter(formatter)
        root.addHandler(fh)
