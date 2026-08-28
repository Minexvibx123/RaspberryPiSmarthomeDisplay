"""Free text label widget - no entity required."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from app.widgets.base import BaseWidget, PropertyDef


class TextWidget(BaseWidget):
    type_name = "text"
    display_name = "Text"
    category = "Anzeige"
    icon = "\U0001F5DA"
    default_size = (200, 80)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("text", "Text", "text", "Text", group="Inhalt"),
        PropertyDef("alignment", "Ausrichtung", "select", "center", options=["left", "center", "right"], group="Format"),
        PropertyDef("bold", "Fett", "bool", False, group="Format"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.label = QLabel(self.get_prop("text", "Text"))
        self.label.setWordWrap(True)
        align_map = {"left": Qt.AlignLeft, "center": Qt.AlignCenter, "right": Qt.AlignRight}
        self.label.setAlignment(align_map.get(self.get_prop("alignment", "center"), Qt.AlignCenter) | Qt.AlignVCenter)
        weight = "700" if self.get_prop("bold", False) else "400"
        self.label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: {weight}; border: none; background: transparent;"
        )
        self.content_layout.addWidget(self.label)

    def refresh_from_state(self) -> None:
        pass
