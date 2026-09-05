from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton
from app.widgets.base import BaseWidget
from .api import PiHoleClient


class _Stats(QThread):
    done = Signal(object)
    def __init__(self, url, sid, parent): super().__init__(parent); self.url, self.sid = url, sid
    def run(self):
        try: self.done.emit(PiHoleClient(self.url, self.sid).stats())
        except Exception as exc: self.done.emit({"error": str(exc)})


class PiHoleStatsWidget(BaseWidget):
    type_name = "pihole_stats"; display_name = "Pi-hole"; category = "Netzwerk"; default_size = (240, 160)
    def build_ui(self): self.label = QLabel("Pi-hole wird geladen..."); self.label.setWordWrap(True); self.content_layout.addWidget(self.label)
    def refresh_from_state(self):
        job = _Stats(self.config.get("pihole_url", "http://pi.hole"), self.config.get("pihole_sid", ""), self)
        job.done.connect(self.show_stats); job.finished.connect(job.deleteLater); job.start(); self.job = job
    def show_stats(self, data):
        if "error" in data: self.label.setText("Offline\n" + data["error"]); return
        self.label.setText(f"Online\nQueries: {data.get('queries', 0)}\nGeblockt: {data.get('blocked', 0)}\nRate: {data.get('percentage', 0)} %")


class _SetBlocking(QThread):
    done = Signal(object)
    def __init__(self, url, sid, enabled, timer, parent):
        super().__init__(parent); self.url, self.sid, self.enabled, self.timer = url, sid, enabled, timer
    def run(self):
        try: self.done.emit(PiHoleClient(self.url, self.sid).set_blocking(self.enabled, self.timer))
        except Exception as exc: self.done.emit({"error": str(exc)})


class PiHoleControlWidget(BaseWidget):
    type_name = "pihole_control"; display_name = "Pi-hole Steuerung"; category = "Netzwerk"; default_size = (320, 130)

    def build_ui(self) -> None:
        self.status = QLabel("Bereit")
        self.content_layout.addWidget(self.status)
        row = QHBoxLayout()
        for label, timer in (("5 Min", 300), ("30 Min", 1800), ("1 Std", 3600), ("Dauerhaft", None)):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, t=timer: self._set_blocking(False, t))
            row.addWidget(button)
        self.content_layout.addLayout(row)
        enable_button = QPushButton("Blocking aktivieren")
        enable_button.clicked.connect(lambda: self._set_blocking(True, None))
        self.content_layout.addWidget(enable_button)

    def refresh_from_state(self) -> None:
        pass

    def _set_blocking(self, enabled: bool, timer) -> None:
        job = _SetBlocking(
            self.config.get("pihole_url", "http://pi.hole"),
            self.config.get("pihole_sid", ""),
            enabled, timer, self,
        )
        job.done.connect(self._show_result)
        job.finished.connect(job.deleteLater)
        job.start()
        self.job = job

    def _show_result(self, data) -> None:
        self.status.setText("Fehler: " + data["error"] if "error" in data else "Aktualisiert")