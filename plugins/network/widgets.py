from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QLabel

from app.widgets.base import BaseWidget, PropertyDef
from .api import NetworkMonitor


class _Probe(QThread):
    done = Signal(object)
    def __init__(self, host, parent):
        super().__init__(parent); self.host = host
    def run(self): self.done.emit(NetworkMonitor().probe(self.host))


class NetworkDeviceWidget(BaseWidget):
    type_name = "network_device"
    display_name = "Netzwerkgerät"
    category = "Netzwerk"
    default_size = (220, 110)
    PROPERTY_SCHEMA = [PropertyDef("host", "IP oder Hostname", "text", "127.0.0.1")]
    def build_ui(self):
        self.label = QLabel("Prüfe..."); self.content_layout.addWidget(self.label)
    def refresh_from_state(self):
        self.job = _Probe(self.get_prop("host"), self); self.job.done.connect(self.show_result); self.job.start()
    def show_result(self, result):
        self.label.setText(f"{'Online' if result['online'] else 'Offline'}\n{result['response_ms'] or '-'} ms")