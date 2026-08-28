"""Media Player widget - transport controls and volume."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout

from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph


class MediaPlayerWidget(BaseWidget):
    type_name = "media_player"
    display_name = "Medienplayer"
    category = "Steuerung"
    icon = "speaker"
    default_size = (200, 160)
    requires_entity = True
    entity_domains = ["media_player"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["media_player"], group="Verbindung"),
        PropertyDef("show_volume", "Lautstärkeregler anzeigen", "bool", True, group="Verhalten"),
        PropertyDef("show_media_info", "Medieninfo anzeigen", "bool", True, group="Verhalten"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        header = QHBoxLayout()
        self.icon_label = IconGlyph("speaker", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(int(self.get_prop('font_size', 16)) + 16, int(self.get_prop('font_size', 16)) + 16)
        self.name_label = QLabel(self.get_prop("name") or self.config.get("entity_id", "Medienplayer"))
        self.name_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 600; border: none; background: transparent;"
        )
        header.addWidget(self.icon_label)
        header.addWidget(self.name_label, 1)
        self.content_layout.addLayout(header)

        self.state_label = QLabel("")
        self.state_label.setStyleSheet("color: #AAAAAA; font-size: 12px; border: none; background: transparent;")
        self.content_layout.addWidget(self.state_label)

        self.media_info_label = QLabel("")
        self.media_info_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: 13px; border: none; background: transparent;")
        self.media_info_label.setWordWrap(True)
        if self.get_prop("show_media_info", True):
            self.content_layout.addWidget(self.media_info_label)

        controls_row = QHBoxLayout()
        self.prev_btn = QPushButton("⏮")
        self.play_pause_btn = QPushButton("▶/⏸")
        self.next_btn = QPushButton("⏭")
        
        for b, cb in ((self.prev_btn, self._prev), (self.play_pause_btn, self._play_pause), (self.next_btn, self._next)):
            b.setStyleSheet(f"QPushButton {{ background: rgba(255,255,255,20); color: {self.get_prop('text_color', '#FFFFFF')}; border-radius: 8px; padding: 6px; font-size: 16px; }}")
            b.clicked.connect(cb)
            controls_row.addWidget(b)
        self.content_layout.addLayout(controls_row)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        if self.get_prop("show_volume", True):
            self.content_layout.addWidget(self.volume_slider)
            
        self.content_layout.addStretch()

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            self.state_label.setText("Keine Verbindung")
            self.media_info_label.setText("")
            return
            
        is_playing = e.state == "playing"
        self.set_active(is_playing)
        
        state_text = "idle"
        if e.state == "playing":
            state_text = "playing"
        elif e.state == "paused":
            state_text = "paused"
        self.state_label.setText(state_text)
        
        accent = self.get_prop("accent_color", "#4C8DFF")
        self.icon_label.set_color(accent if is_playing else "#777777")
        
        self.play_pause_btn.setText("⏸" if is_playing else "▶")
        
        title = e.attributes.get("media_title", "")
        artist = e.attributes.get("media_artist", "")
        
        info_text = ""
        if title and artist:
            info_text = f"{title} - {artist}"
        elif title:
            info_text = title
        elif artist:
            info_text = artist
            
        self.media_info_label.setText(info_text)
        
        volume_level = e.attributes.get("volume_level")
        if volume_level is not None:
            self.volume_slider.blockSignals(True)
            self.volume_slider.setValue(int(volume_level * 100))
            self.volume_slider.blockSignals(False)

    def _play_pause(self) -> None:
        self.call_service("media_player", "media_play_pause")

    def _prev(self) -> None:
        self.call_service("media_player", "media_previous_track")

    def _next(self) -> None:
        self.call_service("media_player", "media_next_track")
        
    def _on_volume_changed(self, value: int) -> None:
        self.call_service("media_player", "volume_set", volume_level=value / 100.0)
