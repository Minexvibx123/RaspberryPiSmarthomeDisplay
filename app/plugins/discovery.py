"""Plugin discovery: turn directories under ``plugins/`` into loaded plugins.

The on-disk contract for a plugin:

.. code-block:: text

    plugins/<id>/
        manifest.json      # plugin metadata (see PluginManifest)
        plugin.py          # must define a `Plugin` subclass
        ...                # optional supporting modules (api.py, widgets/, ...)

Discovery never raises on a single broken plugin - it records the error and
moves on. That is the core error-isolation promise.
"""
from __future__ import annotations

import importlib.util
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.plugins.api import Plugin, PluginManifest

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredPlugin:
    """Result of discovering a single plugin directory."""

    plugin_id: str
    plugin_dir: Path
    manifest: Optional[PluginManifest]
    error: Optional[str] = None


def find_plugin_dirs(root: Path) -> list[Path]:
    """Return subdirectories of ``root`` that contain at least a manifest."""
    if not root.is_dir():
        return []
    return [p for p in sorted(root.iterdir()) if p.is_dir() and (p / "manifest.json").is_file()]


def _load_manifest(plugin_dir: Path) -> tuple[Optional[PluginManifest], Optional[str]]:
    manifest_path = plugin_dir / "manifest.json"
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = PluginManifest.from_dict(data)
        manifest.validate()
        return manifest, None
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        return None, f"Ungültiges Manifest: {exc}"


def discover(root: Path) -> list[DiscoveredPlugin]:
    """Scan ``root`` and return one :class:`DiscoveredPlugin` per valid dir."""
    result: list[DiscoveredPlugin] = []
    for plugin_dir in find_plugin_dirs(root):
        plugin_id = plugin_dir.name
        manifest, error = _load_manifest(plugin_dir)
        if error:
            logger.warning("Plugin '%s': %s", plugin_id, error)
            result.append(DiscoveredPlugin(plugin_id=plugin_id, plugin_dir=plugin_dir, manifest=None, error=error))
            continue
        result.append(DiscoveredPlugin(plugin_id=plugin_id, plugin_dir=plugin_dir, manifest=manifest))
    return result


def instantiate(plugin_dir: Path) -> tuple[Optional[Plugin], Optional[str]]:
    """Import ``plugin.py`` from ``plugin_dir`` and return a Plugin instance.

    Returns ``(instance, None)`` on success or ``(None, error_message)`` if
    anything goes wrong (missing module, missing class, bad import, ...).
    """
    plugin_py = plugin_dir / "plugin.py"
    if not plugin_py.is_file():
        return None, "plugin.py fehlt"

    # A unique module name avoids collisions between same-named plugins.
    module_name = f"_homepanel_plugin_{plugin_dir.name}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, plugin_py)
        if spec is None or spec.loader is None:
            return None, "plugin.py konnte nicht geladen werden"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - plugin import failure must be isolated
        logger.exception("Failed to import plugin from %s", plugin_dir)
        return None, f"Import fehlgeschlagen: {exc}"

    plugin_class = getattr(module, "Plugin", None)
    if plugin_class is None:
        return None, "plugin.py definiert keine 'Plugin'-Klasse"
    try:
        instance = plugin_class()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to instantiate plugin from %s", plugin_dir)
        return None, f"Instanziierung fehlgeschlagen: {exc}"
    return instance, None
