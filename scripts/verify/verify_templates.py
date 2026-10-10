"""Verification for SQLite-backed widget templates."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.database import Database  # noqa: E402

root = Path(tempfile.mkdtemp(prefix="homepanel_templates_"))
try:
    db = Database(root / "homepanel.db")
    saved = db.save_template("Temperature compact", "widget", {"unit": "C"}, "sensor")
    loaded = db.get_template(saved.id)
    templates = db.list_templates("widget")
    assert loaded is not None and loaded.config == {"unit": "C"}
    assert [(template.name, template.type) for template in templates] == [("Temperature compact", "sensor")]

    actions = [{"domain": "media_player", "service": "media_pause", "entity_id": "media_player.sonos", "data": {}}]
    action_template = db.save_template("Pause Sonos", "service_actions", {"actions": actions})
    loaded_actions = db.get_template(action_template.id)
    assert loaded_actions is not None and loaded_actions.kind == "service_actions"
    assert loaded_actions.config["actions"] == actions
    assert [template.name for template in db.list_templates("service_actions")] == ["Pause Sonos"]

    db.delete_template(saved.id)
    assert db.list_templates("widget") == []
finally:
    shutil.rmtree(root, ignore_errors=True)

print("VERIFICATION PASSED")