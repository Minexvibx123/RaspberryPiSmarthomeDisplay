from app.plugins.api import Plugin as PluginBase, PluginSettingDef

from .view import BrowserView


DEFAULT_BOOKMARKS = "Home Assistant|http://homeassistant.local:8123;Router|http://192.168.178.1"


class Plugin(PluginBase):
    settings_schema = [
        PluginSettingDef("home_url", "Startseite", "text", "http://homeassistant.local:8123"),
        PluginSettingDef("bookmarks", "Bookmarks (Name|URL;Name|URL)", "text", DEFAULT_BOOKMARKS),
    ]

    def create_app_view(self, parent=None):
        return BrowserView(
            self.settings.get("home_url", "http://homeassistant.local:8123"),
            self.settings.get("bookmarks", DEFAULT_BOOKMARKS),
            parent=parent,
        )
