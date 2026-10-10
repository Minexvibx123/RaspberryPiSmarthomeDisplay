"""Building blocks shared by the bundled HomePanel apps."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.ui import design

STATE_DE = {
    "on": "An", "off": "Aus", "open": "Offen", "closed": "Geschlossen", "opening": "Öffnet",
    "closing": "Schließt", "playing": "Spielt", "paused": "Pausiert", "idle": "Bereit",
    "home": "Zuhause", "not_home": "Unterwegs", "unavailable": "Nicht erreichbar",
    "unknown": "Unbekannt", "locked": "Verriegelt", "unlocked": "Entriegelt", "heat": "Heizen",
    "cool": "Kühlen", "auto": "Automatik", "heat_cool": "Heizen/Kühlen", "dry": "Entfeuchten",
    "fan_only": "Lüften", "armed_away": "Scharf (abwesend)", "armed_home": "Scharf (zuhause)",
    "disarmed": "Unscharf", "triggered": "AUSGELÖST",
}


def tr(state: str) -> str:
    return STATE_DE.get(str(state), str(state))


def number(entity) -> float | None:
    try:
        return float(entity.state)
    except (TypeError, ValueError):
        return None


def tone_color(tone: str) -> str:
    surface = design._ACTIVE["surface"]
    base = {"ok": design._ACTIVE["accent"], "warn": "#D9961A", "bad": "#E5645A"}.get(tone)
    return design.readable(base, surface, 3.0) if base else design.readable(design._ACTIVE["text"], surface)


@dataclass
class AppContext:
    db: Any
    state_manager: Any = None
    app_id: str = ""

    def load(self, key: str, default: Any = None) -> Any:
        return self.db.get_setting(f"app.{self.app_id}.{key}", default)

    def save(self, key: str, value: Any) -> None:
        self.db.set_setting(f"app.{self.app_id}.{key}", value)

    def entities(self) -> list:
        return list(self.state_manager.entities.values()) if self.state_manager else []

    def call(self, actions: list[dict]) -> None:
        if self.state_manager:
            self.state_manager.run_service_actions(actions)


class AppPage(QWidget):
    """Common frame: large title, then free content below."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(24, 18, 24, 18)
        self.root.setSpacing(14)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 26px; font-weight: 800;")
        self.root.addWidget(self.title_label)


def card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("appCard")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(8)
    return frame, layout


def big_button(text: str, callback: Callable, variant: str = "") -> QPushButton:
    button = QPushButton(text)
    button.setMinimumHeight(54)
    if variant:
        button.setProperty("variant", variant)
    button.clicked.connect(lambda _checked=False: callback())
    return button


@dataclass
class BoardSpec:
    title: str
    select: Callable[[Any], bool]
    describe: Callable[[Any], str]
    sort: Callable[[Any], Any]
    actions: Callable[[Any], list]
    tone: Callable[[Any], str] = lambda entity: ""
    empty: str = "Keine passenden Geräte gefunden."
    limit: int = 80
    columns: int = 2


class EntityBoard(AppPage):
    """Card grid of Home Assistant entities with per-entity action buttons."""

    def __init__(self, ctx: AppContext, spec: BoardSpec, parent=None):
        super().__init__(spec.title, parent)
        self.ctx, self.spec = ctx, spec
        self._shown: set[str] = set()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(12)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.container)
        self.root.addWidget(self.scroll, 1)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.refresh)
        if ctx.state_manager:
            ctx.state_manager.entities_loaded.connect(self.refresh)
            ctx.state_manager.entity_updated.connect(self._on_updated)
        self.refresh()

    def _on_updated(self, entity_id: str, _state: dict) -> None:
        entity = self.ctx.state_manager.get_entity(entity_id)
        if entity_id in self._shown or (entity is not None and self.spec.select(entity)):
            self._timer.start(250)

    def refresh(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        entities = sorted((e for e in self.ctx.entities() if self.spec.select(e)), key=self.spec.sort)
        entities = entities[: self.spec.limit]
        self._shown = {e.entity_id for e in entities}
        if not entities:
            empty = QLabel(self.spec.empty)
            empty.setWordWrap(True)
            self.grid.addWidget(empty, 0, 0)
            return
        for index, entity in enumerate(entities):
            self.grid.addWidget(self._card(entity), index // self.spec.columns, index % self.spec.columns)

    def _card(self, entity) -> QFrame:
        frame, layout = card()
        name = QLabel(entity.friendly_name)
        name.setStyleSheet("font-size: 17px; font-weight: 700;")
        name.setWordWrap(True)
        layout.addWidget(name)
        status = QLabel(self.spec.describe(entity))
        status.setStyleSheet(f"color: {tone_color(self.spec.tone(entity))}; font-weight: 600;")
        status.setWordWrap(True)
        layout.addWidget(status)
        actions = self.spec.actions(entity)
        if actions:
            row = QHBoxLayout()
            for label, domain, service, data in actions:
                button = big_button(label, lambda d=domain, s=service, x=data, eid=entity.entity_id: self.ctx.call(
                    [{"domain": d, "service": s, "entity_id": eid, "data": x}]))
                button.setMinimumHeight(46)
                row.addWidget(button)
            layout.addLayout(row)
        return frame
