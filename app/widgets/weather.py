"""Weather widget - reads a Home Assistant `weather.*` entity."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph

CONDITION_ICONS = {
    "sunny": "sun", "clear-night": "night", "cloudy": "cloud",
    "partlycloudy": "cloud", "rainy": "rain", "pouring": "rain",
    "snowy": "snow", "fog": "cloud", "lightning": "storm",
    "lightning-rainy": "storm", "windy": "wind", "windy-variant": "wind",
    "exceptional": "star",
}


class WeatherWidget(BaseWidget):
    type_name = "weather"
    display_name = "Wetter"
    category = "Anzeige"
    icon = "sun"
    default_size = (220, 150)
    requires_entity = True
    entity_domains = ["weather"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["weather"], group="Verbindung"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.icon_label = IconGlyph("sun", self.get_prop("accent_color", "#4C8DFF"))
        icon_size = int(self.get_prop('font_size', 16)) + 40
        self.icon_label.setFixedSize(icon_size, icon_size)
        self.temp_label = QLabel("--°")
        self.temp_label.setAlignment(Qt.AlignCenter)
        self.temp_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {int(self.get_prop('font_size', 16)) + 12}px; font-weight: 700; border: none; background: transparent;"
        )
        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setStyleSheet("color: #AAAAAA; font-size: 12px; border: none; background: transparent;")
        for w in (self.icon_label, self.temp_label, self.detail_label):
            self.content_layout.addWidget(w)

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            return
        self.icon_label.set_icon(CONDITION_ICONS.get(e.state, "cloud"))
        temp = e.attributes.get("temperature")
        humidity = e.attributes.get("humidity")
        self.temp_label.setText(f"{temp}°" if temp is not None else "--°")
        self.detail_label.setText(f"Luftfeuchtigkeit {humidity}%" if humidity is not None else "")
