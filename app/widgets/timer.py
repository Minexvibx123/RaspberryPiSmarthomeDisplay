"""Timer / Countdown widget."""
from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from app.widgets.base import BaseWidget, PropertyDef


class TimerWidget(BaseWidget):
    type_name = "timer"
    display_name = "Timer"
    category = "Steuerung"
    icon = "clock"
    default_size = (220, 160)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("label_text", "Beschriftung", "text", "Timer", group="Inhalt"),
        PropertyDef("duration_minutes", "Dauer (Minuten)", "number", 10, min=1, max=480, group="Inhalt"),
        PropertyDef("auto_restart", "Automatisch neustarten", "bool", False, group="Verhalten"),
    ]

    def __init__(self, widget_id: int, config: dict, state_manager=None, parent=None):
        self._remaining_seconds = 0
        self._running = False
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        super().__init__(widget_id, config, state_manager, parent)
        
        # Initialize timer state
        self._reset_timer()

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                    
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        # Label
        self.name_label = QLabel(self.get_prop("label_text", "Timer"))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {int(self.get_prop('font_size', 16)) - 2}px; border: none; background: transparent;"
        )
        
        # Time display
        self.time_label = QLabel("00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {int(self.get_prop('font_size', 16)) + 16}px; font-weight: 700; border: none; background: transparent;"
        )
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        
        accent = self.get_prop("accent_color", "#4C8DFF")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {accent};
                border-radius: 3px;
            }}
        """)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                color: white;
                font-size: 14px;
                border: none;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """
        
        self.btn_start = QPushButton("▶")
        self.btn_start.setFixedSize(32, 32)
        self.btn_start.setStyleSheet(btn_style)
        self.btn_start.clicked.connect(self._start_timer)
        
        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setFixedSize(32, 32)
        self.btn_pause.setStyleSheet(btn_style)
        self.btn_pause.clicked.connect(self._pause_timer)
        
        self.btn_reset = QPushButton("↺")
        self.btn_reset.setFixedSize(32, 32)
        self.btn_reset.setStyleSheet(btn_style)
        self.btn_reset.clicked.connect(self._reset_timer)
        
        buttons_layout.addWidget(self.btn_start)
        buttons_layout.addWidget(self.btn_pause)
        buttons_layout.addWidget(self.btn_reset)
        
        # Add to main layout
        self.content_layout.addWidget(self.name_label)
        self.content_layout.addWidget(self.time_label)
        self.content_layout.addWidget(self.progress_bar)
        
        buttons_widget = QWidget()
        buttons_widget.setLayout(buttons_layout)
        buttons_widget.setStyleSheet("background: transparent;")
        self.content_layout.addWidget(buttons_widget)
        
        self._update_display()

    def _tick(self) -> None:
        if not self._running:
            return
            
        if self._remaining_seconds > 0:
            self._remaining_seconds -= 1
            self._update_display()
            
            if self._remaining_seconds == 0:
                self._timer_finished()

    def _start_timer(self) -> None:
        if self._remaining_seconds <= 0:
            self._reset_timer()
            
        self._running = True
        self._timer.start(1000)
        self.set_active(True)
        self._update_display()

    def _pause_timer(self) -> None:
        self._running = False
        self._timer.stop()
        self.set_active(False)
        self._update_display()

    def _reset_timer(self) -> None:
        self._running = False
        self._timer.stop()
        self.set_active(False)
        
        duration_mins = self.get_prop("duration_minutes", 10)
        self._remaining_seconds = int(duration_mins * 60)
        
        # Reset styles
        if hasattr(self, 'time_label'):
            self.time_label.setStyleSheet(
                f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {int(self.get_prop('font_size', 16)) + 16}px; font-weight: 700; border: none; background: transparent;"
            )
            
        self._update_display()

    def _timer_finished(self) -> None:
        self._running = False
        self._timer.stop()
        
        # Visual alert
        self.set_active(True)
        self.time_label.setStyleSheet(
            f"color: #FF4444; font-size: {int(self.get_prop('font_size', 16)) + 16}px; font-weight: 700; border: none; background: transparent;"
        )
        
        if self.get_prop("auto_restart", False):
            # Restart after a short delay to show the alert
            QTimer.singleShot(2000, self._start_timer)

    def _update_display(self) -> None:
        if not hasattr(self, 'time_label'):
            return
            
        # Update time text
        mins = self._remaining_seconds // 60
        secs = self._remaining_seconds % 60
        self.time_label.setText(f"{mins:02d}:{secs:02d}")
        
        # Update progress bar
        duration_secs = int(self.get_prop("duration_minutes", 10) * 60)
        self.progress_bar.setMaximum(duration_secs)
        
        # Progress bar goes down as time decreases
        self.progress_bar.setValue(self._remaining_seconds)
        
        # Update button states
        self.btn_start.setVisible(not self._running)
        self.btn_pause.setVisible(self._running)

    def refresh_from_state(self) -> None:
        # Timer doesn't depend on external state, but we might need to update
        # if config changed (e.g. duration_minutes)
        pass
        
    def apply_config(self, config: dict) -> None:
        super().apply_config(config)
        # If duration changed while stopped, reset to new duration
        if not self._running:
            self._reset_timer()
            
    def deleteLater(self) -> None:
        self._timer.stop()
        super().deleteLater()
