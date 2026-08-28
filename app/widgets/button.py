"""A generic tappable button widget - can fire a service call or open a page."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout

from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph


class ButtonWidget(BaseWidget):
    type_name = "button"
    display_name = "Button"
    category = "Steuerung"
    icon = "flash"
    default_size = (180, 100)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("text", "Text", "text", "Button", group="Inhalt"),
        PropertyDef("icon_char", "Icon", "icon", "flash", group="Inhalt"),
        PropertyDef("entity_id", "Entity (optional)", "entity", "", entity_domains=["light", "switch", "input_boolean", "scene", "script"], group="Aktion"),
        PropertyDef("action", "Aktion", "select", "toggle", options=["toggle", "turn_on", "turn_off", "activate", "navigate"], group="Aktion"),
        PropertyDef("target_page", "Zielseite (bei Navigation)", "text", "", group="Aktion"),
        PropertyDef("long_press_action", "Verhalten bei langem Drücken", "select", "none", options=["none", "toggle", "turn_on", "turn_off"], group="Aktion"),
    ]

    navigate_requested = Signal(str)

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        self.icon_label = IconGlyph(self.get_prop("icon_char", "flash"), self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(int(self.get_prop('font_size', 16)) + 26, int(self.get_prop('font_size', 16)) + 26)
        self.text_label = QLabel(self.get_prop("text", "Button"))
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 600; border: none; background: transparent;"
        )
        layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.text_label)
        self.content_layout.addLayout(layout)

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            return
        is_on = e.state == "on"
        self.set_active(is_on)
        self.icon_label.set_color(self.get_prop("accent_color", "#4C8DFF") if is_on else self.get_prop("text_color", "#FFFFFF"))

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        action = self.get_prop("action", "toggle")
        entity_id = self.config.get("entity_id")
        if action == "navigate":
            self.navigate_requested.emit(self.get_prop("target_page", ""))
        elif entity_id:
            domain = entity_id.split(".")[0]
            if action == "toggle":
                self.call_service(domain, "toggle")
            elif action == "turn_on":
                self.call_service(domain, "turn_on")
            elif action == "turn_off":
                self.call_service(domain, "turn_off")
            elif action == "activate":
                self.call_service(domain, "turn_on")
        self.clicked.emit()
        super().mouseReleaseEvent(event)
