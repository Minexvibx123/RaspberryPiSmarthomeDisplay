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
        self._stopped = False
        state_manager.entity_updated.connect(self._on_entity_updated)

    def stop(self) -> None:
        self._stopped = True
        try:
            self.state_manager.entity_updated.disconnect(self._on_entity_updated)
        except (RuntimeError, TypeError):
            pass

    def _on_entity_updated(self, entity_id: str, new_state: dict) -> None:
        if self._stopped:
            return
        for workflow in self.db.list_workflows(enabled_only=True):
            if workflow.trigger_entity == entity_id and str(new_state.get("state")) == workflow.trigger_state:
                self._run(workflow.steps)

    def _run(self, steps: list) -> None:
        self._run_step(steps, 0)

    def _run_step(self, steps: list, index: int) -> None:
        if self._stopped or index >= len(steps):
            return
        step = steps[index]
        kind = step.get("kind")
        if kind == "wait":
            seconds = float(step.get("seconds", 0))
            QTimer.singleShot(max(0, int(seconds * 1000)), lambda: self._run_step(steps, index + 1))
            return
        if kind == "action":
            action = {
                "domain": step.get("domain", ""),
                "service": step.get("service", ""),
                "entity_id": step.get("entity_id") or None,
                "data": step.get("data", {}),
            }
            self.state_manager.run_service_actions(
                [action],
                on_finished=lambda success, error: self._continue_after_action(
                    steps, index, success, error, action,
                ),
            )
            return
        self._run_step(steps, index + 1)

    def _continue_after_action(self, steps: list, index: int, success: bool,
                               error: str, action: dict) -> None:
        if self._stopped:
            return
        if not success:
            logger.warning("Workflow step failed (%s): %s", error, action)
            return
        self._run_step(steps, index + 1)
