from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from app.widgets.base import BaseWidget, PropertyDef

from .api import FlashforgeClient


class _MjpegReader(QThread):
    frame_ready = Signal(bytes)
    offline = Signal()

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self._quit = False

    def stop(self):
        self._quit = True
        self.requestInterruption()

    def run(self):
        import requests
        while not self._quit and not self.isInterruptionRequested():
            try:
                response = requests.get(self.url, stream=True, timeout=(5, 10))
                response.raise_for_status()
                if self._quit:
                    response.close()
                    return
                buffer = bytearray()
                for chunk in response.iter_content(8192):
                    if self._quit:
                        break
                    buffer.extend(chunk)
                    start = buffer.find(b"\xff\xd8")
                    while start != -1:
                        end = buffer.find(b"\xff\xd9", start + 2)
                        if end == -1:
                            break
                        frame = bytes(buffer[start:end + 2])
                        del buffer[:end + 2]
                        self.frame_ready.emit(frame)
                        start = buffer.find(b"\xff\xd8")
                    if len(buffer) > 4_000_000:
                        buffer.clear()
                response.close()
            except Exception:
                if not self._quit:
                    self.offline.emit()
                    self.msleep(2000)


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


class _CommandThread(QThread):
    ready = Signal(str)
    failed = Signal(str)

    def __init__(self, host, port, fn, parent=None):
        super().__init__(parent)
        self.host, self.port = host, port
        self.fn = fn

    def run(self):
        try:
            self.ready.emit(self.fn(FlashforgeClient(self.host, self.port)))
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
        if getattr(self, "fetch", None) is not None:
            if self.fetch.isRunning():
                return
            previous = self.fetch
            self.fetch = None
            previous.deleteLater()
        host = self.config.get("printer_host", "192.168.178.112")
        port = int(self.config.get("printer_port", 8899))
        self.fetch = _StatusFetch(host, port, self)
        self.fetch.ready.connect(self._show_status)
        self.fetch.failed.connect(lambda error: self.status.setText("Offline"))
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
        row.setSpacing(10)
        for label, command in (("Pause", "M25"), ("Fortsetzen", "M24"), ("Abbrechen", "M26")):
            button = QPushButton(label)
            button.setMinimumHeight(52)
            button.clicked.connect(lambda _checked=False, cmd=command: self._run(cmd))
            row.addWidget(button)
        self.content_layout.addLayout(row)

    def refresh_from_state(self):
        pass

    def _run(self, command):
        if command == "M26" and QMessageBox.question(self, "Druck abbrechen", "Druck wirklich abbrechen?") != QMessageBox.Yes:
            return
        thread = _CommandThread(self.config.get("printer_host", "192.168.178.112"), int(self.config.get("printer_port", 8899)), lambda client: client.command(command), self)
        thread.failed.connect(lambda error: self._show_error(error))
        thread.start()

    def _show_error(self, error):
        QMessageBox.critical(self, "Flashforge", f"Befehl fehlgeschlagen:\n{error}")


