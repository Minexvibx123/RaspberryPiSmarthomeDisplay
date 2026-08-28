"""Cover / Rollladen (blinds, garage doors, ...) widget."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.widgets.base import BaseWidget, PropertyDef


class CoverWidget(BaseWidget):
    type_name = "cover"
    display_name = "Rollladen"
    category = "Steuerung"
    icon = "blinds"
    default_size = (200, 150)
    requires_entity = True
    entity_domains = ["cover"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["cover"], group="Verbindung"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.name_label = QLabel(self.get_prop("name") or "Rollladen")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; border: none; background: transparent;"
        )
        self.content_layout.addWidget(self.name_label)

        self.position_label = QLabel("--%")
        self.position_label.setAlignment(Qt.AlignCenter)
        self.position_label.setStyleSheet(
            f"color: {self.get_prop('accent_color', '#4C8DFF')}; font-size: {int(self.get_prop('font_size', 16)) + 10}px; font-weight: 700; border: none; background: transparent;"
        )
        self.content_layout.addWidget(self.position_label)

        row = QHBoxLayout()
        self.up_btn = QPushButton("\u25B2 Auf")
        self.stop_btn = QPushButton("Stopp")
        self.down_btn = QPushButton("\u25BC Zu")
        for b, cb in ((self.up_btn, self._open), (self.stop_btn, self._stop), (self.down_btn, self._close)):
            b.setStyleSheet(f"QPushButton {{ background: rgba(255,255,255,20); color: {self.get_prop('text_color', '#FFFFFF')}; border-radius: 8px; padding: 6px; }}")
            b.clicked.connect(cb)
            row.addWidget(b)
        self.content_layout.addLayout(row)

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            self.position_label.setText("--%")
            return
        self.set_active(e.state == "open")
        pos = e.attributes.get("current_position")
        self.position_label.setText(f"{pos}%" if pos is not None else e.state.capitalize())

    def _open(self) -> None:
        self.call_service("cover", "open_cover")

    def _close(self) -> None:
        self.call_service("cover", "close_cover")

    def _stop(self) -> None:
        self.call_service("cover", "stop_cover")
