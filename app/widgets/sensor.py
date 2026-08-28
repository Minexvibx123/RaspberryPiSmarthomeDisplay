"""Read-only sensor value display (temperature, humidity, power, ...)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph


class SensorWidget(BaseWidget):
    type_name = "sensor"
    display_name = "Sensor"
    category = "Anzeige"
    icon = "gauge"
    default_size = (170, 130)
    requires_entity = True
    entity_domains = ["sensor", "binary_sensor"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["sensor", "binary_sensor"], group="Verbindung"),
        PropertyDef("icon_char", "Icon", "icon", "gauge", group="Inhalt"),
        PropertyDef("unit_override", "Einheit (überschreiben)", "text", "", group="Format"),
        PropertyDef("decimals", "Dezimalstellen", "number", 1, min=0, max=3, group="Format"),
        PropertyDef("min_value", "Min", "number", 0, group="Format"),
        PropertyDef("max_value", "Max", "number", 100, group="Format"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.icon_label = IconGlyph(self.get_prop("icon_char", "gauge"), self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(int(self.get_prop('font_size', 16)) + 20, int(self.get_prop('font_size', 16)) + 20)
        self.value_label = QLabel("--")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet(
            f"color: {self.get_prop('accent_color', '#4C8DFF')}; font-size: {int(self.get_prop('font_size', 16)) + 10}px; font-weight: 600; border: none; background: transparent;"
        )
        self.name_label = QLabel(self.get_prop("name") or self.config.get("entity_id", "Sensor"))
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {int(self.get_prop('font_size', 16)) - 2}px; border: none; background: transparent;"
        )
        for w in (self.icon_label, self.value_label, self.name_label):
            self.content_layout.addWidget(w, alignment=Qt.AlignCenter)

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            self.value_label.setText("--")
            return
        unit = self.get_prop("unit_override") or e.attributes.get("unit_of_measurement", "")
        try:
            decimals = int(self.get_prop("decimals", 1))
            val = f"{float(e.state):.{decimals}f}"
        except (ValueError, TypeError):
            val = e.state
        self.value_label.setText(f"{val} {unit}".strip())