class PrintJogWidget(QWidget):
    """Touch-first X/Y/Z jog control for the Flashforge app view."""

    STEPS = (1, 10, 50)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.step = 10
        self._step_buttons = []

        self.setObjectName("jogPanel")
        self.setStyleSheet(
            "QWidget#jogPanel { background-color: rgba(23,24,32,200); border-radius: 16px;"
            " border: 1px solid rgba(255,255,255,30); }"
            "QWidget#jogPanel QLabel { background: transparent; }"
            "QWidget#jogPanel QPushButton { background-color: #2A2C3A; color: #FFFFFF;"
            " border: 1px solid rgba(255,255,255,40); border-radius: 10px; font-size: 18px; }"
            "QWidget#jogPanel QPushButton:pressed { background-color: #4C8DFF; }"
            "QWidget#jogPanel QPushButton:checked { background-color: #4C8DFF; color: #FFFFFF; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Achsensteuerung")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #FFFFFF;")
        header.addWidget(title)
        header.addStretch(1)
        for mm in self.STEPS:
            btn = QPushButton(f"{mm} mm")
            btn.setCheckable(True)
            btn.setMinimumHeight(36)
            btn.setFixedWidth(58)
            btn.setChecked(mm == self.step)
            btn.clicked.connect(lambda _checked=False, s=mm: self._set_step(s))
            header.addWidget(btn)
            self._step_buttons.append(btn)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(8)
        for column, axis in enumerate(("X", "Y", "Z")):
            axis_label = QLabel(axis)
            axis_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            axis_label.setStyleSheet("font-size: 22px; font-weight: 800; color: #4C8DFF;")
            grid.addWidget(axis_label, 0, column)
            minus = QPushButton("\u2212")
            minus.setMinimumHeight(52)
            minus.clicked.connect(lambda _checked=False, a=axis: self._start_jog(a, -1))
            grid.addWidget(minus, 1, column)
            plus = QPushButton("\uff0b")
            plus.setMinimumHeight(52)
            plus.clicked.connect(lambda _checked=False, a=axis: self._start_jog(a, 1))
            grid.addWidget(plus, 2, column)
        layout.addLayout(grid, 1)

        home_btn = QPushButton("Home (alle Achsen)")
        home_btn.setMinimumHeight(48)
        home_btn.clicked.connect(self._home)
        layout.addWidget(home_btn)

        self.feedback = QLabel("")
        self.feedback.setStyleSheet("font-size: 13px; color: #9AA0B4;")
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)

        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(lambda: self.feedback.setText(""))

    def _host_port(self):
        return self.config.get("printer_host", "192.168.178.112"), int(self.config.get("printer_port", 8899))

    def _set_step(self, mm):
        self.step = mm
        for btn, value in zip(self._step_buttons, self.STEPS):
            btn.setChecked(value == mm)

    def _start_jog(self, axis, direction):
        delta = direction * self.step
        self._flash(f"{'X' if axis == 'X' else ''}{'Y' if axis == 'Y' else ''}{'Z' if axis == 'Z' else ''}{('+' if delta >= 0 else '')}{delta} mm")
        kwargs = {"dx": 0.0, "dy": 0.0, "dz": 0.0}
        if axis == "X": kwargs["dx"] = float(delta)
        elif axis == "Y": kwargs["dy"] = float(delta)
        else: kwargs["dz"] = float(delta)
        thread = _CommandThread(*self._host_port(), lambda client: client.move(**kwargs), self)
        thread.failed.connect(lambda error: self._flash(f"Fehler: {error}"))
        thread.start()

    def _home(self):
        self._flash("Home läuft...")
        thread = _CommandThread(*self._host_port(), lambda client: client.home(), self)
        thread.failed.connect(lambda error: self._flash(f"Fehler: {error}"))
        thread.start()

    def _flash(self, message):
        self.feedback.setText(message)
        self._feedback_timer.start(3000)


class FlashforgeCameraWidget(BaseWidget):
    type_name = "flashforge_camera"
    display_name = "Drucker-Kamera"
    category = "Hardware"
    icon = "camera"
    default_size = (320, 200)

    PROPERTY_SCHEMA = [
        PropertyDef("host", "Drucker-IP", "text", "192.168.178.112", group="Verbindung"),
        PropertyDef("stream_port", "Kamera-Port", "number", 8080, min=1, max=65535, group="Verbindung"),
        PropertyDef("stream_path", "Stream-Pfad", "text", "/?action=stream", group="Verbindung"),
    ]

    def __init__(self, widget_id, config, state_manager=None, parent=None):
        super().__init__(widget_id, config, state_manager, parent)
        self._reader = None
        self._last = None
        self._starting = False

    def build_ui(self):
        self.image_label = QLabel("Kamera offline")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(
            "color: #888888; font-size: 14px; border: none; background-color: #000000; border-radius: 10px;"
        )
        self.content_layout.addWidget(self.image_label, 1)

    def _stream_url(self):
        host = self.get_prop("host", "192.168.178.112")
        port = int(self.get_prop("stream_port", 8080))
        path = self.get_prop("stream_path", "/?action=stream") or "/?action=stream"
        return f"http://{host}:{port}{path}"

    def _start_stream(self):
        if self._starting:
            return
        self._starting = True
        try:
            self._stop_stream()
            reader = _MjpegReader(self._stream_url())
            reader.frame_ready.connect(self._on_frame)
            reader.offline.connect(self._on_offline)
            reader.finished.connect(reader.deleteLater)
            self._reader = reader
            reader.start()
        finally:
            self._starting = False

    def _stop_stream(self):
        reader = self._reader
        self._reader = None
        if reader is not None:
            reader.stop()
            if reader.isRunning():
                reader.wait(300)

    def _on_frame(self, data):
        try:
            pixmap = QPixmap.fromImage(QImage.fromData(data))
            if not pixmap.isNull():
                self._last = pixmap
                self._scale_image()
        except RuntimeError:
            pass

    def _on_offline(self):
        try:
            self._last = None
            self.image_label.clear()
            self.image_label.setText("Kamera offline")
        except RuntimeError:
            pass

    def _scale_image(self):
        try:
            if self._last is None or self.image_label.size().isEmpty():
                return
            self.image_label.setPixmap(
                self._last.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        except RuntimeError:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        if self.isVisible():
            self._start_stream()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop_stream()

    def closeEvent(self, event):
        self._stop_stream()
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._scale_image()
