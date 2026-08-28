"""Plugin API: the contracts every plugin implements.

A plugin is a directory under ``plugins/`` containing a ``manifest.json`` and
a ``plugin.py`` that defines a ``Plugin`` subclass. The base classes here are
the stable, documented surface plugin authors build against - everything else
in the app must not leak into plugins.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:  # avoid import cycles / heavy deps at plugin import time
    from app.core.service_registry import ServiceRegistry
    from app.plugins.plugin_settings import PluginSettings

logger = logging.getLogger(__name__)


@dataclass
class PluginManifest:
    """Metadata parsed from a plugin's ``manifest.json``."""

    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    enabled: bool = True
    category: str = "general"
    requires: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "PluginManifest":
        """Build a manifest from raw JSON, tolerating missing optional fields."""
        return cls(
            id=str(data.get("id", "")).strip(),
            name=str(data.get("name", "")).strip(),
            version=str(data.get("version", "0.0.0")).strip(),
            description=str(data.get("description", "")),
            author=str(data.get("author", "")),
            enabled=bool(data.get("enabled", True)),
            category=str(data.get("category", "general")),
            requires=list(data.get("requires", [])),
        )

    def validate(self) -> None:
        """Raise ValueError if required fields are missing/invalid."""
        if not self.id:
            raise ValueError("Plugin manifest is missing 'id'")
        if not self.name:
            raise ValueError(f"Plugin '{self.id}' is missing 'name'")
        if not self.version:
            raise ValueError(f"Plugin '{self.id}' is missing 'version'")


class Plugin:
    """Base class plugins subclass.

    Lifecycle:
        1. Discovery imports ``plugin.py`` and instantiates the plugin class.
        2. The PluginManager calls :meth:`on_load` when the plugin is enabled.
        3. :meth:`on_unload` is called when the plugin is disabled or removed.

    Plugins expose their manifest, a read/write ``settings`` handle and the
    central :attr:`services` registry. Every hook is wrapped in try/except by
    the manager so a broken plugin can never take down the panel.
    """

    def __init__(
        self,
        manifest: Optional[PluginManifest] = None,
        services: Optional["ServiceRegistry"] = None,
        settings: Optional["PluginSettings"] = None,
        plugin_dir: Optional[str] = None,
    ) -> None:
        # Discovery instantiates the plugin without arguments; the manager
        # assigns manifest/services/settings/plugin_dir afterwards.
        self.manifest = manifest
        self.services = services
        self.settings = settings
        self.plugin_dir = plugin_dir
        self._error: Optional[str] = None

    # -- lifecycle hooks (override in subclasses) ------------------------- #
    def on_load(self) -> None:
        """Set up the plugin (connections, timers, widget registration)."""

    def on_unload(self) -> None:
        """Tear down anything set up in :meth:`on_load`."""

    def register_widgets(self) -> None:
        """Register widget classes into the global widget registry.

        Default does nothing. Subclasses import their widget classes and call
        :func:`app.widgets.registry.register_widget_class` for each.
        """

    # -- helpers ---------------------------------------------------------- #
    @property
    def id(self) -> str:
        return self.manifest.id if self.manifest else ""

    def fail(self, message: str) -> None:
        """Mark the plugin as errored. Used inside a hook via except block."""
        self._error = message
        logger.error("Plugin '%s' error: %s", self.id, message)

    def clear_error(self) -> None:
        self._error = None

    @property
    def error(self) -> Optional[str]:
        return self._error
