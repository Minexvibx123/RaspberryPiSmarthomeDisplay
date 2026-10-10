from app.plugins.api import Plugin as PluginBase
from app.widgets.energy_dashboard import EnergyDashboardWidget


class Plugin(PluginBase):
    def create_app_view(self, parent=None):
        state_manager = self.services.resolve("state_manager")
        return EnergyDashboardWidget(-1001, {"name": "Energie"}, state_manager, parent)