"""Generic slider widget - controls a numeric HA entity (e.g. input_number, cover position, light brightness)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSlider, QVBoxLayout

from app.widgets.base import BaseWidget, PropertyDef


class SliderWidget(BaseWidget):
    type_name = "slider"
    display_name = "Slider"
    category = "Steuerung"
    icon = "\U0001F39A"
    default_size = (220, 120)
    requires_entity = True
    entity_domains = ["input_number", "light", "cover", "media_player"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["input_number", "light", "cover", "media_player"], group="Verbindung"),
        PropertyDef("min_value", "Min", "number", 0, group="Verhalten"),
        PropertyDef("max_value", "Max", "number", 100, group="Verhalten"),
        PropertyDef("service_domain", "Service-Domain", "text", "input_number", group="Erweitert"),
        PropertyDef("service_name", "Service-Name", "text", "set_value", group="Erweitert"),
        PropertyDef("value_field", "Wertfeld", "text", "value", group="Erweitert"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.name_label = QLabel(self.get_prop("name") or "Slider")
        self.name_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; border: none; background: transparent;"
        )
        self.content_layout.addWidget(self.name_label)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(int(self.get_prop("min_value", 0)), int(self.get_prop("max_value", 100)))
        self.slider.sliderReleased.connect(self._on_release)
        self.content_layout.addWidget(self.slider)
        self.value_label = QLabel("--")
        self.value_label.setAlignment(Qt.AlignRight)
        self.value_label.setStyleSheet("color: #AAAAAA; font-size: 12px; border: none; background: transparent;")
        self.content_layout.addWidget(self.value_label)

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            return
        try:
            val = float(e.state)
        except (ValueError, TypeError):
            val = self.slider.minimum()
        self.slider.blockSignals(True)
        self.slider.setValue(int(val))
        self.slider.blockSignals(False)
        self.value_label.setText(str(int(val)))

    def _on_release(self) -> None:
        domain = self.get_prop("service_domain", "input_number")
        service = self.get_prop("service_name", "set_value")
        field = self.get_prop("value_field", "value")
        self.call_service(domain, service, **{field: self.slider.value()})
        self.value_label.setText(str(self.slider.value()))
