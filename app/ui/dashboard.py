"""Free-form canvas that renders a page's widgets, and the dashboard shell
(connection badge + navigation + canvas) around it.

The same canvas is reused by the editor (it just flips `edit_mode` on and
adds selection/drag/resize handling) so normal-mode and editor-mode always
look pixel-identical.
"""
from __future__ import annotations

import os
import time
from typing import Optional

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.widgets.base import BaseWidget
from app.widgets.registry import widget_class

HANDLE_SIZE = 44


class ResizeHandle(QWidget):
    resize_delta = Signal(int, int)
    resize_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(HANDLE_SIZE, HANDLE_SIZE)
        self.setCursor(Qt.SizeFDiagCursor)
        self.setStyleSheet(
            f"background-color: #4C8DFF; border-radius: {HANDLE_SIZE // 2}px; border: 3px solid white;"
        )
        self._drag_origin: Optional[QPoint] = None

    def mousePressEvent(self, event) -> None:
        self._drag_origin = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_origin is None:
            return
        pos = event.globalPosition().toPoint()
        delta = pos - self._drag_origin
        self._drag_origin = pos
        self.resize_delta.emit(delta.x(), delta.y())

    def mouseReleaseEvent(self, event) -> None:
        self._drag_origin = None
        self.resize_finished.emit()


