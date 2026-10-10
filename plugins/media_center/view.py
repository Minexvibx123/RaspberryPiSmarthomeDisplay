"""Full-screen media controls for all Home Assistant media players."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget,
)


class MediaCenterView(QWidget):
    def __init__(self, state_manager, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        self._entity_ids: list[str] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Medien")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        layout.addWidget(title)
        self.player_combo = QComboBox()
        self.player_combo.currentIndexChanged.connect(self._select_player)
        layout.addWidget(self.player_combo)

        self.title_label = QLabel("Kein Mediaplayer verfügbar")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(self.title_label, 1)
        self.artist_label = QLabel("")
        self.artist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.artist_label)
        self.state_label = QLabel("")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.state_label)

        controls = QHBoxLayout()
        self.previous_button = QPushButton("⏮")
        self.play_pause_button = QPushButton("▶")
        self.next_button = QPushButton("⏭")
        for button in (self.previous_button, self.play_pause_button, self.next_button):
            button.setMinimumSize(64, 56)
            controls.addWidget(button)
        self.previous_button.clicked.connect(lambda: self._call("media_previous_track"))
        self.play_pause_button.clicked.connect(lambda: self._call("media_play_pause"))
        self.next_button.clicked.connect(lambda: self._call("media_next_track"))
        layout.addLayout(controls)

        self.source_combo = QComboBox()
        self.source_combo.currentIndexChanged.connect(self._select_source)
        self.source_combo.hide()
        layout.addWidget(self.source_combo)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.sliderReleased.connect(self._set_volume)
        layout.addWidget(self.volume_slider)
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        if self.state_manager:
            self.state_manager.entities_loaded.connect(self.refresh_players)
            self.state_manager.entity_updated.connect(self._on_entity_updated)
        self.refresh_players()

    def refresh_players(self) -> None:
        current = self.player_combo.currentData()
        entities = self.state_manager.entities.values() if self.state_manager else []
        players = sorted(
            (entity for entity in entities if entity.domain == "media_player"),
            key=lambda entity: entity.friendly_name.casefold(),
        )
        self.player_combo.blockSignals(True)
        self.player_combo.clear()
        self._entity_ids = []
        for entity in players:
            self.player_combo.addItem(entity.friendly_name, entity.entity_id)
            self._entity_ids.append(entity.entity_id)
        index = self.player_combo.findData(current)
        self.player_combo.setCurrentIndex(index if index >= 0 else (0 if players else -1))
        self.player_combo.blockSignals(False)
        self._select_player()

    def _select_player(self, *_args) -> None:
        entity_id = self.player_combo.currentData()
        entity = self.state_manager.get_entity(entity_id) if entity_id and self.state_manager else None
        if entity is None:
            self.title_label.setText("Kein Mediaplayer verfügbar")
            self.artist_label.clear()
            self.state_label.clear()
            self.source_combo.hide()
            self.volume_slider.setEnabled(False)
            return
        attributes = entity.attributes
        self.title_label.setText(attributes.get("media_title") or entity.friendly_name)
        self.artist_label.setText(attributes.get("media_artist", ""))
        self.state_label.setText(entity.state.replace("_", " ").title())
        self.play_pause_button.setText("⏸" if entity.state == "playing" else "▶")
        volume = attributes.get("volume_level")
        self.volume_slider.setEnabled(volume is not None)
        if volume is not None:
            self.volume_slider.blockSignals(True)
            self.volume_slider.setValue(round(float(volume) * 100))
            self.volume_slider.blockSignals(False)
        sources = attributes.get("source_list") or []
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        self.source_combo.addItems([str(source) for source in sources])
        self.source_combo.setCurrentText(str(attributes.get("source", "")))
        self.source_combo.setVisible(bool(sources))
        self.source_combo.blockSignals(False)

    def _on_entity_updated(self, entity_id: str, _new_state: dict) -> None:
        if entity_id in self._entity_ids:
            self._select_player()
        elif entity_id.startswith("media_player."):
            self.refresh_players()

    def _call(self, service: str, data: dict | None = None) -> None:
        entity_id = self.player_combo.currentData()
        if not entity_id or not self.state_manager:
            return
        self.status_label.setText("Aktion gesendet")
        self.state_manager.run_service_actions([{
            "domain": "media_player", "service": service,
            "entity_id": entity_id, "data": data or {},
        }])

    def _set_volume(self) -> None:
        self._call("volume_set", {"volume_level": self.volume_slider.value() / 100})

    def _select_source(self, index: int) -> None:
        if index >= 0:
            self._call("select_source", {"source": self.source_combo.currentText()})