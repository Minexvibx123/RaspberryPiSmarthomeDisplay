"""Touch-optimized internal browser view, optional QtWebEngine dependency."""
from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)


def parse_bookmarks(raw: str) -> list[tuple[str, str]]:
    bookmarks = []
    for entry in raw.split(";"):
        entry = entry.strip()
        if "|" in entry:
            name, url = entry.split("|", 1)
            if name.strip() and url.strip():
                bookmarks.append((name.strip(), url.strip()))
    return bookmarks


class BrowserView(QWidget):
    def __init__(self, home_url: str, bookmarks_raw: str, parent=None):
        super().__init__(parent)
        self.home_url = home_url
        self.web_view = None

        layout = QVBoxLayout(self)
        nav = QHBoxLayout()
        self.back_btn = QPushButton("\u2190")
        self.forward_btn = QPushButton("\u2192")
        self.reload_btn = QPushButton("\u27f3")
        self.home_btn = QPushButton("\u2302")
        self.url_edit = QLineEdit()
        self.url_edit.returnPressed.connect(self._navigate_to_typed_url)
        self.bookmarks_combo = QComboBox()
        self.bookmarks_combo.addItem("\u2b50 Bookmarks")
        for name, url in parse_bookmarks(bookmarks_raw):
            self.bookmarks_combo.addItem(name, url)
        self.bookmarks_combo.activated.connect(self._open_bookmark)
        self.fullscreen_btn = QPushButton("\u26f6")
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        for widget in (
            self.back_btn, self.forward_btn, self.reload_btn, self.home_btn,
            self.url_edit, self.bookmarks_combo, self.fullscreen_btn,
        ):
            nav.addWidget(widget)
        nav.setStretch(4, 1)
        layout.addLayout(nav)

        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            message = QLabel("Browser-Funktion ist nicht verfügbar (QtWebEngine fehlt).")
            message.setWordWrap(True)
            layout.addWidget(message, 1)
            for widget in (self.back_btn, self.forward_btn, self.reload_btn, self.home_btn, self.url_edit, self.fullscreen_btn):
                widget.setEnabled(False)
            return

        self.web_view = QWebEngineView(self)
        self.back_btn.clicked.connect(self.web_view.back)
        self.forward_btn.clicked.connect(self.web_view.forward)
        self.reload_btn.clicked.connect(self.web_view.reload)
        self.home_btn.clicked.connect(self._go_home)
        self.web_view.urlChanged.connect(lambda url: self.url_edit.setText(url.toString()))
        layout.addWidget(self.web_view, 1)
        self._go_home()

    def _go_home(self) -> None:
        if self.web_view is not None:
            self.web_view.setUrl(QUrl.fromUserInput(self.home_url))

    def _navigate_to_typed_url(self) -> None:
        if self.web_view is not None:
            self.web_view.setUrl(QUrl.fromUserInput(self.url_edit.text().strip()))

    def _open_bookmark(self, index: int) -> None:
        url = self.bookmarks_combo.itemData(index)
        if url and self.web_view is not None:
            self.web_view.setUrl(QUrl.fromUserInput(url))

    def _toggle_fullscreen(self) -> None:
        window = self.window()
        if window.isFullScreen():
            window.showNormal()
        else:
            window.showFullScreen()
