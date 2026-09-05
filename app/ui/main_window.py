"""Main application window – two-stage standby state machine.

State machine: NORMAL → DIMMED → OFF.  Any user interaction resets to NORMAL.
When ``standby_enabled`` is *False* the legacy screensaver behaviour
(plain clock overlay after ``screensaver_timeout`` minutes) is used instead.
"""
from __future__ import annotations

import glob
import logging
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from app.core.database import Database
from app.core.settings import AppSettings
from app.core.state_manager import StateManager
from app.core.service_registry import ServiceRegistry
from app.core.workflows import WorkflowEngine
from app.plugins.manager import PluginManager
from app.ui.dashboard import ConnectionBadge, DashboardCanvas
from app.ui.app_launcher import AppLauncher
from app.ui.editor import EditorScreen
from app.ui.navigation import NavigationBar
from app.ui.settings_screen import SettingsScreen
from app.ui.setup_wizard import SetupWizard
from app.ui.themes import ThemeManager

EDIT_HOLD_MS = 3000
CORNER_SIZE = 70

_log = logging.getLogger(__name__)

_BACKLIGHT_BL_POWER_GLOBS = ["/sys/class/backlight/*/bl_power"]
_BACKLIGHT_BRIGHTNESS_GLOBS = ["/sys/class/backlight/*/brightness"]
_BACKLIGHT_OFF = b"4"
_BACKLIGHT_ON = b"0"


class CornerGestureZone(QWidget):
    """Invisible zone in a corner - press and hold for EDIT_HOLD_MS to trigger."""

    def __init__(self, on_triggered, parent=None):
        super().__init__(parent)
        self.on_triggered = on_triggered
        self.setFixedSize(CORNER_SIZE, CORNER_SIZE)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fire)

    def mousePressEvent(self, event) -> None:
        self._timer.start(EDIT_HOLD_MS)

    def mouseReleaseEvent(self, event) -> None:
        self._timer.stop()

    def _fire(self) -> None:
        self.on_triggered()


class DashboardView(QWidget):
    """Normal (non-editor) run mode."""

    def __init__(self, db, state_manager, settings, on_request_edit, on_request_settings, on_request_apps, on_navigate_page, design_size, parent=None):
        super().__init__(parent)
        self.db = db
        self.settings = settings

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(16, 10, 16, 4)
        self.badge = ConnectionBadge(state_manager)
        top_bar.addWidget(self.badge, 1)
        settings_btn = QPushButton("\u2699")
        settings_btn.setFixedSize(40, 40)
        settings_btn.clicked.connect(on_request_settings)
        top_bar.addWidget(settings_btn)
        apps_btn = QPushButton("Apps")
        apps_btn.clicked.connect(on_request_apps)
        top_bar.addWidget(apps_btn)
        root.addLayout(top_bar)

        self.canvas = DashboardCanvas(state_manager, db, design_size)
        self.canvas.set_edit_mode(False)
        self.canvas.navigate_requested.connect(on_navigate_page)
        root.addWidget(self.canvas, 1)

        self.nav_bar = NavigationBar(style=settings.navigation_style)
        self.nav_bar.page_selected.connect(self.load_page)
        root.addWidget(self.nav_bar)

        self.corner_zone = CornerGestureZone(on_request_edit, self)
        self.corner_zone.move(0, 0)
        self.corner_zone.raise_()

    def load_page(self, page_id: int) -> None:
        self.canvas.load_page(page_id)
        self.nav_bar.set_pages(self.db.list_pages(), page_id)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.corner_zone.raise_()


