"""Simple on/off switch widget."""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel

from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph


class SwitchWidget(BaseWidget):
    type_name = "switch"
    display_name = "Schalter"
    category = "Steuerung"
    icon = "power"
    default_size = (200, 110)
    requires_entity = True
    entity_domains = ["switch", "input_boolean"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["switch", "input_boolean"], group="Verbindung"),
        PropertyDef("icon_char", "Icon", "icon", "power", group="Inhalt"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        row = QHBoxLayout()
        self.icon_label = IconGlyph(self.get_prop("icon_char", "power"), self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(int(self.get_prop('font_size', 16)) + 18, int(self.get_prop('font_size', 16)) + 18)
        self.name_label = QLabel(self.get_prop("name") or self.config.get("entity_id", "Schalter"))
        self.name_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 600; border: none; background: transparent;"
        )
        row.addWidget(self.icon_label)
        row.addWidget(self.name_label, 1)
        self.content_layout.addLayout(row)
        self.state_label = QLabel("")
        self.state_label.setStyleSheet("color: #AAAAAA; font-size: 13px; border: none; background: transparent;")
        self.content_layout.addWidget(self.state_label)
        self.content_layout.addStretch()

    def refresh_from_state(self) -> None:
        e = self.entity()
        is_on = bool(e and e.state == "on")
        self.set_active(is_on)
        self.state_label.setText("An" if is_on else "Aus")
        accent = self.get_prop("accent_color", "#4C8DFF")
        self.icon_label.set_color(accent if is_on else "#777777")

    def mouseReleaseEvent(self, event) -> None:
        domain = self.config.get("entity_id", "switch.").split(".")[0]
        self.call_service(domain, "toggle")
        self.clicked.emit()
        super().mouseReleaseEvent(event)
