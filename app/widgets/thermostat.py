"""Thermostat / climate control widget."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.widgets.base import BaseWidget, PropertyDef


class ThermostatWidget(BaseWidget):
    type_name = "thermostat"
    display_name = "Thermostat"
    category = "Steuerung"
    icon = "thermometer"
    default_size = (200, 180)
    requires_entity = True
    entity_domains = ["climate"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["climate"], group="Verbindung"),
        PropertyDef("step", "Schrittweite", "number", 0.5, min=0.1, max=5, group="Verhalten"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.name_label = QLabel(self.get_prop("name") or "Heizung")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {int(self.get_prop('font_size', 16)) - 1}px; border: none; background: transparent;"
        )
        self.content_layout.addWidget(self.name_label)

        row = QHBoxLayout()
        self.minus_btn = QPushButton("-")
        self.plus_btn = QPushButton("+")
        for b in (self.minus_btn, self.plus_btn):
            b.setFixedSize(44, 44)
            b.setStyleSheet(
                f"QPushButton {{ font-size: 22px; border-radius: 22px; background: rgba(255,255,255,20); color: {self.get_prop('text_color', '#FFFFFF')}; }}"
            )
        self.temp_label = QLabel("--")
        self.temp_label.setAlignment(Qt.AlignCenter)
        self.temp_label.setStyleSheet(
            f"color: {self.get_prop('accent_color', '#4C8DFF')}; font-size: {int(self.get_prop('font_size', 16)) + 16}px; font-weight: 700; border: none; background: transparent;"
        )
        self.minus_btn.clicked.connect(lambda: self._adjust(-self.get_prop("step", 0.5)))
        self.plus_btn.clicked.connect(lambda: self._adjust(self.get_prop("step", 0.5)))
        row.addWidget(self.minus_btn)
        row.addWidget(self.temp_label, 1)
        row.addWidget(self.plus_btn)
        self.content_layout.addLayout(row)

        self.current_label = QLabel("Ist: --")
        self.current_label.setAlignment(Qt.AlignCenter)
        self.current_label.setStyleSheet("color: #AAAAAA; font-size: 12px; border: none; background: transparent;")
        self.content_layout.addWidget(self.current_label)

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            self.temp_label.setText("--")
            return
        self.set_active(e.state not in ("off", "unavailable", "unknown"))
        target = e.attributes.get("temperature")
        current = e.attributes.get("current_temperature")
        self.temp_label.setText(f"{target}°" if target is not None else "--")
        self.current_label.setText(f"Ist: {current}°" if current is not None else "Ist: --")

    def _adjust(self, delta: float) -> None:
        e = self.entity()
        if not e:
            return
        target = e.attributes.get("temperature", 20)
        new_temp = round(float(target) + delta, 1)
        self.call_service("climate", "set_temperature", temperature=new_temp)
