"""Example plugin proving the HomePanel plugin seam.

Loads cleanly, writes a marker setting and registers nothing custom - the
point is to show the lifecycle works end to end without any fake widgets.
"""
from __future__ import annotations

import logging

from app.plugins.api import Plugin as PluginBase, PluginSettingDef

logger = logging.getLogger(__name__)


class Plugin(PluginBase):
    settings_schema = [
        PluginSettingDef("endpoint", "Lokale Dienstadresse", "text", "http://localhost"),
        PluginSettingDef("poll_interval", "Aktualisierung (Sekunden)", "number", 30),
        PluginSettingDef("notifications", "Benachrichtigungen", "bool", True),
        PluginSettingDef("display_mode", "Anzeige", "select", "compact", ["compact", "detailed"]),
    ]

    def on_load(self) -> None:
        # settings is a namespaced PluginSettings handle (plugin.example_plugin.*)
        if self.settings is not None:
            self.settings.set("loaded", True)
            counter = int(self.settings.get("load_count", 0) or 0) + 1
            self.settings.set("load_count", counter)
        logger.info("Beispiel-Plugin geladen")

    def on_unload(self) -> None:
        logger.info("Beispiel-Plugin entladen")
