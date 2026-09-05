"""Shared, safe condition evaluation for visibility and widget styling."""
from __future__ import annotations

from typing import Any


OPERATORS = [
    "equals", "not_equals", "greater_than", "less_than", "contains",
    "online", "offline", "true", "false",
]


def matches_condition(value: Any, operator: str, expected: Any = "") -> bool:
    """Evaluate a user-configured condition without executing user code."""
    state = "" if value is None else str(value)
    normalized = state.strip().lower()

    if operator == "equals":
        return state == str(expected)
    if operator == "not_equals":
        return state != str(expected)
    if operator == "contains":
        return str(expected).lower() in normalized
    if operator in ("greater_than", "less_than"):
        try:
            return float(state) > float(expected) if operator == "greater_than" else float(state) < float(expected)
        except (TypeError, ValueError):
            return False
    if operator == "online":
        return normalized not in ("", "offline", "unavailable", "unknown", "none")
    if operator == "offline":
        return normalized in ("", "offline", "unavailable", "unknown", "none")
    if operator == "true":
        return normalized in ("true", "on", "yes", "1")
    if operator == "false":
        return normalized in ("false", "off", "no", "0", "")
    return False