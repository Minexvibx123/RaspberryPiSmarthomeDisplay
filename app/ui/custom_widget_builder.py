"""Visual, no-Python builder dialog for CustomWidget elements.

Elements are assembled from a small palette (Text, Icon, Sensor Value,
Progress Bar, Button) and bound to entities using the safe expression
templates from :mod:`app.core.expressions`. Persistence reuses the existing
PropertiesPanel -> Database update path, no parallel storage is created.
"""
from __future__ import annotations

import copy

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QSpinBox, QVBoxLayout,
)

from app.ui.element_library import EntityPickerDialog

ELEMENT_TYPES = ["text", "icon", "sensor_value", "progress_bar", "button"]


def open_custom_widget_builder(properties_panel, widget_instance) -> None:
    elements = copy.deepcopy(widget_instance.config.get("elements", []))

    dialog = QDialog(properties_panel)
    dialog.setWindowTitle("Widget-Elemente bearbeiten")
    dialog.resize(480, 420)
    layout = QVBoxLayout(dialog)

    element_list = QListWidget()

    def refresh_list() -> None:
        element_list.clear()
        for element in elements:
            label = element.get("template") or element.get("icon", "")
            element_list.addItem(QListWidgetItem(f"{element['type']}: {label}"))

    refresh_list()
    layout.addWidget(element_list, 1)

    add_row = QHBoxLayout()
    type_combo = QComboBox()
    type_combo.addItems(ELEMENT_TYPES)
    add_btn = QPushButton("+ Element hinzufügen")

    def add_element() -> None:
        elements.append({
            "type": type_combo.currentText(), "template": "{{ state }}", "entity_id": "",
            "icon": "star", "color": "#FFFFFF", "x": 10, "y": 10, "w": 150, "h": 40,
        })
        refresh_list()
        element_list.setCurrentRow(len(elements) - 1)

    add_btn.clicked.connect(add_element)
    add_row.addWidget(type_combo)
    add_row.addWidget(add_btn)
    layout.addLayout(add_row)

    form = QFormLayout()
    template_edit = QLineEdit()
    entity_btn = QPushButton("Entity auswählen...")
    x_spin, y_spin, w_spin, h_spin = QSpinBox(), QSpinBox(), QSpinBox(), QSpinBox()
    for spin in (x_spin, y_spin, w_spin, h_spin):
        spin.setRange(0, 2000)
    form.addRow("Text/Vorlage", template_edit)
    form.addRow("Entity", entity_btn)
    position_row = QHBoxLayout()
    for spin in (x_spin, y_spin, w_spin, h_spin):
        position_row.addWidget(spin)
    form.addRow("Position/Größe (x, y, w, h)", position_row)
    layout.addLayout(form)

    remove_btn = QPushButton("Element entfernen")
    layout.addWidget(remove_btn)

    def selected_index() -> int:
        return element_list.currentRow()

    def load_selected(row: int) -> None:
        if row < 0 or row >= len(elements):
            return
        element = elements[row]
        template_edit.setText(element.get("template", ""))
        entity_btn.setText(element.get("entity_id") or "Entity auswählen...")
        x_spin.setValue(int(element.get("x", 0)))
        y_spin.setValue(int(element.get("y", 0)))
        w_spin.setValue(int(element.get("w", 100)))
        h_spin.setValue(int(element.get("h", 30)))

    def save_selected() -> None:
        row = selected_index()
        if row < 0:
            return
        element = elements[row]
        element["template"] = template_edit.text()
        element["x"], element["y"] = x_spin.value(), y_spin.value()
        element["w"], element["h"] = w_spin.value(), h_spin.value()
        refresh_list()
        element_list.setCurrentRow(row)

    for widget in (template_edit,):
        widget.editingFinished.connect(save_selected)
    for spin in (x_spin, y_spin, w_spin, h_spin):
        spin.valueChanged.connect(lambda _value: save_selected())

    def pick_entity() -> None:
        row = selected_index()
        if row < 0:
            return
        picker = EntityPickerDialog(properties_panel.state_manager, parent=dialog)
        if picker.exec() and picker.selected_entity_id:
            elements[row]["entity_id"] = picker.selected_entity_id
            entity_btn.setText(picker.selected_entity_id)

    entity_btn.clicked.connect(pick_entity)

    def remove_selected() -> None:
        row = selected_index()
        if row < 0:
            return
        elements.pop(row)
        refresh_list()

    remove_btn.clicked.connect(remove_selected)
    element_list.currentRowChanged.connect(load_selected)
    if elements:
        element_list.setCurrentRow(0)

    buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
    buttons.rejected.connect(dialog.reject)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)

    if dialog.exec():
        properties_panel._update("elements", elements)
