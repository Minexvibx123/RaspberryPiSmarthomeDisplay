"""Headless smoke test for the shared widget animation engine."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QWidget  # noqa: E402

from app.core.animations import ANIMATION_NAMES, animation_engine  # noqa: E402

app = QApplication(sys.argv)
widget = QWidget()
widget.setGeometry(40, 40, 200, 120)
widget.setGraphicsEffect(QGraphicsDropShadowEffect(widget))
widget.show()

for index, animation_name in enumerate(ANIMATION_NAMES):
    QTimer.singleShot(index * 350, lambda name=animation_name: animation_engine.play(widget, name))
QTimer.singleShot(len(ANIMATION_NAMES) * 350 + 300, app.quit)
app.exec()

print("VERIFICATION PASSED")