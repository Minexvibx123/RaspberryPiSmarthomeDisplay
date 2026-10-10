from app.plugins.api import Plugin as PluginBase

from .view import DeviceCenterView


class Plugin(PluginBase):
    def create_app_view(self, parent=None):
        return DeviceCenterView(self.services.resolve("state_manager"), parent)