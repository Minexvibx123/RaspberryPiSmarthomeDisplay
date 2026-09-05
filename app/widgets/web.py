"""Optional embedded web panel backed by QtWebEngine when available."""
from __future__ import annotations

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QLabel

from app.widgets.base import BaseWidget, PropertyDef


class WebWidget(BaseWidget):
    type_name = "web"
    display_name = "Web Panel"
    category = "Apps"
    icon = "WEB"
    default_size = (480, 320)
    PROPERTY_SCHEMA = [
        PropertyDef("url", "URL", "text", "https://home-assistant.local", group="Web"),
        PropertyDef("refresh_interval", "Aktualisierung (Sekunden)", "number", 0, min=0, max=3600, group="Web"),
        PropertyDef("zoom", "Zoom (%)", "number", 100, min=25, max=300, group="Web"),
        PropertyDef("allow_interaction", "Interaktion erlauben", "bool", True, group="Web"),
        PropertyDef("reload_on_page_open", "Beim Seitenwechsel neu laden", "bool", True, group="Web"),
    ]

    def build_ui(self) -> None:
        self.web_view = None
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            message = QLabel("WebEngine ist nicht installiert.")
            message.setWordWrap(True)
            self.content_layout.addWidget(message)
            return

        self.web_view = QWebEngineView(self)
        self.content_layout.addWidget(self.web_view, 1)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.web_view.reload)

    def refresh_from_state(self) -> None:
        if self.web_view is None:
            return
        self.web_view.setEnabled(bool(self.get_prop("allow_interaction", True)))
        self.web_view.setZoomFactor(float(self.get_prop("zoom", 100)) / 100)
        url = QUrl.fromUserInput(str(self.get_prop("url", "")))
        if url.isValid() and url != self.web_view.url():
            self.web_view.setUrl(url)
        interval = int(float(self.get_prop("refresh_interval", 0)) * 1000)
        if interval > 0:
            self.refresh_timer.start(interval)
        else:
            self.refresh_timer.stop()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.web_view is not None and self.get_prop("reload_on_page_open", True):
            self.web_view.reload()