class DashboardCanvas(QWidget):
    """Renders widgets for the current page at scaled design coordinates."""

    widget_selected = Signal(int)
    multi_selected = Signal(int)  # count of selected widgets
    widget_moved = Signal(int, float, float)      # widget_id, new_x, new_y (design coords)
    widget_resized = Signal(int, float, float)     # widget_id, new_w, new_h (design coords)
    navigate_requested = Signal(str)

    def __init__(self, state_manager, db, design_size: tuple[int, int], parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        self.db = db
        self.design_w, self.design_h = design_size
        self.edit_mode = False
        self.current_page_id: Optional[int] = None
        self.widget_instances: dict[int, BaseWidget] = {}
        self.selected_widget_id: Optional[int] = None
        self._multi_selected_ids: set[int] = set()
        self.resize_handle: Optional[ResizeHandle] = None
        self.grid_enabled = False
        self.grid_size = 20

        self._drag_widget_id: Optional[int] = None
        self._drag_origin: Optional[QPoint] = None
        self._drag_start_geo: Optional[QRect] = None

        self._page_bg_path: str = ""
        self._page_bg_fit: str = "cover"
        self._page_bg_pixmap: Optional[QPixmap] = None

        if self.state_manager:
            self.state_manager.entity_updated.connect(self._on_entity_updated)

    # ------------------------------------------------------------------ #
    def scale(self) -> tuple[float, float]:
        w = max(self.width(), 1)
        h = max(self.height(), 1)
        return w / self.design_w, h / self.design_h

    def load_page(self, page_id: int) -> None:
        self.current_page_id = page_id
        self._load_page_bg(page_id)
        self.clear()
        for w in self.db.list_widgets(page_id):
            self._instantiate(w)
        self.reposition_all()

    def clear(self) -> None:
        for inst in self.widget_instances.values():
            inst.removeEventFilter(self)
            inst.deleteLater()
        self.widget_instances.clear()
        self.selected_widget_id = None
        self._remove_resize_handle()

    def _load_page_bg(self, page_id: int) -> None:
        page = self.db.get_page(page_id)
        self._page_bg_path = page.bg_image_path if page else ""
        self._page_bg_fit = page.bg_fit if page else "cover"
        self._page_bg_pixmap = None
        if self._page_bg_path and os.path.exists(self._page_bg_path):
            pm = QPixmap(self._page_bg_path)
            if not pm.isNull():
                self._page_bg_pixmap = pm

    def _instantiate(self, w) -> BaseWidget:
        cls = widget_class(w.type)
        inst = cls(w.id, w.config, self.state_manager, parent=self)
        inst.installEventFilter(self)
        inst.show()
        if hasattr(inst, "navigate_requested"):
            inst.navigate_requested.connect(self.navigate_requested.emit)
        self.widget_instances[w.id] = inst
        return inst

    def add_widget(self, wtype: str, entity_id: str = "") -> Optional[BaseWidget]:
        if self.current_page_id is None:
            return None
        cls = widget_class(wtype)
        default_w, default_h = cls.default_size
        config = {}
        if entity_id:
            config["entity_id"] = entity_id
        db_widget = self.db.create_widget(
            self.current_page_id, wtype,
            x=(self.design_w - default_w) / 2, y=(self.design_h - default_h) / 2,
            w=default_w, h=default_h, config=config,
        )
        inst = self._instantiate(db_widget)
        self.reposition_all()
        return inst

    def remove_widget(self, widget_id: int) -> None:
        self.db.delete_widget(widget_id)
        inst = self.widget_instances.pop(widget_id, None)
        if inst:
            inst.deleteLater()
        if self.selected_widget_id == widget_id:
            self.select_widget(None)

    def duplicate_widget(self, widget_id: int) -> None:
        w = self.db.duplicate_widget(widget_id)
        if w:
            self._instantiate(w)
            self.reposition_all()
            self.select_widget(w.id)

    def reposition_all(self) -> None:
        sx, sy = self.scale()
        for wid, inst in self.widget_instances.items():
            w = self.db.get_widget(wid)
            if not w:
                continue
            inst.setGeometry(int(w.x * sx), int(w.y * sy), int(w.w * sx), int(w.h * sy))
        self._position_resize_handle()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.reposition_all()

    # ------------------------------------------------------------------ #
    # selection / edit mode
    # ------------------------------------------------------------------ #
    def set_edit_mode(self, enabled: bool) -> None:
        self.edit_mode = enabled
        if not enabled:
            self.select_widget(None)
        self.update()

    def set_grid_enabled(self, enabled: bool) -> None:
        self.grid_enabled = enabled
        self.update()

    def set_grid_size(self, size: int) -> None:
        self.grid_size = max(4, size)
        self.update()

    def _snap(self, value: float) -> float:
        if not self.grid_enabled:
            return value
        return round(value / self.grid_size) * self.grid_size

    def paintEvent(self, event) -> None:
        if self._page_bg_pixmap and not self._page_bg_pixmap.isNull():
            painter = QPainter(self)
            canvas_rect = self.rect()
            pm = self._page_bg_pixmap
            pw, ph = pm.width(), pm.height()
            cw, ch = canvas_rect.width(), canvas_rect.height()

            if self._page_bg_fit == "cover":
                scale = max(cw / max(pw, 1), ch / max(ph, 1))
                sw, sh = int(pw * scale), int(ph * scale)
                sx = (cw - sw) // 2
                sy = (ch - sh) // 2
                painter.drawPixmap(sx, sy, sw, sh, pm)
            elif self._page_bg_fit == "contain":
                scale = min(cw / max(pw, 1), ch / max(ph, 1))
                sw, sh = int(pw * scale), int(ph * scale)
                sx = (cw - sw) // 2
                sy = (ch - sh) // 2
                painter.drawPixmap(sx, sy, sw, sh, pm)
            else:  # stretch
                painter.drawPixmap(0, 0, cw, ch, pm)
            painter.end()

        super().paintEvent(event)
        if not (self.edit_mode and self.grid_enabled):
            return
        painter = QPainter(self)
        painter.setPen(QColor(255, 255, 255, 40))
        sx, sy = self.scale()
        step_x = max(int(self.grid_size * sx), 4)
        step_y = max(int(self.grid_size * sy), 4)
        for x in range(0, self.width(), step_x):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step_y):
            painter.drawLine(0, y, self.width(), y)

    def select_widget(self, widget_id: Optional[int], multi: bool = False) -> None:
        if multi:
            if widget_id is not None:
                if widget_id in self._multi_selected_ids:
                    self._multi_selected_ids.remove(widget_id)
                    if widget_id in self.widget_instances:
                        self.widget_instances[widget_id].set_selected(False)
                else:
                    self._multi_selected_ids.add(widget_id)
                    if widget_id in self.widget_instances:
                        self.widget_instances[widget_id].set_selected(True)
                
                # If we have exactly one item in multi-select, treat it as single select
                if len(self._multi_selected_ids) == 1:
                    single_id = list(self._multi_selected_ids)[0]
                    self._multi_selected_ids.clear()
                    self.select_widget(single_id, multi=False)
                    return
                
                # If we have multiple items, clear single select and emit multi
                if len(self._multi_selected_ids) > 1:
                    if self.selected_widget_id is not None and self.selected_widget_id in self.widget_instances:
                        if self.selected_widget_id not in self._multi_selected_ids:
                            self.widget_instances[self.selected_widget_id].set_selected(False)
                        self._multi_selected_ids.add(self.selected_widget_id)
                        self.selected_widget_id = None
                    self._remove_resize_handle()
                    self.multi_selected.emit(len(self._multi_selected_ids))
                    return
                
                # If empty, clear all
                if len(self._multi_selected_ids) == 0:
                    self.select_widget(None)
                    return
            return

        # Single select logic
        for wid in self._multi_selected_ids:
            if wid in self.widget_instances and wid != widget_id:
                self.widget_instances[wid].set_selected(False)
        self._multi_selected_ids.clear()

        if self.selected_widget_id is not None and self.selected_widget_id in self.widget_instances:
            self.widget_instances[self.selected_widget_id].set_selected(False)
        self.selected_widget_id = widget_id
        self._remove_resize_handle()
        if widget_id is not None and widget_id in self.widget_instances:
            self.widget_instances[widget_id].set_selected(True)
            if self.edit_mode:
                self._create_resize_handle(widget_id)
            self.widget_selected.emit(widget_id)
        else:
            self.widget_selected.emit(-1) # Signal clear

    def get_multi_selected_ids(self) -> set[int]:
        if self.selected_widget_id is not None:
            return {self.selected_widget_id}
        return self._multi_selected_ids.copy()

    def _create_resize_handle(self, widget_id: int) -> None:
        self.resize_handle = ResizeHandle(self)
        self.resize_handle.resize_delta.connect(lambda dx, dy: self._on_resize_delta(widget_id, dx, dy))
        self.resize_handle.resize_finished.connect(lambda: self._finish_resize(widget_id))
        self.resize_handle.show()
        self.resize_handle.raise_()
        self._position_resize_handle()

    def _remove_resize_handle(self) -> None:
        if self.resize_handle:
            self.resize_handle.deleteLater()
            self.resize_handle = None

    def _position_resize_handle(self) -> None:
        if not self.resize_handle or self.selected_widget_id is None:
            return
        inst = self.widget_instances.get(self.selected_widget_id)
        if not inst:
            return
        geo = inst.geometry()
        self.resize_handle.move(geo.right() - HANDLE_SIZE // 2, geo.bottom() - HANDLE_SIZE // 2)

    def _on_resize_delta(self, widget_id: int, dx: int, dy: int) -> None:
        w = self.db.get_widget(widget_id)
        inst = self.widget_instances.get(widget_id)
        if not w or not inst:
            return
        sx, sy = self.scale()
        new_w = max(60, w.w + dx / sx)
        new_h = max(50, w.h + dy / sy)
        self.db.update_widget(widget_id, w=new_w, h=new_h)
        inst.setGeometry(inst.x(), inst.y(), int(new_w * sx), int(new_h * sy))
        self._position_resize_handle()

    def _finish_resize(self, widget_id: int) -> None:
        w = self.db.get_widget(widget_id)
        inst = self.widget_instances.get(widget_id)
        if not w or not inst:
            return
        new_w, new_h = self._snap(w.w), self._snap(w.h)
        new_w, new_h = max(60, new_w), max(50, new_h)
        self.db.update_widget(widget_id, w=new_w, h=new_h)
        sx, sy = self.scale()
        inst.setGeometry(inst.x(), inst.y(), int(new_w * sx), int(new_h * sy))
        self._position_resize_handle()
        self.widget_resized.emit(widget_id, new_w, new_h)

    # ------------------------------------------------------------------ #
    # drag-to-move via event filter on child widgets (edit mode only)
    # ------------------------------------------------------------------ #
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if not self.edit_mode:
            return False
        widget_id = None
        for wid, inst in self.widget_instances.items():
            if inst is obj:
                widget_id = wid
                break
        if widget_id is None:
            return False

        if event.type() == QEvent.Type.MouseButtonPress:
            import PySide6.QtGui
            import PySide6.QtWidgets
            if isinstance(event, PySide6.QtGui.QMouseEvent):
                modifiers = event.modifiers()
                is_shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
            else:
                is_shift = False
            self.select_widget(widget_id, multi=is_shift)
            self._drag_widget_id = widget_id
            if isinstance(event, PySide6.QtGui.QMouseEvent):
                self._drag_origin = event.globalPosition().toPoint()
            if isinstance(obj, PySide6.QtWidgets.QWidget):
                self._drag_start_geo = obj.geometry()
            return True
        elif event.type() == QEvent.Type.MouseMove and self._drag_widget_id == widget_id and self._drag_origin:
            import PySide6.QtGui
            import PySide6.QtWidgets
            if isinstance(event, PySide6.QtGui.QMouseEvent) and self._drag_start_geo is not None:
                delta = event.globalPosition().toPoint() - self._drag_origin
                new_geo = QRect(self._drag_start_geo)
                new_geo.translate(delta.x(), delta.y())
                if isinstance(obj, PySide6.QtWidgets.QWidget):
                    obj.setGeometry(new_geo)
                self._position_resize_handle()
            return True
        elif event.type() == QEvent.Type.MouseButtonRelease and self._drag_widget_id == widget_id:
            import PySide6.QtGui
            import PySide6.QtWidgets
            if isinstance(event, PySide6.QtGui.QMouseEvent) and isinstance(obj, PySide6.QtWidgets.QWidget):
                sx, sy = self.scale()
                geo = obj.geometry()
                new_x, new_y = self._snap(geo.x() / sx), self._snap(geo.y() / sy)
                self.db.update_widget(widget_id, x=new_x, y=new_y)
                obj.setGeometry(int(new_x * sx), int(new_y * sy), geo.width(), geo.height())
                self._position_resize_handle()
                self.widget_moved.emit(widget_id, new_x, new_y)
                self._drag_widget_id = None
                self._drag_origin = None
            return True
        return False

    def _on_entity_updated(self, entity_id: str, new_state: dict) -> None:
        for inst in self.widget_instances.values():
            inst.on_state_changed(entity_id, new_state)


class ConnectionBadge(QLabel):
    def __init__(self, state_manager, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        state_manager.connection_status_changed.connect(self._update)
        self._update(state_manager.connected)

    def _update(self, connected: bool) -> None:
        if connected:
            self.setObjectName("connectionBadgeOk")
            self.setText("\u25CF Home Assistant verbunden")
        else:
            since = self.state_manager.seconds_since_last_connection()
            suffix = f" (zuletzt vor {int(since)}s)" if since else ""
            self.setObjectName("connectionBadgeBad")
            self.setText(f"\u26A0 Verbindung verloren{suffix}")
        self.style().unpolish(self)
        self.style().polish(self)
