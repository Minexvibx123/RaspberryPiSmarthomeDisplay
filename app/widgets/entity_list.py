"""Scrollable list of entities - e.g. "all lights", or an arbitrary manual selection."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from app.widgets.base import BaseWidget, PropertyDef


class EntityListWidget(BaseWidget):
    type_name = "entity_list"
    display_name = "Entity-Liste"
    category = "Anzeige"
    icon = "\U0001F4CB"
    default_size = (260, 220)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("domain_filter", "Kategorie", "select", "light", options=["light", "switch", "sensor", "cover", "climate", "all"], group="Inhalt"),
        PropertyDef("area_filter", "Raum (optional)", "text", "", group="Inhalt"),
        PropertyDef("max_items", "Max. Einträge", "number", 8, min=1, max=30, group="Inhalt"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.title_label = QLabel(self.get_prop("name") or "Entitäten")
        self.title_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 600; border: none; background: transparent;"
        )
        self.content_layout.addWidget(self.title_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(6)
        self.scroll.setWidget(self.list_container)
        self.content_layout.addWidget(self.scroll)

    def refresh_from_state(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.state_manager:
            return
        domain = self.get_prop("domain_filter", "light")
        area = self.get_prop("area_filter", "").lower()
        max_items = int(self.get_prop("max_items", 8))
        count = 0
        for entity_id, e in self.state_manager.entities.items():
            if domain != "all" and e.domain != domain:
                continue
            if area and area not in e.area.lower():
                continue
            row = QHBoxLayout()
            name = QLabel(e.friendly_name)
            name.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: 13px; border: none; background: transparent;")
            state = QLabel(e.state)
            state.setStyleSheet(f"color: {self.get_prop('accent_color', '#4C8DFF')}; font-size: 13px; border: none; background: transparent;")
            row.addWidget(name, 1)
            row.addWidget(state)
            wrapper = QWidget()
            wrapper.setLayout(row)
            self.list_layout.addWidget(wrapper)
            count += 1
            if count >= max_items:
                break
        self.list_layout.addStretch()
