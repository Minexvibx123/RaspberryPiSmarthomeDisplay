"""Verify that the optional web widget imports and registers without WebEngine."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.widgets.registry import widget_class  # noqa: E402

web_widget = widget_class("web")
assert web_widget.type_name == "web"
assert web_widget.display_name == "Web Panel"
print("VERIFICATION PASSED")