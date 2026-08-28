"""The visual editor: canvas in edit mode + toolbar + properties panel.

Undo/redo works on whole-page snapshots (list of widget rows) which keeps
the implementation simple and robust - every mutation (move, resize, add,
delete, property change) pushes a snapshot before it happens.
"""
from __future__ import annotations

import copy
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton,
    QSplitter, QVBoxLayout, QWidget,
)

from app.ui.dashboard import DashboardCanvas
from app.ui.element_library import EntityPickerDialog, WidgetLibraryDialog
from app.ui.navigation import NavigationBar
from app.ui.properties import PropertiesPanel

MAX_UNDO_DEPTH = 30


class EditorScreen(QWidget):
    exit_requested = Signal(bool)  # True = save (keep changes), False = cancel (revert)

    def __init__(self, db, state_manager, design_size, parent=None):
        super().__init__(parent)
        self.db = db
        self.state_manager = state_manager
        self.current_page_id: Optional[int] = None
        self._undo_stack: list[list[dict]] = []
        self._redo_stack: list[list[dict]] = []
        self._entry_snapshot: Optional[list[dict]] = None
        self._clipboard: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 8, 10, 8)
        title = QLabel("Editor-Modus")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        self.grid_btn = QPushButton("Raster: Aus")
        self.grid_btn.clicked.connect(self._toggle_grid)
        self.grid_size_combo = QComboBox()
        self.grid_size_combo.addItems(["10 px", "20 px", "40 px", "80 px"])
        self.grid_size_combo.setCurrentText("20 px")
        self.grid_size_combo.currentTextChanged.connect(self._change_grid_size)
        self.undo_btn = QPushButton("\u21B6 Rückgängig")
        self.undo_btn.clicked.connect(self.undo)
        self.redo_btn = QPushButton("\u21B7 Wiederholen")
        self.redo_btn.clicked.connect(self.redo)
        self.add_btn = QPushButton("+ Element")
        self.add_btn.clicked.connect(self._add_element)
        self.add_page_btn = QPushButton("+ Seite")
        self.add_page_btn.clicked.connect(self._add_page)
        self.copy_btn = QPushButton("Kopieren")
        self.copy_btn.clicked.connect(self._copy_selected)
        self.paste_btn = QPushButton("Einfügen")
        self.paste_btn.clicked.connect(self._paste)
        self.cancel_btn = QPushButton("Abbrechen")
        self.cancel_btn.clicked.connect(self._cancel)
        self.save_btn = QPushButton("Speichern")
        self.save_btn.setStyleSheet("background-color: #33D9B2; color: #08281F; font-weight: 700;")
        self.save_btn.clicked.connect(self._save)
        for b in (self.grid_btn, self.grid_size_combo, self.undo_btn, self.redo_btn, self.add_btn, self.add_page_btn, self.copy_btn, self.paste_btn, self.cancel_btn, self.save_btn):
            toolbar.addWidget(b)
        root.addLayout(toolbar)

        self.nav_bar = NavigationBar(style="bottom")
        self.nav_bar.set_edit_mode(True)
        self.nav_bar.page_selected.connect(self.load_page)
        self.nav_bar.add_page_requested.connect(self._add_page)
        self.nav_bar.page_delete_requested.connect(self._delete_page)

        splitter = QSplitter()
        self.canvas = DashboardCanvas(state_manager, db, design_size)
        self.canvas.set_edit_mode(True)
        self.canvas.widget_selected.connect(self._on_widget_selected)
        self.canvas.multi_selected.connect(self._on_multi_selected)
        self.canvas.widget_moved.connect(lambda *_: None)
        self.canvas.widget_resized.connect(lambda *_: None)

        canvas_wrap = QVBoxLayout()
        canvas_container = QWidget()
        canvas_container.setLayout(canvas_wrap)
        canvas_wrap.setContentsMargins(0, 0, 0, 0)
        canvas_wrap.addWidget(self.canvas, 1)
        canvas_wrap.addWidget(self.nav_bar)

        self.properties_panel = PropertiesPanel(state_manager)
        self.properties_panel.setMinimumWidth(280)
        self.properties_panel.setMaximumWidth(340)
        self.properties_panel.delete_requested.connect(self._delete_selected)
        self.properties_panel.duplicate_requested.connect(self._duplicate_selected)
        self.properties_panel.size_changed.connect(self._on_size_changed)

        splitter.addWidget(canvas_container)
        splitter.addWidget(self.properties_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        QShortcut(QKeySequence("Ctrl+C"), self, self._copy_selected)
        QShortcut(QKeySequence("Ctrl+V"), self, self._paste)
        QShortcut(QKeySequence("Delete"), self, self._delete_selected)
        QShortcut(QKeySequence("Backspace"), self, self._delete_selected)

    # ------------------------------------------------------------------ #
    def enter(self, page_id: int) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._entry_snapshot = self._export_all_pages()
        self.load_page(page_id)

    def load_page(self, page_id: int) -> None:
        self.current_page_id = page_id
        self.canvas.load_page(page_id)
        self.nav_bar.set_pages(self.db.list_pages(), page_id)
        self.properties_panel.set_widget(None, self.db)

    def _on_widget_selected(self, widget_id: int) -> None:
        if widget_id == -1:
            self.properties_panel.set_widget(None, self.db)
            return
        inst = self.canvas.widget_instances.get(widget_id)
        self.properties_panel.set_widget(inst, self.db)

    def _on_multi_selected(self, count: int) -> None:
        self.properties_panel.set_multi_selected(count, self.db)

    def _on_size_changed(self) -> None:
        self.canvas.reposition_all()

    # -- toolbar actions --------------------------------------------------- #
    def _toggle_grid(self) -> None:
        enabled = not self.canvas.grid_enabled
        self.canvas.set_grid_enabled(enabled)
        self.grid_btn.setText(f"Raster: {'An' if enabled else 'Aus'}")

    def _change_grid_size(self, text: str) -> None:
        size = int(text.replace(" px", ""))
        self.canvas.set_grid_size(size)

    def _add_element(self) -> None:
        dlg = WidgetLibraryDialog(self)
        if not dlg.exec() or not dlg.selected_type:
            return
        wtype = dlg.selected_type
        from app.widgets.registry import widget_class

        cls = widget_class(wtype)
        entity_id = ""
        if cls.requires_entity:
            picker = EntityPickerDialog(self.state_manager, domain_filter=cls.entity_domains, parent=self)
            if not picker.exec() or not picker.selected_entity_id:
                return
            entity_id = picker.selected_entity_id
        self._push_undo()
        self.canvas.add_widget(wtype, entity_id)

    def _add_page(self) -> None:
        name, ok = QInputDialog.getText(self, "Neue Seite", "Name der Seite:")
        if ok and name.strip():
            page = self.db.create_page(name.strip())
            self.load_page(page.id)

    def _delete_page(self, page_id: int) -> None:
        pages = self.db.list_pages()
        if len(pages) <= 1:
            QMessageBox.information(
                self, "Letzte Seite", "Die letzte Seite kann nicht gelöscht werden."
            )
            return
        page = next((p for p in pages if p.id == page_id), None)
        if page is None:
            return
        confirm = QMessageBox.question(
            self,
            "Seite löschen",
            f"Seite '{page.name}' wirklich löschen?\nAlle Elemente dieser Seite werden entfernt.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        ids_in_order = [p.id for p in pages]
        idx = ids_in_order.index(page_id)
        # Ziel-Seite: aktuelle behalten falls nicht gelöscht, sonst Nachbar wählen
        if self.current_page_id != page_id:
            target = self.current_page_id
        elif idx > 0:
            target = ids_in_order[idx - 1]
        elif len(ids_in_order) > 1:
            target = ids_in_order[idx + 1]
        else:
            target = None
        keep_ids = [pid for pid in ids_in_order if pid != page_id]
        self.db.delete_page(page_id)
        self.db.reorder_pages(keep_ids)
        if target is None and keep_ids:
            target = keep_ids[0]
        if target is not None:
            self.load_page(target)

    def _delete_selected(self) -> None:
        multi_ids = self.canvas.get_multi_selected_ids()
        if not multi_ids:
            return
        self._push_undo()
        for wid in multi_ids:
            self.canvas.remove_widget(wid)
        self.properties_panel.set_widget(None, self.db)

    def _duplicate_selected(self) -> None:
        if self.canvas.selected_widget_id is None:
            return
        self._push_undo()
        self.canvas.duplicate_widget(self.canvas.selected_widget_id)

    def _copy_selected(self) -> None:
        multi_ids = self.canvas.get_multi_selected_ids()
        if not multi_ids:
            return
        self._clipboard = []
        for wid in multi_ids:
            w = self.db.get_widget(wid)
            if w:
                self._clipboard.append(copy.deepcopy(w.__dict__))

    def _paste(self) -> None:
        if not self._clipboard or self.current_page_id is None:
            return
        self._push_undo()
        for wc in self._clipboard:
            self.db.create_widget(
                self.current_page_id, wc["type"],
                wc["x"] + 30, wc["y"] + 30,
                wc["w"], wc["h"], dict(wc.get("config", {})),
            )
        if self.current_page_id is not None:
            self.canvas.load_page(self.current_page_id)

    # -- undo / redo (whole-page snapshots) -------------------------------- #
    def _page_snapshot(self) -> list[dict]:
        return [copy.deepcopy(w.__dict__) for w in self.db.list_widgets(self.current_page_id)]

    def _push_undo(self) -> None:
        self._undo_stack.append(self._page_snapshot())
        if len(self._undo_stack) > MAX_UNDO_DEPTH:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _restore_snapshot(self, snapshot: list[dict]) -> None:
        if self.current_page_id is None:
            return
        for w in self.db.list_widgets(self.current_page_id):
            self.db.delete_widget(w.id)
        for w in snapshot:
            self.db.create_widget(self.current_page_id, w["type"], w["x"], w["y"], w["w"], w["h"], w["config"], z=w["z"])
        self.canvas.load_page(self.current_page_id)
        self.properties_panel.set_widget(None, self.db)

    def undo(self) -> None:
        if not self._undo_stack:
            return
        self._redo_stack.append(self._page_snapshot())
        snapshot = self._undo_stack.pop()
        self._restore_snapshot(snapshot)

    def redo(self) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append(self._page_snapshot())
        snapshot = self._redo_stack.pop()
        self._restore_snapshot(snapshot)

    # -- save / cancel ------------------------------------------------------ #
    def _export_all_pages(self) -> list[dict]:
        data = []
        for page in self.db.list_pages():
            data.append({
                "page_id": page.id,
                "widgets": [copy.deepcopy(w.__dict__) for w in self.db.list_widgets(page.id)],
            })
        return data

    def _save(self) -> None:
        self.exit_requested.emit(True)

    def _cancel(self) -> None:
        if self._entry_snapshot is not None:
            confirm = QMessageBox.question(
                self, "Änderungen verwerfen?",
                "Alle Änderungen seit dem Öffnen des Editors werden verworfen. Fortfahren?",
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            known_page_ids = {p["page_id"] for p in self._entry_snapshot}
            for page in self.db.list_pages():
                if page.id not in known_page_ids:
                    self.db.delete_page(page.id)  # discard pages created during this editor session
            for page_data in self._entry_snapshot:
                for w in self.db.list_widgets(page_data["page_id"]):
                    self.db.delete_widget(w.id)
                for w in page_data["widgets"]:
                    self.db.create_widget(page_data["page_id"], w["type"], w["x"], w["y"], w["w"], w["h"], w["config"], z=w["z"])
        self.exit_requested.emit(False)
