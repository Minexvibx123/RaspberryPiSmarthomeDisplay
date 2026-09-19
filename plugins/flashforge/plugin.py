from app.plugins.api import Plugin as PluginBase, PluginSettingDef
from app.widgets.registry import register_widget_class
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .widgets import PrintControlWidget, PrintJogWidget, PrinterStatusWidget


class Plugin(PluginBase):
    settings_schema = [PluginSettingDef("host", "Drucker-IP", "text", "192.168.178.112"), PluginSettingDef("port", "TCP-Port", "number", 8899)]

    def register_widgets(self):
        register_widget_class(PrinterStatusWidget)
        register_widget_class(PrintControlWidget)

    def create_app_view(self, parent=None):
        view = QWidget(parent)
        layout = QVBoxLayout(view)
        title = QLabel("Flashforge Adventurer 5M Pro")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        layout.addWidget(title)
        config = {"printer_host": self.settings.get("host", "192.168.178.112"), "printer_port": self.settings.get("port", 8899)}
        layout.addWidget(PrinterStatusWidget(0, config, parent=view))
        layout.addWidget(PrintControlWidget(0, config, parent=view))
        layout.addWidget(PrintJogWidget(config, parent=view), 1)
        return view