"""Notification widget for displaying Home Assistant persistent notifications."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from app.core.http_fetch import fetch
from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph


class NotificationWidget(BaseWidget):
    type_name = "notification"
    display_name = "Benachrichtigungen"
    category = "Anzeige"
    icon = "shield"
    default_size = (280, 220)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("refresh_seconds", "Aktualisierung (s)", "number", 30, min=10, max=300, group="Inhalt"),
        PropertyDef("max_items", "Max. Anzahl", "number", 5, min=1, max=20, group="Inhalt"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item:
                w = item.widget()
                if w:
                    w.deleteLater()

        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        
        title_layout = QVBoxLayout()
        self.title_label = QLabel(self.get_prop("name") or "Benachrichtigungen")
        self.title_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {int(self.get_prop('font_size', 16))}px; font-weight: 600;"
        )
        title_layout.addWidget(self.title_label)
        header_layout.addLayout(title_layout)
        
        self.content_layout.addWidget(header)

        # Scroll Area for notifications
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(12, 0, 12, 12)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.scroll_content)
        self.content_layout.addWidget(self.scroll_area, 1)

        # Timer for auto-refresh
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._fetch_notifications)
        
        # Initial fetch
        self._fetch_notifications()

    def _safe_refresh_from_state(self) -> None:
        # Update timer interval if changed
        interval_ms = int(self.get_prop("refresh_seconds", 30)) * 1000
        if self._refresh_timer.interval() != interval_ms:
            self._refresh_timer.start(interval_ms)
            
        # Update title
        self.title_label.setText(self.get_prop("name") or "Benachrichtigungen")
        self.title_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {int(self.get_prop('font_size', 16))}px; font-weight: 600;"
        )
        
        # Re-fetch
        self._fetch_notifications()

    def _fetch_notifications(self) -> None:
        if not self.state_manager or not self.state_manager.settings.ha_url:
            self._render_empty("Keine Verbindung")
            return

        url = f"{self.state_manager.settings.ha_url}/api/states"
        headers = {
            "Authorization": f"Bearer {self.state_manager.settings.ha_token}",
            "Content-Type": "application/json",
        }
        
        fetch(
            url,
            on_success=self._on_fetch_success,
            on_error=lambda err: self._render_empty(f"Fehler: {err}"),
            headers=headers,
            parent=self
        )

    def _on_fetch_success(self, data: list) -> None:
        if not isinstance(data, list):
            self._render_empty("Ungültige Daten")
            return

        # Filter for persistent notifications
        notifications = [
            entity for entity in data 
            if entity.get("entity_id", "").startswith("persistent_notification.")
        ]
        
        # Sort by last_updated descending
        notifications.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
        
        # Limit items
        max_items = int(self.get_prop("max_items", 5))
        notifications = notifications[:max_items]

        # Clear current layout
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item and item.widget():
                w = item.widget()
                if w:
                    w.deleteLater()

        if not notifications:
            self._render_empty("Keine Benachrichtigungen")
            return

        # Render notifications
        text_color = self.get_prop("text_color", "#FFFFFF")
        accent_color = self.get_prop("accent_color", "#4C8DFF")
        font_size = int(self.get_prop("font_size", 16))
        
        for notif in notifications:
            attrs = notif.get("attributes", {})
            title = attrs.get("title", "Benachrichtigung")
            message = attrs.get("message", "")
            
            # Format time (simple extraction from ISO string)
            time_str = notif.get("last_updated", "")
            if "T" in time_str:
                time_part = time_str.split("T")[1][:5] # HH:MM
                date_part = time_str.split("T")[0].split("-")
                if len(date_part) == 3:
                    time_str = f"{date_part[2]}.{date_part[1]}. {time_part}"
            
            item_widget = QWidget()
            item_widget.setStyleSheet(f"background: rgba(255,255,255,10); border-radius: 8px;")
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(10, 8, 10, 8)
            item_layout.setSpacing(4)
            
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet(f"color: {accent_color}; font-size: {font_size - 2}px; font-weight: 600; background: transparent;")
            title_lbl.setWordWrap(True)
            
            msg_lbl = QLabel(message)
            msg_lbl.setStyleSheet(f"color: {text_color}; font-size: {font_size - 4}px; background: transparent;")
            msg_lbl.setWordWrap(True)
            
            time_lbl = QLabel(time_str)
            time_lbl.setStyleSheet(f"color: rgba(255,255,255,120); font-size: {font_size - 6}px; background: transparent;")
            time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            
            item_layout.addWidget(title_lbl)
            item_layout.addWidget(msg_lbl)
            item_layout.addWidget(time_lbl)
            
            self.scroll_layout.addWidget(item_widget)

    def _render_empty(self, message: str) -> None:
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item:
                w = item.widget()
                if w:
                    w.deleteLater()
                
        lbl = QLabel(message)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"color: rgba(255,255,255,120); font-size: {int(self.get_prop('font_size', 16)) - 2}px; background: transparent;"
        )
        self.scroll_layout.addWidget(lbl)
