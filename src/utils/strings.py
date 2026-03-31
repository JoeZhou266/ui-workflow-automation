from __future__ import annotations

import re


def slugify(text: str) -> str:
    """Convert a string to a lowercase slug suitable for filenames or IDs."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def truncate(text: str, max_len: int = 200, suffix: str = "...") -> str:
    """Truncate a string to ``max_len`` characters, appending ``suffix`` if cut."""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix
