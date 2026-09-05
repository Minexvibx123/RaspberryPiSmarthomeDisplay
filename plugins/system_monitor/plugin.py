"""HomePanel system monitoring plugin."""
from __future__ import annotations

from app.plugins.api import Plugin as PluginBase
from app.widgets.registry import register_widget_class

from .widgets import CPUWidget, NetworkWidget, RAMWidget, StorageWidget, SystemServiceWidget


class Plugin(PluginBase):
    def register_widgets(self) -> None:
        for widget_class in (CPUWidget, RAMWidget, StorageWidget, NetworkWidget, SystemServiceWidget):
            register_widget_class(widget_class)