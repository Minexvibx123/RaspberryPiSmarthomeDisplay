"""Light widget - on/off toggle with optional brightness slider."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QVBoxLayout

from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph


class LightWidget(BaseWidget):
    type_name = "light"
    display_name = "Licht"
    category = "Steuerung"
    icon = "bulb"
    default_size = (200, 140)
    requires_entity = True
    entity_domains = ["light"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["light"], group="Verbindung"),
        PropertyDef("show_brightness", "Helligkeitsregler anzeigen", "bool", True, group="Verhalten"),
        PropertyDef("show_state", "Ein/Aus-Zustand anzeigen", "bool", True, group="Verhalten"),
        PropertyDef("icon_char", "Icon", "icon", "bulb", group="Inhalt"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        header = QHBoxLayout()
        self.icon_label = IconGlyph(self.get_prop("icon_char", "bulb"), self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(int(self.get_prop('font_size', 16)) + 16, int(self.get_prop('font_size', 16)) + 16)
        self.name_label = QLabel(self.get_prop("name") or self.config.get("entity_id", "Licht"))
        self.name_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 600; border: none; background: transparent;"
        )
        header.addWidget(self.icon_label)
        header.addWidget(self.name_label, 1)
        self.content_layout.addLayout(header)

        self.state_label = QLabel("")
        self.state_label.setStyleSheet("color: #AAAAAA; font-size: 12px; border: none; background: transparent;")
        if self.get_prop("show_state", True):
            self.content_layout.addWidget(self.state_label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1, 255)
        self.slider.setValue(180)
        self.slider.valueChanged.connect(self._on_slider_changed)
        if self.get_prop("show_brightness", True):
            self.content_layout.addWidget(self.slider)
        self.content_layout.addStretch()

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            self.state_label.setText("Keine Verbindung")
            return
        is_on = e.state == "on"
        self.set_active(is_on)
        self.state_label.setText("An" if is_on else "Aus")
        brightness = e.attributes.get("brightness")
        if brightness is not None:
            self.slider.blockSignals(True)
            self.slider.setValue(int(brightness))
            self.slider.blockSignals(False)
        accent = self.get_prop("accent_color", "#4C8DFF")
        self.icon_label.set_color(accent if is_on else "#777777")

    def _on_slider_changed(self, value: int) -> None:
        self.call_service("light", "turn_on", brightness=value)

    def mouseReleaseEvent(self, event) -> None:
        # tapping the header/icon area toggles the light (slider handles its own drags)
        if not self.slider.underMouse():
            self.call_service("light", "toggle")
            self.clicked.emit()
        super().mouseReleaseEvent(event)