class _StandbyOverlay(QWidget):
    """Full-window overlay for DIMMED and OFF standby states."""

    interacted = Signal()

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self._settings = settings
        self.setAutoFillBackground(True)
        self._background_label = QLabel(self)
        self._background_label.setScaledContents(True)
        self._background_label.lower()
        self._timer_label = QLabel(self)
        self._timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._timer_label.setStyleSheet("color: white; font-size: 48px; font-weight: 300;")
        self._date_label = QLabel(self)
        self._date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._date_label.setStyleSheet("color: rgba(255,255,255,150); font-size: 18px;")
        self._info_label = QLabel(self)
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_label.setStyleSheet("color: rgba(255,255,255,190); font-size: 16px;")
        layout = QVBoxLayout(self)
        layout.addWidget(self._timer_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._date_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._info_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_time)
        self._clock_timer.start(1000)
        self._info_timer = QTimer(self)
        self._info_timer.timeout.connect(self._update_info)
        self._update_time()

    def set_darkness(self, opacity_percent: int) -> None:
        alpha = max(0, min(255, int(opacity_percent * 255 / 100)))
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QColor(0, 0, 0, alpha))
        self.setPalette(pal)
        self._timer_label.setVisible(True)
        self._date_label.setVisible(True)
        self._apply_screensaver_mode()

    def set_fully_black(self) -> None:
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QColor(0, 0, 0, 255))
        self.setPalette(pal)
        self._timer_label.setVisible(True)
        self._date_label.setVisible(True)
        self._apply_screensaver_mode()

    def _apply_screensaver_mode(self) -> None:
        background_path = self._settings.screensaver_background_path if self._settings else ""
        pixmap = QPixmap(background_path) if background_path else None
        if pixmap and not pixmap.isNull():
            self._background_label.setPixmap(pixmap)
            self._background_label.setGeometry(self.rect())
            self._background_label.show()
        else:
            self._background_label.hide()

        mode = self._settings.screensaver_mode if self._settings else "digital_clock"
        if mode == "system_info":
            self._info_label.show()
            self._update_info()
            self._info_timer.start(5000)
        else:
            self._info_timer.stop()
            self._info_label.hide()

    def _update_info(self) -> None:
        try:
            import os

            load_percent = min(100, round(os.getloadavg()[0] * 100 / max(1, os.cpu_count() or 1)))
            meminfo = {}
            for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
                key, value = line.split(":", 1)
                meminfo[key] = int(value.split()[0])
            mem_percent = round(100 * (1 - meminfo.get("MemAvailable", meminfo.get("MemFree", 0)) / max(1, meminfo.get("MemTotal", 1))))
            temperature = None
            for zone in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
                try:
                    temperature = int(Path(zone).read_text(encoding="utf-8").strip()) / 1000
                    break
                except (OSError, ValueError):
                    continue
            text = f"CPU {load_percent}%  RAM {mem_percent}%"
            if temperature is not None:
                text += f"  {temperature:.1f} °C"
            self._info_label.setText(text)
        except OSError:
            self._info_label.setText("Systeminformationen nicht verfügbar")

    def _update_time(self) -> None:
        from datetime import datetime
        now = datetime.now()
        self._timer_label.setText(now.strftime("%H:%M"))
        self._date_label.setText(now.strftime("%A, %d. %B %Y"))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._background_label.setGeometry(self.rect())

    def mousePressEvent(self, event) -> None:
        self.interacted.emit()

    def mouseReleaseEvent(self, event) -> None:
        self.interacted.emit()

    def mouseMoveEvent(self, event) -> None:
        self.interacted.emit()

    def wheelEvent(self, event) -> None:
        self.interacted.emit()


def _backlight_set_state(off: bool, saved_state: dict) -> None:
    """Best-effort backlight control via sysfs.  *saved_state* is mutated
    to remember the original brightness for later restoration."""
    try:
        for pattern in _BACKLIGHT_BL_POWER_GLOBS:
            for path in glob.glob(pattern):
                if off:
                    try:
                        orig = Path(path).read_bytes().strip()
                        saved_state.setdefault("bl_power", {})[path] = orig
                    except OSError:
                        pass
                    try:
                        Path(path).write_bytes(_BACKLIGHT_OFF)
                    except OSError as exc:
                        _log.warning("Cannot write %s: %s", path, exc)
                else:
                    try:
                        Path(path).write_bytes(_BACKLIGHT_ON)
                    except OSError:
                        pass
        for pattern in _BACKLIGHT_BRIGHTNESS_GLOBS:
            for path in glob.glob(pattern):
                if off:
                    try:
                        orig = Path(path).read_bytes().strip()
                        saved_state.setdefault("brightness", {})[path] = orig
                    except OSError:
                        pass
                    try:
                        Path(path).write_bytes(b"0")
                    except OSError:
                        pass
                else:
                    restored = saved_state.get("brightness", {}).get(path)
                    if restored is not None:
                        try:
                            Path(path).write_bytes(restored)
                        except OSError:
                            pass
    except Exception:
        if not saved_state.get("_warned"):
            _log.warning("Backlight sysfs control unavailable, relying on black overlay", exc_info=True)
            saved_state["_warned"] = True

