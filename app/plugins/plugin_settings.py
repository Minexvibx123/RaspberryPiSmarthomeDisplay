"""Per-plugin settings with a namespaced key layout.

Plugin settings are stored in the same SQLite ``settings`` table as every
other setting, but under the ``plugin.<id>.<key>`` namespace so plugins can
never collide with core settings or with each other.
"""
from __future__ import annotations

from typing import Any, Optional

from app.core.database import Database


class PluginSettings:
    """Namespaced read/write settings handle handed to each plugin."""

    def __init__(self, db: Database, plugin_id: str) -> None:
        self._db = db
        self._ns = f"plugin.{plugin_id}"

    def _key(self, key: str) -> str:
        return f"{self._ns}.{key}"

    def get(self, key: str, default: Any = None) -> Any:
        return self._db.get_setting(self._key(key), default)

    def set(self, key: str, value: Any) -> None:
        self._db.set_setting(self._key(key), value)

    def delete(self, key: str) -> None:
        self._db.set_setting(self._key(key), None)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<PluginSettings '{self._ns}'>"
