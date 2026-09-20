"""Headless verification for the extended screensaver (mode + background image)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.core.database import Database  # noqa: E402
from app.core.settings import AppSettings  # noqa: E402
from app.ui.main_window import _StandbyOverlay  # noqa: E402

app = QApplication(sys.argv)

root = Path(tempfile.mkdtemp(prefix="homepanel_screensaver_"))
db = Database(root / "homepanel.db")
settings = AppSettings(db)

overlay = _StandbyOverlay(settings=settings)
overlay.resize(200, 120)

settings.screensaver_mode = "digital_clock"
overlay.set_darkness(60)
assert overlay._info_label.isHidden(), "digital clock mode must not show system info"

settings.screensaver_mode = "system_info"
overlay.set_darkness(60)
assert not overlay._info_label.isHidden(), "system info mode must show the info label"
assert overlay._info_label.text(), "system info label must contain text"

image_path = root / "background.png"
QImage(64, 64, QImage.Format.Format_RGB32).save(str(image_path))
settings.screensaver_background_path = str(image_path)
overlay.set_fully_black()
assert not overlay._background_label.isHidden(), "background image must be shown when configured"

settings.screensaver_background_path = ""
overlay.set_fully_black()
assert overlay._background_label.isHidden(), "background image must hide when cleared"

print("VERIFICATION PASSED")
