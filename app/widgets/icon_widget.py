"""Standalone icon widget - purely decorative, or reflects a binary entity."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel

from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph


class IconWidget(BaseWidget):
    type_name = "icon"
    display_name = "Icon"
    category = "Anzeige"
    icon = "star"
    default_size = (100, 100)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("icon_char", "Icon", "icon", "star", group="Inhalt"),
        PropertyDef("icon_image_path", "Eigenes Bild", "image", "", group="Inhalt"),
        PropertyDef("entity_id", "Entity (optional)", "entity", "", entity_domains=["binary_sensor", "switch", "light"], group="Verbindung"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        img_path = self.get_prop("icon_image_path", "")
        if img_path and os.path.exists(img_path):
            self.icon_image_label = QLabel()
            self.icon_image_label.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(self.icon_image_label)
            self._update_custom_image()
        else:
            self.icon_image_label = None
            self.icon_label = IconGlyph(self.get_prop("icon_char", "star"), self.get_prop("accent_color", "#4C8DFF"))
            self.content_layout.addWidget(self.icon_label)

    def _update_custom_image(self) -> None:
        img_path = self.get_prop("icon_image_path", "")
        if not self.icon_image_label or not img_path:
            return
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.icon_image_label.size(),
                Qt.KeepAspectRatio, Qt.SmoothTransformation,
            )
            self.icon_image_label.setPixmap(scaled)
        else:
            self.icon_image_label.setText("\u2753")

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            return
        active = e.state in ("on", "home", "open")
        self.set_active(active)
        accent = self.get_prop("accent_color", "#4C8DFF")
        if hasattr(self, "icon_label") and self.icon_label is not None:
            self.icon_label.set_color(accent if active else "#777777")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if getattr(self, "icon_image_label", None) is not None:
            self._update_custom_image()
