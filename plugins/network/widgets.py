from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QPushButton

from app.widgets.base import BaseWidget, PropertyDef
from .api import NetworkMonitor


class _Probe(QThread):
    done = Signal(object)
    def __init__(self, host, parent):
        super().__init__(parent); self.host = host
    def run(self): self.done.emit(NetworkMonitor().probe(self.host))


_ACTIVE_SCANS: set[QThread] = set()


class _NetworkScan(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, cidr):
        super().__init__()
        self.cidr = cidr

    def run(self):
        try:
            self.done.emit(NetworkMonitor().discover(self.cidr or None))
        except (OSError, RuntimeError, ValueError) as exc:
            self.failed.emit(str(exc))


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


class NetworkInventoryWidget(BaseWidget):
    type_name = "network_inventory"
    display_name = "Netzwerk-Inventar"
    category = "Netzwerk"
    default_size = (380, 280)
    PROPERTY_SCHEMA = [
        PropertyDef("cidr", "Privates IPv4-Netz (optional)", "text", "", group="Scan"),
    ]

    def build_ui(self):
        self.scan_button = QPushButton("Lokales Netz scannen")
        self.scan_button.clicked.connect(self.start_scan)
        self.content_layout.addWidget(self.scan_button)
        self.status_label = QLabel("Manueller Ping-Scan, keine Portprüfung")
        self.status_label.setWordWrap(True)
        self.content_layout.addWidget(self.status_label)
        self.results = QPlainTextEdit()
        self.results.setReadOnly(True)
        self.results.setPlaceholderText("Gefundene Geräte erscheinen hier.")
        self.results.setMaximumBlockCount(256)
        self.content_layout.addWidget(self.results, 1)

    def start_scan(self):
        if getattr(self, "_scan_job", None) and self._scan_job.isRunning():
            return
        self.scan_button.setEnabled(False)
        self.status_label.setText("Suche aktive Hosts im privaten IPv4-Netz …")
        job = _NetworkScan(str(self.get_prop("cidr", "")).strip())
        self._scan_job = job
        _ACTIVE_SCANS.add(job)
        job.done.connect(self.show_results)
        job.failed.connect(self.show_error)
        job.finished.connect(lambda current=job: _ACTIVE_SCANS.discard(current))
        job.finished.connect(job.deleteLater)
        job.start()

    def show_results(self, devices):
        self._scan_job = None
        self.scan_button.setEnabled(True)
        if not devices:
            self.status_label.setText("Keine antwortenden Hosts gefunden.")
            self.results.clear()
            return
        self.status_label.setText(f"{len(devices)} aktive Hosts gefunden")
        self.results.setPlainText("\n".join(
            f"{device['host']}  {device.get('name') or 'Name unbekannt'}  "
            f"{device.get('response_ms') if device.get('response_ms') is not None else '-'} ms"
            for device in devices
        ))

    def show_error(self, message):
        self._scan_job = None
        self.scan_button.setEnabled(True)
        self.status_label.setText(message)