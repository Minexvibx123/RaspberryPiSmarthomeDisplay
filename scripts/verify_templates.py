"""Verification for SQLite-backed widget templates."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import Database  # noqa: E402

root = Path(tempfile.mkdtemp(prefix="homepanel_templates_"))
try:
    db = Database(root / "homepanel.db")
    saved = db.save_template("Temperature compact", "widget", {"unit": "C"}, "sensor")
    loaded = db.get_template(saved.id)
    templates = db.list_templates("widget")
    assert loaded is not None and loaded.config == {"unit": "C"}
    assert [(template.name, template.type) for template in templates] == [("Temperature compact", "sensor")]
    db.delete_template(saved.id)
    assert db.list_templates("widget") == []
finally:
    shutil.rmtree(root, ignore_errors=True)

print("VERIFICATION PASSED")