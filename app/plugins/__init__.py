"""Plugin system for HomePanel.

Public surface for plugin authors and the rest of the app:
- :class:`Plugin` / :class:`PluginManifest` — the API a plugin implements
- :class:`PluginManager` — discovery + lifecycle + error isolation
- :class:`PluginSettings` — namespaced per-plugin settings
"""
from __future__ import annotations

from app.plugins.api import Plugin, PluginManifest
from app.plugins.manager import PluginManager

__all__ = ["Plugin", "PluginManifest", "PluginManager"]
