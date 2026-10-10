"""Small visual editor for ordered Home Assistant service actions."""
from __future__ import annotations

import json
import re

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QMessageBox, QPushButton, QScrollArea, QVBoxLayout,
    QWidget, QInputDialog, QListWidgetItem,
)


class ServiceActionsDialog(QDialog):
    def __init__(self, actions: list[dict], parent=None, db=None):
        super().__init__(parent)
        self.setWindowTitle("Home-Assistant-Aktionen")
        self.resize(620, 520)
        self.db = db
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

        action_buttons = QHBoxLayout()
        add_button = QPushButton("Aktion hinzufügen")
        add_button.clicked.connect(lambda: self._add_row({}))
        action_buttons.addWidget(add_button)
        if self.db is not None:
            load_button = QPushButton("Vorlage laden")
            load_button.clicked.connect(self._load_template)
            save_button = QPushButton("Als Vorlage speichern")
            save_button.clicked.connect(self._save_template)
            action_buttons.addWidget(load_button)
            action_buttons.addWidget(save_button)
        layout.addLayout(action_buttons)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        for action in actions:
            self._add_row(action)

    def _load_template(self) -> None:
        templates = self.db.list_templates("service_actions")
        if not templates:
            QMessageBox.information(self, "Aktionsvorlagen", "Noch keine Aktionsvorlagen gespeichert.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Aktionsvorlage laden")
        layout = QVBoxLayout(dialog)
        template_list = QListWidget()
        for template in templates:
            item = QListWidgetItem(template.name)
            item.setData(0x0100, template.id)
            template_list.addItem(item)
        template_list.setCurrentRow(0)
        layout.addWidget(template_list)
        buttons = QDialogButtonBox(QDialogButtonBox.Open | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if not dialog.exec() or template_list.currentItem() is None:
            return
        template = self.db.get_template(template_list.currentItem().data(0x0100))
        actions = template.config.get("actions") if template and isinstance(template.config, dict) else None
        if not isinstance(actions, list) or any(not isinstance(action, dict) for action in actions):
            QMessageBox.warning(self, "Ungültige Vorlage", "Die gespeicherte Aktionsliste ist ungültig.")
            return
        for row in list(self._rows):
            self._remove_row(row)
        for action in actions:
            self._add_row(action)

    def _save_template(self) -> None:
        try:
            actions = self.actions()
        except (ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Ungültige Aktion", str(exc))
            return
        name, accepted = QInputDialog.getText(self, "Aktionsvorlage", "Name der Vorlage:")
        name = name.strip()
        if not accepted or not name:
            return
        existing = next((template for template in self.db.list_templates() if template.name == name), None)
        if existing and existing.kind != "service_actions":
            QMessageBox.warning(
                self, "Name bereits verwendet",
                "Dieser Name wird bereits von einer anderen Vorlagenart verwendet.",
            )
            return
        if existing:
            answer = QMessageBox.question(
                self, "Vorlage überschreiben?",
                f"Die Vorlage „{name}“ existiert bereits. Überschreiben?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self.db.save_template(name, "service_actions", {"actions": actions})
        QMessageBox.information(self, "Aktionsvorlage", "Vorlage gespeichert.")

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