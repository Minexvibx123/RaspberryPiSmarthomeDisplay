from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph


class ContainerWidget(BaseWidget):
    type_name = "container"
    display_name = "Container"
    category = "Allgemein"
    icon = "home"
    default_size = (400, 300)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("group_name", "Gruppenname", "text", "", group="Inhalt"),
        PropertyDef("border_visible", "Rahmen sichtbar", "bool", True, group="Darstellung"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        group_name = self.get_prop("group_name", "")
        if group_name:
            self.title_label = QLabel(group_name)
            self.title_label.setStyleSheet(
                f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: bold; border: none; background: transparent;"
            )
            layout.addWidget(self.title_label)
            
        self.content_layout.addLayout(layout)

    def refresh_from_state(self) -> None:
        pass
