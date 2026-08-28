"""Live clock / date widget - no entity required."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from app.widgets.base import BaseWidget, PropertyDef


class ClockWidget(BaseWidget):
    type_name = "clock"
    display_name = "Uhr"
    category = "Anzeige"
    icon = "\U0001F550"
    default_size = (220, 130)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("show_seconds", "Sekunden anzeigen", "bool", False, group="Format"),
        PropertyDef("show_date", "Datum anzeigen", "bool", True, group="Format"),
        PropertyDef("time_format", "Zeitformat", "select", "24h", options=["24h", "12h"], group="Format"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.time_label = QLabel("--:--")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {int(self.get_prop('font_size', 16)) + 20}px; font-weight: 700; border: none; background: transparent;"
        )
        self.date_label = QLabel("")
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet("color: #AAAAAA; font-size: 13px; border: none; background: transparent;")
        self.content_layout.addWidget(self.time_label)
        self.content_layout.addWidget(self.date_label)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_from_state)
        self._timer.start(1000 if self.get_prop("show_seconds") else 15000)

    def refresh_from_state(self) -> None:
        now = datetime.now()
        fmt = "%H:%M:%S" if self.get_prop("show_seconds") else "%H:%M"
        if self.get_prop("time_format") == "12h":
            fmt = fmt.replace("%H", "%I") + " %p"
        self.time_label.setText(now.strftime(fmt))
        if self.get_prop("show_date", True):
            self.date_label.setText(now.strftime("%A, %d. %B"))
            self.date_label.show()
        else:
            self.date_label.hide()
