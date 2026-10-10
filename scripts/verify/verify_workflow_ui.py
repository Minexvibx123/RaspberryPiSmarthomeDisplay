"""Offscreen verification for the workflow management UI."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.core.database import Database  # noqa: E402
from app.ui.workflow_editor import WorkflowEditDialog, WorkflowManagerWidget  # noqa: E402


app = QApplication(sys.argv)
root = Path(tempfile.mkdtemp(prefix="homepanel_workflow_ui_"))
try:
    db = Database(root / "homepanel.db")
    dialog = WorkflowEditDialog(db)
    dialog.name_edit.setText("Bewegung Licht")
    dialog.entity_edit.setText("binary_sensor.motion")
    dialog.state_edit.setText("on")
    dialog.steps = [
        {"kind": "action", "domain": "light", "service": "turn_on", "entity_id": "light.hall", "data": {}},
        {"kind": "wait", "seconds": 2.0},
        {"kind": "action", "domain": "light", "service": "turn_off", "entity_id": "light.hall", "data": {}},
    ]
    data = dialog.workflow_data()
    workflow = db.save_workflow(
        data["name"], data["trigger_entity"], data["trigger_state"], data["steps"],
    )
    manager = WorkflowManagerWidget(db)
    assert manager.workflow_list.count() == 1
    manager.workflow_list.setCurrentRow(0)
    manager._toggle_workflow()
    stored = db.get_workflow(workflow.id)
    assert stored is not None and not stored.enabled
    assert "inaktiv" in manager.workflow_list.item(0).text()
    assert stored.steps == data["steps"]
    db.close()
finally:
    shutil.rmtree(root, ignore_errors=True)

print("VERIFICATION PASSED")