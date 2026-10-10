"""Touch-oriented editor for saved Home Assistant workflows."""
from __future__ import annotations

import copy
import re

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout,
    QWidget, QInputDialog,
)

from app.ui.service_actions import ServiceActionsDialog


class WorkflowEditDialog(QDialog):
    def __init__(self, db, workflow=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.workflow = workflow
        self.setWindowTitle("Automation bearbeiten" if workflow else "Automation erstellen")
        self.resize(620, 540)
        self.steps = copy.deepcopy(workflow.steps if workflow else [])

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(workflow.name if workflow else "")
        self.entity_edit = QLineEdit(workflow.trigger_entity if workflow else "")
        self.entity_edit.setPlaceholderText("z. B. binary_sensor.bewegung")
        self.state_edit = QLineEdit(workflow.trigger_state if workflow else "on")
        form.addRow("Name", self.name_edit)
        form.addRow("Auslöser-Entity", self.entity_edit)
        form.addRow("Zustand", self.state_edit)
        layout.addLayout(form)

        layout.addWidget(QLabel("Schritte werden der Reihe nach ausgeführt. Ein fehlgeschlagener Service stoppt den Ablauf."))
        self.step_list = QListWidget()
        layout.addWidget(self.step_list, 1)
        self._refresh_steps()

        controls = QHBoxLayout()
        for label, callback in (
            ("Aktionen hinzufügen", self._add_actions),
            ("Wartezeit", self._add_wait),
            ("Bearbeiten", self._edit_step),
            ("Nach oben", lambda: self._move_step(-1)),
            ("Nach unten", lambda: self._move_step(1)),
            ("Entfernen", self._remove_step),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _step_label(self, step: dict, index: int) -> str:
        if step.get("kind") == "wait":
            return f"{index}. Warte {step.get('seconds', 0)} Sekunden"
        return (
            f"{index}. {step.get('domain', '')}.{step.get('service', '')} "
            f"{step.get('entity_id') or ''}"
        ).strip()

    def _refresh_steps(self, selected: int | None = None) -> None:
        self.step_list.clear()
        for index, step in enumerate(self.steps, start=1):
            self.step_list.addItem(self._step_label(step, index))
        if self.steps:
            self.step_list.setCurrentRow(selected if selected is not None else len(self.steps) - 1)

    def _add_actions(self) -> None:
        dialog = ServiceActionsDialog([], self, db=self.db)
        if not dialog.exec():
            return
        self.steps.extend({"kind": "action", **action} for action in dialog.actions())
        self._refresh_steps()

    def _add_wait(self) -> None:
        seconds, accepted = QInputDialog.getDouble(
            self, "Wartezeit", "Sekunden:", 1.0, 0.1, 3600.0, 1,
        )
        if accepted:
            self.steps.append({"kind": "wait", "seconds": seconds})
            self._refresh_steps()

    def _edit_step(self) -> None:
        index = self.step_list.currentRow()
        if not 0 <= index < len(self.steps):
            return
        step = self.steps[index]
        if step.get("kind") == "wait":
            seconds, accepted = QInputDialog.getDouble(
                self, "Wartezeit bearbeiten", "Sekunden:",
                float(step.get("seconds", 1)), 0.1, 3600.0, 1,
            )
            if accepted:
                self.steps[index] = {"kind": "wait", "seconds": seconds}
                self._refresh_steps(index)
            return
        action = {key: value for key, value in step.items() if key != "kind"}
        dialog = ServiceActionsDialog([action], self, db=self.db)
        if dialog.exec():
            replacement = [{"kind": "action", **item} for item in dialog.actions()]
            self.steps[index:index + 1] = replacement
            self._refresh_steps(index)

    def _remove_step(self) -> None:
        index = self.step_list.currentRow()
        if 0 <= index < len(self.steps):
            self.steps.pop(index)
            self._refresh_steps(min(index, len(self.steps) - 1) if self.steps else None)

    def _move_step(self, delta: int) -> None:
        index = self.step_list.currentRow()
        target = index + delta
        if 0 <= index < len(self.steps) and 0 <= target < len(self.steps):
            self.steps[index], self.steps[target] = self.steps[target], self.steps[index]
            self._refresh_steps(target)

    def _accept_if_valid(self) -> None:
        name = self.name_edit.text().strip()
        entity = self.entity_edit.text().strip()
        state = self.state_edit.text().strip()
        if not name or not re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", entity) or not state:
            QMessageBox.warning(
                self, "Ungültiger Auslöser",
                "Name, gültige Entity-ID und Zielzustand sind erforderlich.",
            )
            return
        if not self.steps:
            QMessageBox.warning(self, "Keine Schritte", "Füge mindestens einen Aktions- oder Warte-Schritt hinzu.")
            return
        self.accept()

    def workflow_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "trigger_entity": self.entity_edit.text().strip(),
            "trigger_state": self.state_edit.text().strip(),
            "steps": copy.deepcopy(self.steps),
            "enabled": self.workflow.enabled if self.workflow else True,
            "workflow_id": self.workflow.id if self.workflow else None,
        }


class WorkflowManagerWidget(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        layout = QVBoxLayout(self)
        self.workflow_list = QListWidget()
        layout.addWidget(self.workflow_list, 1)
        buttons = QHBoxLayout()
        for label, callback in (
            ("Neu", self._create_workflow),
            ("Bearbeiten", self._edit_workflow),
            ("Aktivieren / Deaktivieren", self._toggle_workflow),
            ("Löschen", self._delete_workflow),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        selected_id = self._selected_id()
        self.workflow_list.clear()
        for workflow in self.db.list_workflows():
            state = "aktiv" if workflow.enabled else "inaktiv"
            item = QListWidgetItem(
                f"{workflow.name}  ·  {workflow.trigger_entity} = {workflow.trigger_state}  ·  {state}"
            )
            item.setData(0x0100, workflow.id)
            self.workflow_list.addItem(item)
            if workflow.id == selected_id:
                self.workflow_list.setCurrentItem(item)

    def _selected_id(self) -> int | None:
        item = self.workflow_list.currentItem()
        return int(item.data(0x0100)) if item else None

    def _edit_dialog(self, workflow=None) -> None:
        dialog = WorkflowEditDialog(self.db, workflow, self)
        if not dialog.exec():
            return
        data = dialog.workflow_data()
        self.db.save_workflow(
            data["name"], data["trigger_entity"], data["trigger_state"],
            data["steps"], data["enabled"], data["workflow_id"],
        )
        self.refresh()

    def _create_workflow(self) -> None:
        self._edit_dialog()

    def _edit_workflow(self) -> None:
        workflow_id = self._selected_id()
        workflow = self.db.get_workflow(workflow_id) if workflow_id is not None else None
        if workflow is None:
            QMessageBox.information(self, "Automation", "Wähle zuerst eine Automation aus.")
            return
        self._edit_dialog(workflow)

    def _toggle_workflow(self) -> None:
        workflow_id = self._selected_id()
        workflow = self.db.get_workflow(workflow_id) if workflow_id is not None else None
        if workflow is None:
            QMessageBox.information(self, "Automation", "Wähle zuerst eine Automation aus.")
            return
        self.db.set_workflow_enabled(workflow.id, not workflow.enabled)
        self.refresh()

    def _delete_workflow(self) -> None:
        workflow_id = self._selected_id()
        workflow = self.db.get_workflow(workflow_id) if workflow_id is not None else None
        if workflow is None:
            QMessageBox.information(self, "Automation", "Wähle zuerst eine Automation aus.")
            return
        answer = QMessageBox.question(
            self, "Automation löschen?", f"„{workflow.name}“ wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.db.delete_workflow(workflow.id)
            self.refresh()