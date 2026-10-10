"""Touch-first launcher showing the installed apps grouped by category."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.apps.catalog import CATEGORIES
from app.widgets.icons import IconGlyph

COLUMNS = 3


def _tile(entry, callback) -> QPushButton:
    tile = QPushButton()
    tile.setObjectName("appTile")
    tile.setCursor(Qt.CursorShape.PointingHandCursor)
    layout = QHBoxLayout(tile)
    layout.setContentsMargins(14, 10, 14, 10)
    glyph = IconGlyph(entry.icon, "#FFFFFF")
    glyph.setFixedSize(44, 44)
    text = QLabel(f"<b style='font-size:17px'>{entry.name}</b><br>{entry.description}")
    text.setWordWrap(True)
    for child in (glyph, text):
        child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    layout.addWidget(glyph)
    layout.addWidget(text, 1)
    tile.clicked.connect(lambda _checked=False, app_id=entry.id: callback(app_id))
    return tile


class AppLauncher(QWidget):
    exit_requested = Signal()
    store_requested = Signal()

    def __init__(self, catalog, open_app, parent=None):
        super().__init__(parent)
        self.catalog, self.open_app = catalog, open_app
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        back = QPushButton("\u2190 Zurück zum Panel")
        back.clicked.connect(self.exit_requested.emit)
        title = QLabel("Apps")
        title.setStyleSheet("font-size: 26px; font-weight: 800;")
        store = QPushButton("App-Store")
        store.setProperty("variant", "primary")
        store.clicked.connect(self.store_requested.emit)
        top.addWidget(back)
        top.addWidget(title, 1, Qt.AlignmentFlag.AlignCenter)
        top.addWidget(store)
        root.addLayout(top)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        root.addWidget(self.scroll, 1)
        catalog.changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        entries = self.catalog.installed()
        if not entries:
            layout.addWidget(QLabel("Keine Apps installiert. Im App-Store findest du über 30 Apps."))
        for category in CATEGORIES:
            members = [entry for entry in entries if entry.category == category]
            if not members:
                continue
            heading = QLabel(category)
            heading.setStyleSheet("font-size: 15px; font-weight: 800; margin-top: 8px;")
            layout.addWidget(heading)
            grid = QGridLayout()
            grid.setSpacing(10)
            for index, entry in enumerate(members):
                grid.addWidget(_tile(entry, self.open_app), index // COLUMNS, index % COLUMNS)
            layout.addLayout(grid)
        layout.addStretch(1)
        self.scroll.setWidget(container)
