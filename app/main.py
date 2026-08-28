"""HomePanel entry point.

Usage:
    python -m app.main [--windowed] [--demo]
"""
from __future__ import annotations

import argparse
import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HomePanel - Home Assistant Touchpanel")
    parser.add_argument("--windowed", action="store_true", help="Run in a normal window instead of fullscreen kiosk mode")
    parser.add_argument("--demo", action="store_true", help="Force demo mode (no Home Assistant required)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setApplicationName("HomePanel")

    window = MainWindow(app)

    if args.demo and hasattr(window, "settings"):
        window.settings.demo_mode = True

    if args.windowed:
        window.resize(1024, 600)
        window.show()
    else:
        window.showFullScreen()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
