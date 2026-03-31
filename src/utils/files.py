from __future__ import annotations

from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    """Create directory (and parents) if it does not exist. Returns the Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_filename(name: str, max_len: int = 100) -> str:
    """Convert an arbitrary string to a safe filesystem filename component."""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return safe[:max_len]
