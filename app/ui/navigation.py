"""Bottom / side navigation bar for switching between pages.

Purely data-driven: it reflects whatever pages exist in the database. Adding
a page in the editor immediately adds a nav entry - no code change needed.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from app.widgets.icons import icon_qicon

PAGE_ICON_FALLBACK = "home"


class NavigationBar(QWidget):
    page_selected = Signal(int)
    add_page_requested = Signal()
    page_delete_requested = Signal(int)

    def __init__(self, style: str = "bottom", parent=None):
        super().__init__(parent)
        self.style_mode = style  # "bottom" | "sidebar"
        self.setObjectName("navBar")
        self._buttons: dict[int, QPushButton] = {}
        self._active_id: int | None = None
        self._edit_mode = False

        if style == "sidebar":
            self.layout = QVBoxLayout(self)
            self.setFixedWidth(96)
        else:
            self.layout = QHBoxLayout(self)
            self.setFixedHeight(76)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(6)

    def set_edit_mode(self, enabled: bool) -> None:
        self._edit_mode = enabled
        self._render_add_button()

    def set_pages(self, pages: list, active_id: int) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._buttons.clear()
        self._active_id = active_id
        for page in pages:
            btn = QPushButton(f"  {page.name}")
            btn.setIcon(icon_qicon(page.icon or PAGE_ICON_FALLBACK, 32, "#FFFFFF"))
            btn.setIconSize(QSize(22, 22))
            btn.setObjectName("navButtonActive" if page.id == active_id else "navButton")
            btn.setFlat(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, pid=page.id: self.page_selected.emit(pid))
            self.layout.addWidget(btn, 1)
            self._buttons[page.id] = btn
            if self._edit_mode:
                del_btn = QPushButton("✕")
                del_btn.setObjectName("navDeleteButton")
                del_btn.setFlat(True)
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setToolTip(f"Seite '{page.name}' löschen")
                del_btn.setStyleSheet(
                    "QPushButton#navDeleteButton {"
                    " color: #FF7B72; background-color: rgba(255,123,114,35);"
                    " border: 1px solid rgba(255,123,114,90); border-radius: 13px;"
                    " font-size: 13px; padding: 0; }"
                )
                if self.style_mode == "sidebar":
                    del_btn.setFixedHeight(26)
                else:
                    del_btn.setFixedSize(26, 26)
                del_btn.clicked.connect(
                    lambda checked=False, pid=page.id: self.page_delete_requested.emit(pid)
                )
                self.layout.addWidget(del_btn)
        self._render_add_button()

    def _render_add_button(self) -> None:
        existing = getattr(self, "_add_btn", None)
        if existing:
            self.layout.removeWidget(existing)
            existing.deleteLater()
            self._add_btn = None
        if self._edit_mode:
            self._add_btn = QPushButton("+")
            self._add_btn.setObjectName("navButton")
            self._add_btn.clicked.connect(self.add_page_requested.emit)
            self.layout.addWidget(self._add_btn)
