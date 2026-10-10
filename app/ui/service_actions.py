"""Small visual editor for ordered Home Assistant service actions."""
from __future__ import annotations

import json
import re

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)


class ServiceActionsDialog(QDialog):
    def __init__(self, actions: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Home-Assistant-Aktionen")
        self.resize(620, 520)
        self._rows: list[dict[str, QWidget]] = []
        actions = actions if isinstance(actions, list) else []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Aktionen werden der Reihe nach ausgeführt. Ein Fehler stoppt die Kette."))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._rows_widget = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_widget)
        self._rows_layout.addStretch()
        scroll.setWidget(self._rows_widget)
        layout.addWidget(scroll, 1)

        add_button = QPushButton("Aktion hinzufügen")
        add_button.clicked.connect(lambda: self._add_row({}))
        layout.addWidget(add_button)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        for action in actions:
            self._add_row(action)

    def _add_row(self, action: dict) -> None:
        row_widget = QWidget()
        form = QFormLayout(row_widget)
        domain = QComboBox()
        domain.setEditable(True)
        domain.addItems([
            "light", "switch", "cover", "climate", "media_player", "scene",
            "script", "fan", "lock", "notify",
        ])
        domain.setCurrentText(str(action.get("domain", "")))
        service = QLineEdit(str(action.get("service", "")))
        entity_id = QLineEdit(str(action.get("entity_id", "") or ""))
        entity_id.setPlaceholderText("Optional, z. B. light.wohnzimmer")
        data = QLineEdit(json.dumps(action.get("data", {}), ensure_ascii=False))
        data.setPlaceholderText("{}")
        form.addRow("Domain", domain)
        form.addRow("Service", service)
        form.addRow("Entity-ID", entity_id)
        form.addRow("Parameter (JSON-Objekt)", data)
        header = QHBoxLayout()
        header.addWidget(QLabel(f"Aktion {len(self._rows) + 1}"), 1)
        remove = QPushButton("Entfernen")
        header.addWidget(remove)
        form.insertRow(0, header)
        self._rows_layout.insertWidget(self._rows_layout.count() - 1, row_widget)
        row = {"widget": row_widget, "domain": domain, "service": service,
               "entity_id": entity_id, "data": data}
        self._rows.append(row)
        remove.clicked.connect(lambda: self._remove_row(row))

    def _remove_row(self, row: dict[str, QWidget]) -> None:
        self._rows.remove(row)
        row["widget"].deleteLater()

    def _accept_if_valid(self) -> None:
        try:
            self.actions()
        except (ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Ungültige Aktion", str(exc))
            return
        self.accept()

    def actions(self) -> list[dict]:
        result = []
        for index, row in enumerate(self._rows, start=1):
            domain = row["domain"].currentText().strip()
            service = row["service"].text().strip()
            if not re.fullmatch(r"[a-z0-9_]+", domain) or not re.fullmatch(r"[a-z0-9_]+", service):
                raise ValueError(f"Aktion {index}: Domain und Service müssen gültige Home-Assistant-Namen sein.")
            data = json.loads(row["data"].text() or "{}")
            if not isinstance(data, dict):
                raise ValueError(f"Aktion {index}: Parameter müssen ein JSON-Objekt sein.")
            result.append({
                "domain": domain,
                "service": service,
                "entity_id": row["entity_id"].text().strip(),
                "data": data,
            })
        return result