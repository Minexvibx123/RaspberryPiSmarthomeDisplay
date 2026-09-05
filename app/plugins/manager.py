"""PluginManager: discovery, lifecycle and error isolation for all plugins.

Responsibilities:
- discover plugin directories, parse manifests, import modules
- track per-plugin state (``installed``, ``enabled``, ``disabled``, ``error``)
- run enable/disable/reload with full error isolation - a broken plugin can
  never raise through to the UI thread and take down HomePanel
- persist the enabled/disabled choice per plugin so it survives restarts
- hand each plugin a reference to the central ServiceRegistry and its own
  namespaced PluginSettings
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.database import Database
from app.core.service_registry import ServiceRegistry
from app.plugins import discovery
from app.plugins.api import Plugin, PluginManifest
from app.plugins.plugin_settings import PluginSettings
from app.widgets.registry import WIDGET_REGISTRY, unregister_widget_class

logger = logging.getLogger(__name__)

#: states a plugin can be in for the UI
STATE_INSTALLED = "installed"
STATE_ENABLED = "enabled"
STATE_DISABLED = "disabled"
STATE_ERROR = "error"


@dataclass
class PluginInfo:
    id: str
    name: str
    version: str
    description: str
    author: str
    category: str
    plugin_dir: str
    enabled: bool
    state: str
    error: Optional[str] = None


class PluginManager:
    def __init__(self, database: Database, services: ServiceRegistry, plugins_root: Path):
        self.db = database
        self.services = services
        self.plugins_root = Path(plugins_root)
        self._instances: dict[str, Plugin] = {}
        self._registered_widget_types: dict[str, set[str]] = {}
        self._disabled: set[str] = set()
        self._errors: dict[str, str] = {}

    # ------------------------------------------------------------------ #
    # public lifecycle
    # ------------------------------------------------------------------ #
    def load_all(self) -> None:
        """Discover and enable all plugins whose manifest/override says so.

        Never raises: each plugin is handled in isolation and failures are
        recorded as plugin errors. Call once at application startup.
        """
        self.plugins_root.mkdir(parents=True, exist_ok=True)
        pending: dict[str, discovery.DiscoveredPlugin] = {}
        for found in discovery.discover(self.plugins_root):
            if found.error:
                self._errors[found.plugin_id] = found.error
                continue
            pending[found.plugin_id] = found

        while pending:
            loaded_one = False
            for plugin_id, found in list(pending.items()):
                manifest = found.manifest
                requirements = manifest.requires if manifest else []
                missing = [requirement for requirement in requirements if requirement not in pending and requirement not in self._instances]
                if missing:
                    self._errors[plugin_id] = f"Fehlende Plugin-Abhängigkeit: {', '.join(missing)}"
                    pending.pop(plugin_id)
                    loaded_one = True
                elif all(requirement in self._instances for requirement in requirements):
                    self._load_one(found.plugin_dir, manifest)
                    pending.pop(plugin_id)
                    loaded_one = True
            if loaded_one:
                continue

            for plugin_id, found in pending.items():
                requirements = found.manifest.requires if found.manifest else []
                unavailable = [requirement for requirement in requirements if requirement not in self._instances]
                self._errors[plugin_id] = f"Nicht erfüllte Plugin-Abhängigkeiten: {', '.join(unavailable)}"
            break

    def enable(self, plugin_id: str) -> bool:
        """Enable (and load) a plugin. Returns True on success."""
        self.db.set_setting(f"plugin.enabled.{plugin_id}", True)
        self._disabled.discard(plugin_id)
        found = self._find_manifest(plugin_id)
        if found is None:
            return False
        return self._load_one(found.plugin_dir, found.manifest)

    def disable(self, plugin_id: str) -> bool:
        """Disable (and unload) a plugin. Returns True on success."""
        self.db.set_setting(f"plugin.enabled.{plugin_id}", False)
        self._disabled.add(plugin_id)
        self._unload_one(plugin_id)
        return True

    def reload(self, plugin_id: str) -> bool:
        """Unload then re-load a plugin (keeps its enabled state)."""
        self._unload_one(plugin_id)
        manifest = self._find_manifest(plugin_id)
        if manifest is None:
            self._errors[plugin_id] = "Plugin nicht gefunden"
            return False
        ok = self._load_one(manifest.plugin_dir, manifest.manifest)
        return ok

    def unload_all(self) -> None:
        for plugin_id in list(self._instances.keys()):
            self._unload_one(plugin_id)

    # ------------------------------------------------------------------ #
    # queries for the UI
    # ------------------------------------------------------------------ #
    def list_plugins(self) -> list[PluginInfo]:
        result: list[PluginInfo] = []
        for found in self._iter_found():
            pid = found.plugin_id
            fb = self._find_manifest(pid)
            manifest = fb.manifest if fb else None
            enabled = self._is_enabled(pid, manifest)
            state, error = self._state_for(pid, manifest, enabled)
            result.append(
                PluginInfo(
                    id=pid,
                    name=manifest.name if manifest else pid,
                    version=manifest.version if manifest else "-",
                    description=manifest.description if manifest else "",
                    author=manifest.author if manifest else "",
                    category=manifest.category if manifest else "general",
                    plugin_dir=str(found.plugin_dir),
                    enabled=enabled,
                    state=state,
                    error=error,
                )
            )
        return result

    def get_instance(self, plugin_id: str) -> Optional[Plugin]:
        return self._instances.get(plugin_id)

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #
    def _iter_found(self):
        for d in discovery.find_plugin_dirs(self.plugins_root):
            manifest, error = discovery._load_manifest(d)
            if error:
                yield discovery.DiscoveredPlugin(plugin_id=d.name, plugin_dir=d, manifest=None, error=error)
            else:
                yield discovery.DiscoveredPlugin(plugin_id=d.name, plugin_dir=d, manifest=manifest)

    def _find_manifest(self, plugin_id: str) -> Optional[discovery.DiscoveredPlugin]:
        for found in self._iter_found():
            if found.plugin_id == plugin_id:
                return found
        return None

    def _is_enabled(self, plugin_id: str, manifest: Optional[PluginManifest]) -> bool:
        override = self.db.get_setting(f"plugin.enabled.{plugin_id}", None)
        if override is not None:
            return bool(override)
        return bool(manifest and manifest.enabled)

    def _load_one(self, plugin_dir: Path, manifest: Optional[PluginManifest]) -> bool:
        pid = manifest.id if manifest else plugin_dir.name
        # respect disabled override
        if not self._is_enabled(pid, manifest):
            self._disabled.add(pid)
            return True
        if pid in self._instances:
            return True
        missing = [requirement for requirement in (manifest.requires if manifest else []) if requirement not in self._instances]
        if missing:
            self._errors[pid] = f"Nicht erfüllte Plugin-Abhängigkeiten: {', '.join(missing)}"
            return False
        instance, error = discovery.instantiate(plugin_dir)
        if error is not None or instance is None:
            self._errors[pid] = error or "Plugin konnte nicht instanziiert werden"
            return False
        if manifest is not None:
            instance.manifest = manifest
        instance.services = self.services
        instance.settings = PluginSettings(self.db, pid)
        instance.plugin_dir = str(plugin_dir)

        widget_types_before = set(WIDGET_REGISTRY)
        try:
            instance.register_widgets()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Widget registration failed for '%s'", pid)
            self._unregister_widgets(pid, set(WIDGET_REGISTRY) - widget_types_before)
            self._errors[pid] = f"Widget-Registrierung fehlgeschlagen: {exc}"
            return False
        self._registered_widget_types[pid] = set(WIDGET_REGISTRY) - widget_types_before
        try:
            instance.on_load()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Plugin '%s' failed to load", pid)
            self._unregister_widgets(pid)
            self._errors[pid] = f"on_load fehlgeschlagen: {exc}"
            return False

        self._instances[pid] = instance
        self._errors.pop(pid, None)
        self._disabled.discard(pid)
        logger.info("Plugin '%s' v%s geladen", pid, manifest.version if manifest else "?")
        return True

    def _unload_one(self, plugin_id: str) -> None:
        instance = self._instances.pop(plugin_id, None)
        if instance is None:
            return
        try:
            instance.on_unload()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Plugin '%s' failed to unload", plugin_id)
            self._errors[plugin_id] = f"on_unload fehlgeschlagen: {exc}"
        finally:
            self._unregister_widgets(plugin_id)

    def _unregister_widgets(self, plugin_id: str, widget_types: Optional[set[str]] = None) -> None:
        for type_name in widget_types or self._registered_widget_types.pop(plugin_id, set()):
            unregister_widget_class(type_name)

    def _state_for(self, pid: str, manifest: Optional[PluginManifest], enabled: bool) -> tuple[str, Optional[str]]:
        if pid in self._errors:
            return STATE_ERROR, self._errors[pid]
        if not enabled:
            return STATE_DISABLED, None
        if pid in self._instances:
            err = self._instances[pid].error
            if err:
                return STATE_ERROR, err
            return STATE_ENABLED, None
        return STATE_INSTALLED, None
