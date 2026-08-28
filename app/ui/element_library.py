"""Visual widget library and Home-Assistant entity picker.

Both are modal dialogs used exclusively from the editor. The entity picker
is the piece that removes the need to ever type an entity_id by hand: it
groups entities by area/room and offers a search box.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QDialog, QGridLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.widgets.icons import icon_qicon
from app.widgets.registry import widgets_by_category


class WidgetLibraryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Element hinzufügen")
        self.setMinimumSize(560, 480)
        self.selected_type: Optional[str] = None

        layout = QVBoxLayout(self)
        title = QLabel("Was möchtest du hinzufügen?")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        v = QVBoxLayout(container)

        for category, classes in widgets_by_category().items():
            cat_label = QLabel(category)
            cat_label.setStyleSheet("font-size: 14px; color: #9AA1B4; margin-top: 10px;")
            v.addWidget(cat_label)
            grid = QGridLayout()
            for i, cls in enumerate(classes):
                btn = QPushButton(f"  {cls.display_name}")
                btn.setIcon(icon_qicon(cls.icon, 40, "#FFFFFF"))
                btn.setIconSize(QSize(32, 32))
                btn.setMinimumSize(140, 90)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked=False, t=cls.type_name: self._choose(t))
                grid.addWidget(btn, i // 3, i % 3)
            v.addLayout(grid)
        v.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def _choose(self, type_name: str) -> None:
        self.selected_type = type_name
        self.accept()


class EntityPickerDialog(QDialog):
    """Rooms -> entities -> search. Returns the chosen entity_id."""

    def __init__(self, state_manager, domain_filter: Optional[list[str]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Entity auswählen")
        self.setMinimumSize(480, 560)
        self.state_manager = state_manager
        self.domain_filter = domain_filter
        self.selected_entity_id: Optional[str] = None

        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Suchen...")
        self.search.textChanged.connect(self._rebuild)
        layout.addWidget(self.search)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._pick)
        layout.addWidget(self.list_widget, 1)

        choose_btn = QPushButton("Auswählen")
        choose_btn.clicked.connect(self._confirm)
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(choose_btn)
        layout.addWidget(cancel_btn)

        self._rebuild()

    def _grouped_entities(self) -> dict[str, list]:
        grouped: dict[str, list] = {}
        query = self.search.text().lower()
        entities = self.state_manager.entities.values() if self.state_manager else []
        for e in entities:
            if self.domain_filter and e.domain not in self.domain_filter:
                continue
            if query and query not in e.friendly_name.lower() and query not in e.entity_id.lower():
                continue
            area = e.area or "Sonstige"
            grouped.setdefault(area, []).append(e)
        return grouped

    def _rebuild(self) -> None:
        self.list_widget.clear()
        for area, entities in sorted(self._grouped_entities().items()):
            header = QListWidgetItem(f"\u2500\u2500 {area} \u2500\u2500")
            header.setFlags(Qt.NoItemFlags)
            self.list_widget.addItem(header)
            for e in sorted(entities, key=lambda x: x.friendly_name):
                item = QListWidgetItem(f"   {e.friendly_name}  ·  {e.state}")
                item.setData(Qt.UserRole, e.entity_id)
                self.list_widget.addItem(item)

    def _pick(self, item: QListWidgetItem) -> None:
        entity_id = item.data(Qt.UserRole)
        if entity_id:
            self.selected_entity_id = entity_id
            self.accept()

    def _confirm(self) -> None:
        item = self.list_widget.currentItem()
        if item and item.data(Qt.UserRole):
            self.selected_entity_id = item.data(Qt.UserRole)
            self.accept()
