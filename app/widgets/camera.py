"""Camera widget - displays a snapshot from a camera entity."""
from __future__ import annotations

import logging
from urllib.parse import urljoin

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from app.core.http_fetch import fetch
from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph

logger = logging.getLogger(__name__)


class CameraWidget(BaseWidget):
    type_name = "camera"
    display_name = "Kamera"
    category = "Anzeige"
    icon = "camera"
    default_size = (300, 240)
    requires_entity = True
    entity_domains = ["camera"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["camera"], group="Verbindung"),
        PropertyDef("refresh_seconds", "Aktualisierung (Sekunden)", "number", 5, min=1, max=60, group="Verhalten"),
        PropertyDef("show_snapshot", "Bild anzeigen", "bool", True, group="Verhalten"),
    ]

    def __init__(self, widget_id: int, config: dict, state_manager=None, parent=None):
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._fetch_snapshot)
        super().__init__(widget_id, config, state_manager, parent)

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        header = QHBoxLayout()
        self.icon_label = IconGlyph("camera", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(int(self.get_prop('font_size', 16)) + 16, int(self.get_prop('font_size', 16)) + 16)
        self.name_label = QLabel(self.get_prop("name") or self.config.get("entity_id", "Kamera"))
        self.name_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 600; border: none; background: transparent;"
        )
        header.addWidget(self.icon_label)
        header.addWidget(self.name_label, 1)
        self.content_layout.addLayout(header)

        self.state_label = QLabel("")
        self.state_label.setStyleSheet("color: #AAAAAA; font-size: 12px; border: none; background: transparent;")
        self.content_layout.addWidget(self.state_label)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: rgba(0,0,0,50); border-radius: 8px;")
        
        if self.get_prop("show_snapshot", True):
            self.content_layout.addWidget(self.image_label, 1)
        else:
            self.content_layout.addStretch()

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            self.state_label.setText("Keine Verbindung")
            self._refresh_timer.stop()
            return
            
        self.set_active(e.state == "idle" or e.state == "recording")
        self.state_label.setText(e.state)
        
        accent = self.get_prop("accent_color", "#4C8DFF")
        self.icon_label.set_color(accent if self._active else "#777777")
        
        if self.get_prop("show_snapshot", True):
            if not self._refresh_timer.isActive():
                self._fetch_snapshot()
                refresh_ms = int(self.get_prop("refresh_seconds", 5)) * 1000
                self._refresh_timer.start(refresh_ms)
        else:
            self._refresh_timer.stop()

    def _fetch_snapshot(self) -> None:
        if not self.state_manager or not self.config.get("entity_id"):
            return
            
        entity_id = self.config.get("entity_id")
        
        # Try to get token and url from client or settings
        token = None
        ha_url = None
        
        if hasattr(self.state_manager, 'client') and self.state_manager.client:
            token = getattr(self.state_manager.client, 'token', None)
            ha_url = getattr(self.state_manager.client, 'url', None)
            
        if not token and hasattr(self.state_manager, 'settings'):
            token = getattr(self.state_manager.settings, 'ha_token', None)
        if not ha_url and hasattr(self.state_manager, 'settings'):
            ha_url = getattr(self.state_manager.settings, 'ha_url', None)
            
        if not token or not ha_url:
            self.state_label.setText("Fehlende HA Konfiguration")
            return
            
        # Clean up URL
        if ha_url.endswith('/api'):
            ha_url = ha_url[:-4]
        elif ha_url.endswith('/api/'):
            ha_url = ha_url[:-5]
            
        url = urljoin(ha_url, f"/api/camera_proxy/{entity_id}")
        headers = {"Authorization": f"Bearer {token}"}
        
        fetch(
            url=url,
            on_success=self._on_snapshot_success,
            on_error=self._on_snapshot_error,
            headers=headers,
            as_json=False,
            parent=self
        )

    def _on_snapshot_success(self, data: str) -> None:
        # http_fetch returns text, we need to encode it back to bytes for QImage
        try:
            image_bytes = data.encode('ISO-8859-1')
            image = QImage.fromData(image_bytes)
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                # Scale to fit label while keeping aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.image_label.size(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                logger.warning("Failed to load camera snapshot image data")
        except Exception as e:
            logger.error(f"Error processing camera snapshot: {e}")

    def _on_snapshot_error(self, error: str) -> None:
        logger.warning(f"Failed to fetch camera snapshot: {error}")
        self.state_label.setText(f"Fehler: {error}")
        
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # We could re-scale the pixmap here if we kept the original, 
        # but for a camera it will refresh soon anyway
