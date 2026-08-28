"""Dynamic properties panel - built entirely from a widget's PropertyDef schema.

This is what makes "tap element -> change properties" work generically: the
panel has zero widget-specific code, it just renders whatever fields the
selected widget declares.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.ui.element_library import EntityPickerDialog
from app.widgets.base import BaseWidget
from app.widgets.icons import ICON_NAMES, IconGlyph


class PropertiesPanel(QWidget):
    changed = Signal()
    size_changed = Signal()
    delete_requested = Signal()
    duplicate_requested = Signal()

    def __init__(self, state_manager, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        self.widget_instance: Optional[BaseWidget] = None
        self.db = None

        outer = QVBoxLayout(self)
        self.title_label = QLabel("Kein Element ausgewählt")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        outer.addWidget(self.title_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.form_container = QWidget()
        self.form_layout = QVBoxLayout(self.form_container)
        scroll.setWidget(self.form_container)
        outer.addWidget(scroll, 1)

        actions = QHBoxLayout()
        self.dup_btn = QPushButton("Duplizieren")
        self.del_btn = QPushButton("Löschen")
        self.dup_btn.clicked.connect(self.duplicate_requested.emit)
        self.del_btn.clicked.connect(self.delete_requested.emit)
        actions.addWidget(self.dup_btn)
        actions.addWidget(self.del_btn)
        outer.addLayout(actions)

        self.set_widget(None, None)

    def set_multi_selected(self, count: int, db) -> None:
        self.widget_instance = None
        self.db = db
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        self.dup_btn.setEnabled(False)
        self.del_btn.setEnabled(True)

        self.title_label.setText(f"{count} Elemente ausgewählt")

    def set_widget(self, widget_instance: Optional[BaseWidget], db) -> None:
        self.widget_instance = widget_instance
        self.db = db
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        enabled = widget_instance is not None
        self.dup_btn.setEnabled(enabled)
        self.del_btn.setEnabled(enabled)

        if not widget_instance:
            self.title_label.setText("Kein Element ausgewählt")
            return

        self.title_label.setText(widget_instance.display_name)

        db_widget = self.db.get_widget(widget_instance.widget_id) if self.db else None
        if db_widget:
            size_box = QGroupBox("Größe & Position")
            size_form = QFormLayout()
            size_box.setLayout(size_form)

            self.width_spin = QDoubleSpinBox()
            self.width_spin.setRange(40, 4000)
            self.width_spin.setValue(db_widget.w)
            self.width_spin.valueChanged.connect(lambda v: self._update_geometry("w", v))
            size_form.addRow("Breite", self.width_spin)

            self.height_spin = QDoubleSpinBox()
            self.height_spin.setRange(30, 4000)
            self.height_spin.setValue(db_widget.h)
            self.height_spin.valueChanged.connect(lambda v: self._update_geometry("h", v))
            size_form.addRow("Höhe", self.height_spin)

            self.x_spin = QDoubleSpinBox()
            self.x_spin.setRange(-4000, 4000)
            self.x_spin.setValue(db_widget.x)
            self.x_spin.valueChanged.connect(lambda v: self._update_geometry("x", v))
            size_form.addRow("Position X", self.x_spin)

            self.y_spin = QDoubleSpinBox()
            self.y_spin.setRange(-4000, 4000)
            self.y_spin.setValue(db_widget.y)
            self.y_spin.valueChanged.connect(lambda v: self._update_geometry("y", v))
            size_form.addRow("Position Y", self.y_spin)

            self.form_layout.addWidget(size_box)

        groups: dict[str, QFormLayout] = {}
        for prop in widget_instance.full_schema():
            if prop.group not in groups:
                box = QGroupBox(prop.group)
                form = QFormLayout()
                box.setLayout(form)
                self.form_layout.addWidget(box)
                groups[prop.group] = form
            form = groups[prop.group]
            field_widget = self._build_field(prop, widget_instance)
            form.addRow(prop.label, field_widget)
        self.form_layout.addStretch()

    # ------------------------------------------------------------------ #
    def _build_field(self, prop, instance: BaseWidget) -> QWidget:
        value = instance.get_prop(prop.key)

        if prop.type == "text":
            edit = QLineEdit(str(value or ""))
            edit.textChanged.connect(lambda text, p=prop.key: self._update(p, text))
            return edit

        if prop.type == "icon":
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            preview = IconGlyph(value or "star", instance.get_prop("accent_color", "#4C8DFF"))
            preview.setFixedSize(28, 28)
            combo = QComboBox()
            combo.addItems(ICON_NAMES)
            if value in ICON_NAMES:
                combo.setCurrentText(value)

            def on_change(text, p=prop.key, prev=preview):
                prev.set_icon(text)
                self._update(p, text)

            combo.currentTextChanged.connect(on_change)
            row.addWidget(preview)
            row.addWidget(combo, 1)
            return container

        if prop.type == "number":
            spin = QDoubleSpinBox()
            spin.setRange(prop.min if prop.min is not None else -100000, prop.max if prop.max is not None else 100000)
            spin.setValue(float(value) if value is not None else 0)
            spin.valueChanged.connect(lambda val, p=prop.key: self._update(p, val))
            return spin

        if prop.type == "bool":
            check = QCheckBox()
            check.setChecked(bool(value))
            check.toggled.connect(lambda checked, p=prop.key: self._update(p, checked))
            return check

        if prop.type == "select":
            combo = QComboBox()
            combo.addItems(prop.options or [])
            if value in (prop.options or []):
                combo.setCurrentText(value)
            combo.currentTextChanged.connect(lambda text, p=prop.key: self._update(p, text))
            return combo

        if prop.type == "color":
            btn = QPushButton(str(value or "#FFFFFF"))
            btn.setStyleSheet(f"background-color: {value or '#FFFFFF'};")
            def pick(_checked=False, p=prop.key, b=btn):
                color = QColorDialog.getColor(QColor(instance.get_prop(p, "#FFFFFF")), self)
                if color.isValid():
                    hex_val = color.name()
                    b.setText(hex_val)
                    b.setStyleSheet(f"background-color: {hex_val};")
                    self._update(p, hex_val)
            btn.clicked.connect(pick)
            return btn

        if prop.type == "image":
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            line = QLineEdit(str(value or ""))
            line.setReadOnly(True)
            browse = QPushButton("Durchsuchen\u2026")
            clear = QPushButton("\u2715")
            clear.setFixedWidth(28)

            def on_browse(_checked=False, p=prop.key, le=line):
                path, _ = QFileDialog.getOpenFileName(
                    self, "Bild auswählen", "",
                    "Bilder (*.png *.jpg *.jpeg *.svg *.webp *.gif *.bmp)",
                )
                if path:
                    le.setText(path)
                    self._update(p, path)

            def on_clear(_checked=False, p=prop.key, le=line):
                le.setText("")
                self._update(p, "")

            browse.clicked.connect(on_browse)
            clear.clicked.connect(on_clear)
            row.addWidget(line, 1)
            row.addWidget(browse)
            row.addWidget(clear)
            return container

        if prop.type == "entity":
            btn = QPushButton(value or "Entity auswählen...")
            def pick(_checked=False, p=prop.key, b=btn):
                dlg = EntityPickerDialog(self.state_manager, domain_filter=prop.entity_domains, parent=self)
                if dlg.exec() and dlg.selected_entity_id:
                    b.setText(dlg.selected_entity_id)
                    self._update(p, dlg.selected_entity_id)
            btn.clicked.connect(pick)
            return btn

        return QLabel(str(value))

    def _update(self, key: str, value) -> None:
        if not self.widget_instance or not self.db:
            return
        self.widget_instance.config[key] = value
        self.db.update_widget(self.widget_instance.widget_id, config=self.widget_instance.config)
        self.widget_instance.apply_config(self.widget_instance.config)
        self.changed.emit()

    def _update_geometry(self, field: str, value: float) -> None:
        if not self.widget_instance or not self.db:
            return
        self.db.update_widget(self.widget_instance.widget_id, **{field: value})
        self.size_changed.emit()