class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("HomePanel")
        self.db = Database()
        self.settings = AppSettings(self.db)
        self.theme_manager = ThemeManager(self.db)
        self.theme_manager.apply(self.app, self.theme_manager.active())

        self.auto_check_timer = QTimer(self)
        self.auto_check_timer.timeout.connect(lambda: self.theme_manager.check_auto_mode(self.app, self.db))
        self.auto_check_timer.start(300000)
        self.theme_manager.check_auto_mode(self.app, self.db)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self._standby_state = "NORMAL"
        self._saved_backlight: dict = {}
        self._overlay = _StandbyOverlay(self, settings=self.settings)
        self._overlay.interacted.connect(self.wake_from_standby)
        self._overlay.hide()

        self._dim_timer = QTimer(self)
        self._dim_timer.setSingleShot(True)
        self._dim_timer.timeout.connect(self._enter_dimmed)

        self._off_timer = QTimer(self)
        self._off_timer.setSingleShot(True)
        self._off_timer.timeout.connect(self._enter_off)

        self._screensaver_timeout_minutes = self.settings.db.get_setting("screensaver_timeout", 10)
        self._legacy_timer = QTimer(self)
        self._legacy_timer.setSingleShot(True)
        self._legacy_timer.timeout.connect(self._show_legacy_screensaver)
        self._legacy_overlay = _StandbyOverlay(self, settings=self.settings)
        self._legacy_overlay.interacted.connect(self._wake_legacy)
        self._legacy_overlay.hide()
        self._legacy_active = False

        self._reset_standby_timer()

        if not self.settings.setup_complete:
            self.wizard = SetupWizard()
            self.wizard.finished.connect(self._on_setup_finished)
            self.stack.addWidget(self.wizard)
            self.stack.setCurrentWidget(self.wizard)
        else:
            self._start_runtime()

    def _on_setup_finished(self, data: dict) -> None:
        self.settings.language = data.get("language", "de")
        self.settings.ha_url = data.get("ha_url", "")
        self.settings.ha_token = data.get("ha_token", "")
        self.settings.demo_mode = data.get("demo_mode", False)
        self.settings.setup_complete = True
        self._start_runtime()

    def _start_runtime(self) -> None:
        self.state_manager = StateManager(self.settings)
        self.state_manager.start()

        self.services = ServiceRegistry()
        self.services.register("database", self.db)
        self.services.register("settings", self.settings)
        self.services.register("state_manager", self.state_manager)
        plugins_root = Path(__file__).resolve().parent.parent.parent / "plugins"
        self.plugin_manager = PluginManager(self.db, self.services, plugins_root)
        self.plugin_manager.load_all()
        self.services.register("plugin_manager", self.plugin_manager)

        self.workflow_engine = WorkflowEngine(self.db, self.state_manager)
        self.services.register("workflow_engine", self.workflow_engine)

        design_size = self.settings.effective_design_resolution
        pages = self.db.list_pages()
        first_page_id = pages[0].id if pages else self.db.create_page("Home").id

        self.dashboard_view = DashboardView(
            self.db, self.state_manager, self.settings,
            on_request_edit=self._request_edit_mode,
            on_request_settings=self._show_settings,
            on_request_apps=self._show_apps,
            on_navigate_page=self._navigate_to_page_name,
            design_size=design_size,
        )
        self.editor_screen = EditorScreen(self.db, self.state_manager, design_size)
        self.editor_screen.exit_requested.connect(self._on_editor_exit)

        self.settings_screen = SettingsScreen(
            self.db, self.settings, self.theme_manager, self.app,
            on_theme_applied=self._refresh_theme,
            plugin_manager=self.plugin_manager,
        )
        self.settings_back_btn = QPushButton("\u2190 Zurück zum Panel")
        self.settings_back_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.dashboard_view))
        settings_wrap = QWidget()
        wrap_layout = QVBoxLayout(settings_wrap)
        wrap_layout.addWidget(self.settings_back_btn)
        wrap_layout.addWidget(self.settings_screen, 1)

        for w in (self.dashboard_view, self.editor_screen, settings_wrap):
            self.stack.addWidget(w)
        self.settings_wrap = settings_wrap
        self.app_launcher = AppLauncher(self.plugin_manager, self._open_plugin_app)
        self.stack.addWidget(self.app_launcher)

        self.dashboard_view.load_page(first_page_id)
        self.stack.setCurrentWidget(self.dashboard_view)

    def _request_edit_mode(self) -> None:
        if self.settings.edit_pin:
            pin, ok = QInputDialog.getText(self, "PIN erforderlich", "Editor-PIN eingeben:", QLineEdit.EchoMode.Password)
            if not ok or pin != self.settings.edit_pin:
                if ok:
                    QMessageBox.warning(self, "Falsche PIN", "Der Editor-Modus wurde nicht entsperrt.")
                return
        current_page = self.dashboard_view.canvas.current_page_id
        if current_page is not None:
            self.editor_screen.enter(current_page)
            self.stack.setCurrentWidget(self.editor_screen)

    def _on_editor_exit(self, saved: bool) -> None:
        current_page = self.editor_screen.current_page_id
        if current_page is not None:
            self.dashboard_view.load_page(current_page)
        self.stack.setCurrentWidget(self.dashboard_view)

    def _show_settings(self) -> None:
        self.stack.setCurrentWidget(self.settings_wrap)

    def _show_apps(self) -> None:
        self.stack.setCurrentWidget(self.app_launcher)

    def _open_plugin_app(self, plugin_id: str) -> None:
        view = self.plugin_manager.get_instance(plugin_id).create_app_view(self)
        if view is not None:
            self.stack.addWidget(view)
            self.stack.setCurrentWidget(view)

    def _navigate_to_page_name(self, page_name: str) -> None:
        for page in self.db.list_pages():
            if page.name == page_name:
                self.dashboard_view.load_page(page.id)
                self.stack.setCurrentWidget(self.dashboard_view)
                return

    def _refresh_theme(self) -> None:
        pass

    def _reset_standby_timer(self) -> None:
        self._dim_timer.stop()
        self._off_timer.stop()
        if self.settings.standby_enabled:
            self._dim_timer.start(self.settings.standby_dim_minutes * 60_000)
        else:
            self._legacy_timer.start(self._screensaver_timeout_minutes * 60_000)

    def _enter_dimmed(self) -> None:
        if not self.settings.standby_enabled:
            return
        self._standby_state = "DIMMED"
        self._overlay.set_darkness(self.settings.standby_dim_opacity)
        self._overlay.resize(self.size())
        self._overlay.show()
        self._overlay.raise_()
        self._off_timer.start(self.settings.standby_off_minutes * 60_000)

    def _enter_off(self) -> None:
        if not self.settings.standby_enabled:
            return
        self._standby_state = "OFF"
        _backlight_set_state(True, self._saved_backlight)
        self._overlay.set_fully_black()
        self._overlay.resize(self.size())
        self._overlay.show()
        self._overlay.raise_()

    def wake_from_standby(self) -> None:
        was_off = self._standby_state == "OFF"
        self._standby_state = "NORMAL"
        self._dim_timer.stop()
        self._off_timer.stop()
        self._overlay.hide()
        if was_off:
            _backlight_set_state(False, self._saved_backlight)
            self._saved_backlight.clear()
        self._reset_standby_timer()

    def _show_legacy_screensaver(self) -> None:
        self._legacy_active = True
        self._legacy_overlay.set_darkness(80)
        self._legacy_overlay.resize(self.size())
        self._legacy_overlay.show()
        self._legacy_overlay.raise_()

    def _wake_legacy(self) -> None:
        if self._legacy_active:
            self._legacy_active = False
            self._legacy_overlay.hide()
        self._reset_standby_timer()

    def mouseMoveEvent(self, event) -> None:
        self._wake_or_reset()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        self._wake_or_reset()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._wake_or_reset()
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        self._wake_or_reset()
        super().wheelEvent(event)

    def keyPressEvent(self, event) -> None:
        self._wake_or_reset()
        super().keyPressEvent(event)

    def _wake_or_reset(self) -> None:
        if self._standby_state != "NORMAL":
            self.wake_from_standby()
        elif self._legacy_active:
            self._wake_legacy()
        else:
            self._reset_standby_timer()

    def resizeEvent(self, event) -> None:
        if hasattr(self, "_overlay"):
            self._overlay.resize(self.size())
        if hasattr(self, "_legacy_overlay"):
            self._legacy_overlay.resize(self.size())
        super().resizeEvent(event)

    def closeEvent(self, event) -> None:
        if hasattr(self, "state_manager"):
            self.state_manager.stop()
        _backlight_set_state(False, self._saved_backlight)
        super().closeEvent(event)
