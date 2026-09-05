from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QMessageBox, QPushButton
from app.widgets.base import BaseWidget
from .api import DockerClient

class _List(QThread):
    done = Signal(object)
    def __init__(self, parent): super().__init__(parent)
    def run(self):
        try: self.done.emit(DockerClient().containers())
        except Exception as exc: self.done.emit({"error": str(exc)})


class _Action(QThread):
    done = Signal(object)
    def __init__(self, action, container, parent):
        super().__init__(parent); self.action, self.container = action, container
    def run(self):
        try:
            getattr(DockerClient(), self.action)(self.container)
            self.done.emit(None)
        except Exception as exc:
            self.done.emit(str(exc))


class DockerWidget(BaseWidget):
    type_name = "docker_containers"; display_name = "Docker"; category = "System"; default_size = (320, 260)

    def build_ui(self):
        self.list = QListWidget()
        self.content_layout.addWidget(self.list, 1)
        row = QHBoxLayout()
        for label, action in (("Start", "start"), ("Stop", "stop"), ("Neustart", "restart")):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, a=action: self._run_action(a))
            row.addWidget(button)
        self.content_layout.addLayout(row)

    def refresh_from_state(self):
        job = _List(self); job.done.connect(self.show_containers); job.finished.connect(job.deleteLater); job.start(); self.job = job

    def show_containers(self, data):
        self.list.clear()
        if isinstance(data, dict):
            self.list.addItem("Docker nicht verfügbar: " + data["error"]); return
        for item in data:
            state = "●" if item.get("State") == "running" else "○"
            self.list.addItem(f"{state} {item.get('Names', item.get('ID'))} — {item.get('Status', '')}")

    def _selected_container(self):
        item = self.list.currentItem()
        return item.text().split()[1] if item and "nicht verfügbar" not in item.text() else None

    def _run_action(self, action):
        container = self._selected_container()
        if not container:
            return
        if action in ("stop", "restart"):
            if QMessageBox.question(self, "Docker", f"Container '{container}' wirklich {action}en?") != QMessageBox.Yes:
                return
        job = _Action(action, container, self)
        job.done.connect(lambda _result: self.refresh_from_state())
        job.finished.connect(job.deleteLater)
        job.start()
        self.job = job