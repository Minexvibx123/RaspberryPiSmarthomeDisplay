from app.plugins.api import Plugin as PluginBase

from .view import MediaCenterView


class Plugin(PluginBase):
    def create_app_view(self, parent=None):
        return MediaCenterView(self.services.resolve("state_manager"), parent)