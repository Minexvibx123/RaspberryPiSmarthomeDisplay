from app.plugins.api import Plugin as PluginBase
from app.widgets.registry import register_widget_class
from .widgets import NetworkDeviceWidget


class Plugin(PluginBase):
    def register_widgets(self): register_widget_class(NetworkDeviceWidget)