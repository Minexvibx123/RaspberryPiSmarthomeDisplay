"""System monitor widgets backed by the local SystemMetrics API."""
from __future__ import annotations

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton

from app.widgets.base import BaseWidget, PropertyDef

from .api import metrics


def _format_bytes(value: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return "0 B"


class _MetricWidget(BaseWidget):
    category = "System"
    default_size = (220, 130)

    def build_ui(self) -> None:
        self.title = QLabel(self.display_name)
        self.title.setStyleSheet("font-weight: 700;")
        self.value = QLabel("-")
        self.value.setStyleSheet("font-size: 24px; font-weight: 800;")
        self.detail = QLabel("")
        self.content_layout.addWidget(self.title)
        self.content_layout.addWidget(self.value)
        self.content_layout.addWidget(self.detail)
        self.content_layout.addStretch()
        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self._safe_refresh_from_state)
        self.timer.start()


class CPUWidget(_MetricWidget):
    type_name = "system_cpu"
    display_name = "CPU"
    icon = "CPU"

    def refresh_from_state(self) -> None:
        data = metrics.snapshot()
        temperature = data["temperature"]
        self.value.setText(f"{data['cpu_percent']:.1f} %")
        self.detail.setText(f"Temperatur: {temperature:.1f} C" if temperature is not None else "Temperatur nicht verfügbar")


class RAMWidget(_MetricWidget):
    type_name = "system_ram"
    display_name = "RAM"
    icon = "RAM"

    def refresh_from_state(self) -> None:
        data = metrics.snapshot()
        self.value.setText(f"{data['memory_percent']:.1f} %")
        self.detail.setText(f"{_format_bytes(data['memory_used'])} / {_format_bytes(data['memory_total'])}")


class StorageWidget(_MetricWidget):
    type_name = "system_storage"
    display_name = "Speicher"
    icon = "STO"

    def refresh_from_state(self) -> None:
        data = metrics.snapshot()
        self.value.setText(f"{data['storage_percent']:.1f} %")
        self.detail.setText(f"{_format_bytes(data['storage_used'])} / {_format_bytes(data['storage_total'])}")


class NetworkWidget(_MetricWidget):
    type_name = "system_network"
    display_name = "Netzwerk"
    icon = "NET"

    def refresh_from_state(self) -> None:
        data = metrics.snapshot()
        self.value.setText(f"Down {_format_bytes(data['download_rate'])}/s")
        self.detail.setText(f"Up {_format_bytes(data['upload_rate'])}/s")


class _ServiceStatus(QThread):
    done = Signal(object)

    def __init__(self, service_names, parent):
        super().__init__(parent)
        self.service_names = service_names

    def run(self) -> None:
        import subprocess
        results = []
        for name in self.service_names:
            active = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=5).stdout.strip()
            results.append((name, active))
        self.done.emit(results)


class _ServiceAction(QThread):
    done = Signal(object)

    def __init__(self, action, service_name, parent):
        super().__init__(parent)
        self.action, self.service_name = action, service_name

    def run(self) -> None:
        import subprocess
        try:
            subprocess.run(["sudo", "-n", "systemctl", self.action, self.service_name], capture_output=True, text=True, timeout=15, check=True)
            self.done.emit(None)
        except Exception as exc:  # noqa: BLE001
            self.done.emit(str(exc))


class SystemServiceWidget(BaseWidget):
    type_name = "system_services"
    display_name = "Systemdienste"
    category = "System"
    default_size = (300, 240)
    PROPERTY_SCHEMA = [
        PropertyDef("service_names", "Dienste (Komma-getrennt)", "text", "homepanel.service", group="System"),
    ]

    def build_ui(self) -> None:
        self.list = QListWidget()
        self.content_layout.addWidget(self.list, 1)
        row = QHBoxLayout()
        for label, action in (("Start", "start"), ("Stop", "stop"), ("Neustart", "restart")):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, a=action: self._run_action(a))
            row.addWidget(button)
        self.content_layout.addLayout(row)
        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self._safe_refresh_from_state)
        self.timer.start()

    def refresh_from_state(self) -> None:
        names = [name.strip() for name in self.get_prop("service_names", "").split(",") if name.strip()]
        if not names:
            return
        job = _ServiceStatus(names, self)
        job.done.connect(self._show_status)
        job.finished.connect(job.deleteLater)
        job.start()
        self.job = job

    def _show_status(self, results) -> None:
        self.list.clear()
        for name, active in results:
            marker = "●" if active == "active" else "○"
            self.list.addItem(f"{marker} {name} — {active}")

    def _selected_service(self):
        item = self.list.currentItem()
        return item.text().split()[1] if item else None

    def _run_action(self, action: str) -> None:
        service_name = self._selected_service()
        if not service_name:
            return
        if QMessageBox.question(self, "Systemdienst", f"Dienst '{service_name}' wirklich {action}en?") != QMessageBox.Yes:
            return
        job = _ServiceAction(action, service_name, self)
        job.done.connect(lambda _result: self.refresh_from_state())
        job.finished.connect(job.deleteLater)
        job.start()
        self.job = job