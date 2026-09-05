"""Minimal, list-based Workflow engine (Phase 5 foundation).

A workflow is: WHEN <entity> reaches <state> THEN <steps...>, where each step
is either an ``action`` (call_service) or a ``wait`` (delay in seconds before
the next step). This intentionally stays list-based per the master prompt -
a node-based editor can be built on top of this later without changing the
storage format or execution engine.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QTimer

logger = logging.getLogger(__name__)


class WorkflowEngine(QObject):
    def __init__(self, db, state_manager, parent=None):
        super().__init__(parent)
        self.db = db
        self.state_manager = state_manager
        state_manager.entity_updated.connect(self._on_entity_updated)

    def _on_entity_updated(self, entity_id: str, new_state: dict) -> None:
        for workflow in self.db.list_workflows(enabled_only=True):
            if workflow.trigger_entity == entity_id and str(new_state.get("state")) == workflow.trigger_state:
                self._run(workflow.steps)

    def _run(self, steps: list) -> None:
        self._run_step(steps, 0)

    def _run_step(self, steps: list, index: int) -> None:
        if index >= len(steps):
            return
        step = steps[index]
        kind = step.get("kind")
        if kind == "wait":
            seconds = float(step.get("seconds", 0))
            QTimer.singleShot(max(0, int(seconds * 1000)), lambda: self._run_step(steps, index + 1))
            return
        if kind == "action":
            try:
                self.state_manager.call_service(
                    step.get("domain", ""), step.get("service", ""),
                    entity_id=step.get("entity_id") or None, **step.get("data", {}),
                )
            except Exception:  # noqa: BLE001 - a broken workflow step must never crash the panel
                logger.exception("Workflow step failed: %s", step)
        self._run_step(steps, index + 1)
