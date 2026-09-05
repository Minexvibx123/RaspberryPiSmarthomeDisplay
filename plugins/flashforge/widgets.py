from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton

from app.widgets.base import BaseWidget

from .api import FlashforgeClient


class _StatusFetch(QThread):
    ready = Signal(object)
    failed = Signal(str)

    def __init__(self, host, port, parent=None):
        super().__init__(parent)
        self.host, self.port = host, port

    def run(self):
        try:
            self.ready.emit(FlashforgeClient(self.host, self.port).status())
        except Exception as exc:
            self.failed.emit(str(exc))


class PrinterStatusWidget(BaseWidget):
    type_name = "flashforge_status"
    display_name = "Flashforge Status"
    category = "Hardware"
    icon = "PRINT"
    default_size = (280, 180)

    def build_ui(self):
        self.status = QLabel("Verbinde...")
        self.status.setStyleSheet("font-size: 24px; font-weight: 800;")
        self.details = QLabel("")
        self.details.setWordWrap(True)
        self.content_layout.addWidget(self.status)
        self.content_layout.addWidget(self.details)
        self.content_layout.addStretch()
        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.refresh_from_state)
        self.timer.start()

    def refresh_from_state(self):
        if getattr(self, "fetch", None) and self.fetch.isRunning():
            return
        host = self.config.get("printer_host", "192.168.178.112")
        port = int(self.config.get("printer_port", 8899))
        self.fetch = _StatusFetch(host, port, self)
        self.fetch.ready.connect(self._show_status)
        self.fetch.failed.connect(lambda error: self.status.setText("Offline"))
        self.fetch.finished.connect(self.fetch.deleteLater)
        self.fetch.start()

    def _show_status(self, data):
        self.status.setText(str(data["status"]).replace("_", " ").title())
        nozzle = data["nozzle"] or (0, 0)
        bed = data["bed"] or (0, 0)
        self.details.setText(f"Fortschritt: {data['progress']} %\nDüse: {nozzle[0]}/{nozzle[1]} C  Bett: {bed[0]}/{bed[1]} C")


class PrintControlWidget(BaseWidget):
    type_name = "flashforge_controls"
    display_name = "Flashforge Steuerung"
    category = "Hardware"
    icon = "CTRL"
    default_size = (340, 100)

    def build_ui(self):
        row = QHBoxLayout()
        for label, command in (("Pause", "M25"), ("Fortsetzen", "M24"), ("Abbrechen", "M26")):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, cmd=command: self._run(cmd))
            row.addWidget(button)
        self.content_layout.addLayout(row)

    def refresh_from_state(self):
        pass

    def _run(self, command):
        if command == "M26" and QMessageBox.question(self, "Druck abbrechen", "Druck wirklich abbrechen?") != QMessageBox.Yes:
            return
        thread = _StatusFetch(self.config.get("printer_host", "192.168.178.112"), int(self.config.get("printer_port", 8899)), self)
        thread.run = lambda: FlashforgeClient(thread.host, thread.port).command(command)
        thread.start()