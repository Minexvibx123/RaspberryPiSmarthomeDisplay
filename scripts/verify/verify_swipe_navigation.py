"""Offscreen verification for dashboard swipe page navigation."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PySide6.QtCore import QPoint, Qt, QObject, Signal  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.core.database import Database  # noqa: E402
from app.ui.dashboard import DashboardCanvas
from app.ui.main_window import DashboardView  # noqa: E402


class _StateManager(QObject):
    entity_updated = Signal(str, dict)
    connection_status_changed = Signal(bool)

    connected = False

    @staticmethod
    def seconds_since_last_connection():
        return None


class _Settings:
    navigation_style = "bottom"


app = QApplication(sys.argv)
root = Path(tempfile.mkdtemp(prefix="homepanel_swipe_"))
try:
    db = Database(root / "homepanel.db")
    pages = db.list_pages()
    first = pages[0]
    touch_widget = db.create_widget(
        first.id, "text", 20, 20, 260, 180, config={"text": "Touch-Ziel"},
    )
    second = db.create_page("Zweite Seite")
    third = db.create_page("Dritte Seite")
    view = DashboardView(
        db, _StateManager(), _Settings(), lambda: None, lambda: None,
        lambda: None, lambda _name: None, (800, 480),
    )
    view.resize(800, 480)
    view.show()
    view.load_page(first.id)
    view.canvas.resize(800, 400)
    app.processEvents()

    QTest.mousePress(view.canvas, Qt.MouseButton.LeftButton, pos=QPoint(300, 200))
    QTest.mouseMove(view.canvas, QPoint(220, 204))
    app.processEvents()
    assert view.canvas.current_page_id == second.id
    assert view.canvas._transition_overlay is not None
    assert view.canvas._transition_overlay.x() < 0, (
        f"child touch did not move overlay: x={view.canvas._transition_overlay.x()}, "
        f"origin={view.canvas._mouse_swipe_origin}, target_geometry={touch_target.geometry()}"
    )
    assert view.nav_bar._active_id == second.id
    QTest.mouseMove(view.canvas, QPoint(100, 204))
    app.processEvents()
    assert view.canvas._transition_overlay.x() == -200
    QTest.mouseRelease(view.canvas, Qt.MouseButton.LeftButton, pos=QPoint(100, 204))
    app.processEvents()
    assert view.canvas._transition_animation is not None
    assert view.canvas._transition_animation.endValue() == QPoint(-view.canvas.width(), 0)

    QTest.mousePress(view.canvas, Qt.MouseButton.LeftButton, pos=QPoint(170, 200))
    QTest.mouseMove(view.canvas, QPoint(400, 204))
    app.processEvents()
    assert view.canvas._transition_overlay is not None
    assert view.canvas._transition_overlay.x() > 0
    QTest.mouseRelease(view.canvas, Qt.MouseButton.LeftButton, pos=QPoint(400, 204))
    app.processEvents()
    assert view.canvas.current_page_id == first.id
    assert view.canvas._transition_animation is not None
    assert view.canvas._transition_animation.endValue() == QPoint(view.canvas.width(), 0)

    QTest.mousePress(view.canvas, Qt.MouseButton.LeftButton, pos=QPoint(170, 200))
    QTest.mouseRelease(view.canvas, Qt.MouseButton.LeftButton, pos=QPoint(300, 204))
    app.processEvents()
    assert view.canvas.current_page_id == first.id

    view.canvas.set_edit_mode(False)
    touch_device = QTest.createTouchDevice()
    QTest.touchEvent(view.canvas, touch_device).press(
        0, QPoint(300, 200), view.canvas,
    ).commit()
    QTest.touchEvent(view.canvas, touch_device).move(
        0, QPoint(220, 204), view.canvas,
    ).commit()
    app.processEvents()
    assert view.canvas.current_page_id == second.id
    assert view.canvas._transition_overlay is not None
    assert view.canvas._transition_overlay.x() < 0
    QTest.touchEvent(view.canvas, touch_device).move(
        0, QPoint(100, 204), view.canvas,
    ).commit()
    app.processEvents()
    assert view.canvas._transition_overlay.x() == -200
    QTest.touchEvent(view.canvas, touch_device).release(
        0, QPoint(100, 204), view.canvas,
    ).commit()
    app.processEvents()
    assert view.canvas.current_page_id == second.id

    view.load_page(first.id)
    touch_target = view.canvas.widget_instances[touch_widget.id]
    QTest.touchEvent(touch_target, touch_device).press(
        0, QPoint(120, 80), touch_target,
    ).commit()
    QTest.touchEvent(touch_target, touch_device).move(
        0, QPoint(80, 82), touch_target,
    ).commit()
    app.processEvents()
    assert view.canvas.current_page_id == second.id
    assert touch_target in view.canvas._swipe_original_widgets.values()
    target_global = touch_target.mapFromGlobal(
        view.canvas.mapToGlobal(QPoint(20, 82)),
    )
    QTest.touchEvent(touch_target, touch_device).move(
        0, target_global, touch_target,
    ).commit()
    assert view.canvas._transition_overlay.x() < 0, (
        f"child touch did not move overlay: x={view.canvas._transition_overlay.x()}, "
        f"origin={view.canvas._mouse_swipe_origin}, target_geometry={touch_target.geometry()}"
    )
    QTest.touchEvent(touch_target, touch_device).release(
        0, target_global, touch_target,
    ).commit()
    app.processEvents()
    assert view.canvas.current_page_id == second.id
    assert view.canvas._swipe_original_widgets is None

    view.load_page(first.id)
    QTest.mousePress(view.canvas, Qt.MouseButton.LeftButton, pos=QPoint(300, 200))
    QTest.mouseMove(view.canvas, QPoint(270, 204))
    app.processEvents()
    assert view.canvas.current_page_id == second.id
    assert view.canvas._transition_overlay.x() < 0
    QTest.mouseRelease(view.canvas, Qt.MouseButton.LeftButton, pos=QPoint(270, 204))
    app.processEvents()
    assert view.canvas.current_page_id == first.id
    assert view.canvas._transition_animation.endValue() == QPoint(0, 0)

    view.load_page(second.id)
    view.canvas.set_edit_mode(True)
    QTest.mousePress(view.canvas, Qt.MouseButton.LeftButton, pos=QPoint(300, 200))
    QTest.mouseRelease(view.canvas, Qt.MouseButton.LeftButton, pos=QPoint(170, 204))
    app.processEvents()
    assert view.canvas.current_page_id == second.id
    assert DashboardCanvas.swipe_direction(QPoint(100, 10), QPoint(160, 100)) == 0
    db.close()
finally:
    shutil.rmtree(root, ignore_errors=True)

print("VERIFICATION PASSED")