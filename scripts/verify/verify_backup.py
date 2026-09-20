"""Verification for extended backup export/import: templates, workflows, secrets."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.database import Database  # noqa: E402

root = Path(tempfile.mkdtemp(prefix="homepanel_backup_"))
try:
    db = Database(root / "source.db")
    db.set_setting("ha_token", "super-secret-token")
    db.set_setting("plugin.pihole.sid", "secret-session-id")
    db.set_setting("plugin.docker.password", "secret-password")
    db.set_setting("language", "de")
    db.save_template("Temperature Modern", "widget", {"unit": "C"}, "sensor")
    db.save_workflow("Motion Light", "sensor.motion", "on", steps=[{"kind": "action", "domain": "light", "service": "turn_on"}])

    export_without_secrets = db.export_config(include_secrets=False)
    assert "ha_token" not in export_without_secrets["settings"]
    assert "plugin.pihole.sid" not in export_without_secrets["settings"]
    assert "plugin.docker.password" not in export_without_secrets["settings"]
    assert export_without_secrets["settings"].get("language") == "de"
    assert len(export_without_secrets["templates"]) == 1
    assert len(export_without_secrets["workflows"]) == 1

    export_with_secrets = db.export_config(include_secrets=True)
    assert export_with_secrets["settings"].get("ha_token") == "super-secret-token"

    target = Database(root / "target.db")
    target.import_config(export_without_secrets, replace=True)
    assert target.get_setting("ha_token") is None
    assert len(target.list_templates()) == 1
    assert len(target.list_workflows()) == 1
    assert target.list_workflows()[0].trigger_entity == "sensor.motion"
finally:
    shutil.rmtree(root, ignore_errors=True)

print("VERIFICATION PASSED")
