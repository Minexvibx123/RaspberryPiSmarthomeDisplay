"""Verification for the list-based Workflow engine (WHEN/THEN/WAIT)."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QCoreApplication, QObject, QTimer, Signal  # noqa: E402

from app.core.database import Database  # noqa: E402
from app.core.workflows import WorkflowEngine  # noqa: E402


class _FakeStateManager(QObject):
    entity_updated = Signal(str, dict)

    def __init__(self):
        super().__init__()
        self.calls: list[tuple[str, str, str]] = []

    def call_service(self, domain, service, entity_id=None, **_data):
        self.calls.append((domain, service, entity_id))


app = QCoreApplication(sys.argv)

root = Path(tempfile.mkdtemp(prefix="homepanel_workflow_"))
try:
    db = Database(root / "homepanel.db")
    db.save_workflow(
        "Motion turns light on then off", "sensor.motion", "on",
        steps=[
            {"kind": "action", "domain": "light", "service": "turn_on", "entity_id": "light.living_room", "data": {}},
            {"kind": "wait", "seconds": 0.05},
            {"kind": "action", "domain": "light", "service": "turn_off", "entity_id": "light.living_room", "data": {}},
        ],
    )

    fake = _FakeStateManager()
    engine = WorkflowEngine(db, fake)
    fake.entity_updated.emit("sensor.motion", {"state": "on"})

    QTimer.singleShot(500, app.quit)
    app.exec()

    assert fake.calls == [
        ("light", "turn_on", "light.living_room"),
        ("light", "turn_off", "light.living_room"),
    ], f"unexpected calls: {fake.calls}"

    # non-matching trigger state must not run the workflow
    fake.calls.clear()
    fake.entity_updated.emit("sensor.motion", {"state": "off"})
    QTimer.singleShot(150, app.quit)
    app.exec()
    assert fake.calls == [], f"workflow ran on non-matching trigger: {fake.calls}"

    # persistence round-trip
    loaded = db.list_workflows()
    assert len(loaded) == 1 and loaded[0].trigger_entity == "sensor.motion"
    db.set_workflow_enabled(loaded[0].id, False)
    assert db.list_workflows(enabled_only=True) == []
finally:
    shutil.rmtree(root, ignore_errors=True)

print("VERIFICATION PASSED")
