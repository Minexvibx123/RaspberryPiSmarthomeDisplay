"""Searchable, read-only overview of Home Assistant entities."""
from __future__ import annotations

import json

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)


class DeviceCenterView(QWidget):
    def __init__(self, state_manager, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        title = QLabel("Geräte")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        layout.addWidget(title)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Name oder Entity-ID suchen")
        self.search.textChanged.connect(self.refresh)
        filters.addWidget(self.search, 1)
        self.domain_filter = QComboBox()
        self.domain_filter.addItems(["Alle", "light", "switch", "sensor", "binary_sensor", "media_player", "climate", "cover", "person"])
        self.domain_filter.currentTextChanged.connect(self.refresh)
        filters.addWidget(self.domain_filter)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Raum", "Gerät", "Typ", "Zustand"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_details)
        layout.addWidget(self.table, 3)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(150)
        self.details.setPlaceholderText("Gerät auswählen, um Details anzuzeigen.")
        layout.addWidget(self.details, 1)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self.refresh)
        if self.state_manager:
            self.state_manager.entities_loaded.connect(self.refresh)
            self.state_manager.entity_updated.connect(lambda *_args: self._refresh_timer.start(120))
        self.refresh()

    def refresh(self, *_args) -> None:
        selected = self.selected_entity_id()
        query = self.search.text().casefold().strip()
        domain = self.domain_filter.currentText()
        entities = self.state_manager.entities.values() if self.state_manager else []
        rows = []
        for entity in entities:
            if domain != "Alle" and entity.domain != domain:
                continue
            search_text = f"{entity.friendly_name} {entity.entity_id} {entity.area}".casefold()
            if query and query not in search_text:
                continue
            rows.append(entity)
        rows.sort(key=lambda entity: (entity.area.casefold(), entity.friendly_name.casefold()))
        self.table.setRowCount(len(rows))
        for row, entity in enumerate(rows):
            values = (entity.area or "—", entity.friendly_name, entity.domain, entity.state)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, entity.entity_id)
                self.table.setItem(row, column, item)
            if entity.entity_id == selected:
                self.table.selectRow(row)
        self.table.resizeColumnsToContents()
        self.show_details()

    def selected_entity_id(self) -> str | None:
        rows = self.table.selectionModel().selectedRows() if self.table.rowCount() else []
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return str(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def show_details(self) -> None:
        entity_id = self.selected_entity_id()
        entity = self.state_manager.get_entity(entity_id) if entity_id and self.state_manager else None
        if entity is None:
            self.details.clear()
            return
        self.details.setPlainText(json.dumps({
            "entity_id": entity.entity_id,
            "state": entity.state,
            "attributes": entity.attributes,
        }, ensure_ascii=False, indent=2, default=str))