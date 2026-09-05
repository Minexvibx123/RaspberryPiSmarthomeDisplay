"""User-assembled widgets built from a small element palette (no Python).

Elements live as JSON in ``config["elements"]`` and are positioned absolutely
inside the widget; text-like elements are bound to entities using the safe
expression templates from :mod:`app.core.expressions`. Editing happens via
the "Elemente bearbeiten" action button in the standard Property Editor.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QPushButton

from app.core.expressions import ExpressionError, render_template
from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph


class CustomWidget(BaseWidget):
    type_name = "custom_widget"
    display_name = "Eigenes Widget"
    category = "Custom"
    icon = "\U0001F9E9"
    default_size = (220, 160)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("elements", "Elemente bearbeiten", "action", action="custom_widget_elements", group="Elemente"),
    ]

    def build_ui(self) -> None:
        for child in getattr(self, "_element_widgets", []):
            child.deleteLater()
        self._element_widgets = [self._create_element(element) for element in self.config.get("elements", [])]

    def _create_element(self, element: dict):
        kind = element.get("type", "text")
        color = element.get("color", "#FFFFFF")
        if kind == "icon":
            widget = IconGlyph(element.get("icon", "star"), color, parent=self)
        elif kind == "progress_bar":
            widget = QProgressBar(self)
            widget.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")
        elif kind == "button":
            widget = QPushButton(element.get("template", ""), self)
            entity_id = element.get("entity_id", "")
            if entity_id:
                widget.clicked.connect(lambda _checked=False, e=entity_id: self._toggle_entity(e))
        else:  # text | sensor_value
            widget = QLabel(self)
            widget.setStyleSheet(f"color: {color};")
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget.setGeometry(int(element.get("x", 0)), int(element.get("y", 0)), int(element.get("w", 100)), int(element.get("h", 30)))
        widget.show()
        return widget

    def refresh_from_state(self) -> None:
        elements = self.config.get("elements", [])
        for widget, element in zip(getattr(self, "_element_widgets", []), elements):
            self._update_element(widget, element)

    def _update_element(self, widget, element: dict) -> None:
        kind = element.get("type", "text")
        entity_id = element.get("entity_id", "")
        entity = self.state_manager.get_entity(entity_id) if self.state_manager and entity_id else None
        context = {"state": entity.state if entity else ""}
        if kind == "icon":
            return
        try:
            text = render_template(element.get("template", "{{ state }}"), context)
        except ExpressionError as exc:
            text = f"[Fehler: {exc}]"
        if kind == "progress_bar":
            try:
                widget.setValue(max(0, min(100, int(float(context["state"] or 0)))))
            except (TypeError, ValueError):
                widget.setValue(0)
        else:
            widget.setText(text)

    def _toggle_entity(self, entity_id: str) -> None:
        if not self.state_manager or "." not in entity_id:
            return
        domain = entity_id.split(".", 1)[0]
        self.state_manager.call_service(domain, "toggle", entity_id=entity_id)
