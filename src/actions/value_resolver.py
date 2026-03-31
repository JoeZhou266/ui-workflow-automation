from __future__ import annotations

from typing import Any, Optional


class ValueResolver:
    """Resolves element values from the JSON definition.

    Currently a thin pass-through. This class is the designated extension
    point for future variable substitution (e.g. ``${today}``, ``${random_email}``).
    """

    def resolve(self, value: Optional[Any]) -> Optional[Any]:
        """Return the resolved value.

        Args:
            value: Raw value from :class:`ElementDefinition`.

        Returns:
            The resolved value, ready to pass to a Selenium action.
        """
        if value is None:
            return None
        if isinstance(value, str):
            return self._resolve_string(value)
        return value

    def _resolve_string(self, value: str) -> str:
        # Extension point: add ${variable} substitution here when needed.
        return value
