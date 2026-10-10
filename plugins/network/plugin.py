from app.plugins.api import Plugin as PluginBase
from app.widgets.registry import register_widget_class
from .widgets import NetworkDeviceWidget, NetworkInventoryWidget


class Plugin(PluginBase):
    def register_widgets(self):
        register_widget_class(NetworkDeviceWidget)
        register_widget_class(NetworkInventoryWidget)