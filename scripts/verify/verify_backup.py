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
    target.set_setting("ha_token", "local-token")
    target.save_template("Obsolete", "widget", {"old": True})
    target.import_config(export_without_secrets, replace=True)
    assert target.get_setting("ha_token") == "local-token"
    assert len(target.list_templates()) == 1
    assert len(target.list_workflows()) == 1
    assert target.list_workflows()[0].trigger_entity == "sensor.motion"
    assert all(template.name != "Obsolete" for template in target.list_templates())

    before_pages = [page.name for page in target.list_pages()]
    before_templates = [template.name for template in target.list_templates()]
    broken_import = dict(export_without_secrets)
    broken_import["widgets"] = [{
        "page_id": 999999, "type": "sensor", "x": 0, "y": 0,
        "w": 100, "h": 100, "z": 0, "config": {},
    }]
    try:
        target.import_config(broken_import, replace=True)
    except Exception:
        pass
    else:
        raise AssertionError("invalid import unexpectedly succeeded")
    assert [page.name for page in target.list_pages()] == before_pages
    assert [template.name for template in target.list_templates()] == before_templates
    assert target.get_setting("ha_token") == "local-token"

    unsupported = dict(export_without_secrets, format_version=999)
    try:
        target.import_config(unsupported, replace=True)
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported config version unexpectedly succeeded")
finally:
    shutil.rmtree(root, ignore_errors=True)

print("VERIFICATION PASSED")
