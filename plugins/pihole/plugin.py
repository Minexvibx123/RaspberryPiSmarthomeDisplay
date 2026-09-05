from app.plugins.api import Plugin as PluginBase, PluginSettingDef
from app.widgets.registry import register_widget_class
from .widgets import PiHoleControlWidget, PiHoleStatsWidget


class Plugin(PluginBase):
    settings_schema = [PluginSettingDef("url", "Pi-hole URL", "text", "http://pi.hole"), PluginSettingDef("sid", "API Sitzung", "text", "")]

    def register_widgets(self):
        register_widget_class(PiHoleStatsWidget)
        register_widget_class(PiHoleControlWidget)