"""Konsole widget: rolling log view of the Home Assistant logbook or system journal."""
from __future__ import annotations

import logging
import random
import subprocess
from datetime import datetime, timedelta, timezone

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QPlainTextEdit

from app.widgets.base import BaseWidget, PropertyDef

logger = logging.getLogger(__name__)


def _demo_log_line() -> str:
    """Generate one plausible fake log entry for demo mode."""
    now = datetime.now().strftime("%H:%M:%S")
    templates = [
        ("sensor.temperatur", "Wohnzimmer", lambda: f"{random.uniform(18, 26):.1f} C gemessen"),
        ("sensor.luftfeuchtigkeit", "Wohnzimmer", lambda: f"{random.randint(35, 65)} % gemessen"),
        ("light.wohnzimmer_deckenlampe", "", lambda: random.choice(["eingeschaltet", "ausgeschaltet", "Helligkeit auf 80% gesetzt"])),
        ("light.kueche_arbeitslicht", "", lambda: random.choice(["eingeschaltet", "ausgeschaltet"])),
        ("climate.wohnzimmer", "", lambda: f"Zieltemperatur auf {random.uniform(19, 23):.1f} C gesetzt"),
        ("switch.kaffeemaschine", "", lambda: random.choice(["eingeschaltet", "ausgeschaltet"])),
        ("cover.wohnzimmer_rollladen", "", lambda: random.choice(["geoeffnet", "geschlossen", "Position 60% gesetzt"])),
        ("media_player.wohnzimmer_tv", "", lambda: random.choice(["Wiedergabe gestartet", "Wiedergabe pausiert", "Lautstärke auf 70% gesetzt"])),
        ("binary_sensor.haustuer", "", lambda: random.choice(["Geoeffnet", "Geschlossen"])),
        ("websocket", "", lambda: random.choice(["Verbindung hergestellt", "Ping gesendet", "Reconnect nach Unterbrechung"])),
        ("automation.haus", "", lambda: random.choice(["getriggert", "Abgeschlossen", "Fehler: Sensor nicht erreichbar"])),
        ("sensor.energie_verbrauch", "Haus", lambda: f"{random.uniform(0.5, 3.5):.2f} kW gemessen"),
    ]
    entity, area, msg_fn = random.choice(templates)
    label = f"{entity} {area}".strip() if area else entity
    return f"{now}  {label}  {msg_fn()}"


class ConsoleWidget(BaseWidget):
    type_name = "console"
    display_name = "Konsole"
    category = "System"
    icon = "list"
    default_size = (380, 260)

    PROPERTY_SCHEMA = [
        PropertyDef("source", "Quelle", "select", "logbook", options=["logbook", "system"], group="Konfiguration"),
        PropertyDef("logbook_entity", "Logbuch-Entity (Filter)", "text", "", group="Konfiguration"),
        PropertyDef("refresh_seconds", "Aktualisierung (Sek.)", "number", 30, min=5, max=600, group="Konfiguration"),
        PropertyDef("max_lines", "Max. Zeilen", "number", 200, min=20, max=1000, group="Konfiguration"),
    ]

    def __init__(self, widget_id, config, state_manager=None, parent=None):
        self._console: QPlainTextEdit | None = None
        self._poll_timer: QTimer | None = None
        super().__init__(widget_id, config, state_manager, parent)

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._console = QPlainTextEdit()
        self._console.setReadOnly(True)
        font = QFont("monospace")
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        font.setPointSize(max(8, int(self.get_prop("font_size", 16)) - 4))
        self._console.setFont(font)
        self._console.setStyleSheet(
            "QPlainTextEdit { background-color: rgba(0,0,0,120); border: none;"
            f" color: {self.get_prop('text_color', '#FFFFFF')}; }}"
        )
        self._console.setMaximumBlockCount(int(self.get_prop("max_lines", 200)))
        self.content_layout.addWidget(self._console)
        self._start_polling()
        self._refresh_log()

    def refresh_from_state(self) -> None:
        self._refresh_log()

    def _start_polling(self) -> None:
        interval_s = max(5, int(self.get_prop("refresh_seconds", 30)))
        if self._poll_timer is None:
            self._poll_timer = QTimer(self)
            self._poll_timer.timeout.connect(self._refresh_log)
        self._poll_timer.start(interval_s * 1000)

    def _refresh_log(self) -> None:
        source = self.get_prop("source", "logbook")
        try:
            lines = self._fetch_system_lines() if source == "system" else self._fetch_logbook_lines()
        except Exception as exc:
            logger.exception("Konsole: refresh failed")
            lines = [f"{datetime.now():%H:%M:%S} FEHLER: {exc}"]
        if not lines:
            lines = ["(keine Eintraege)"]
        if self._console is not None:
            self._console.setPlainText("\n".join(lines))
            bar = self._console.verticalScrollBar()
            bar.setValue(bar.maximum())

    def _fetch_logbook_lines(self) -> list[str]:
        sm = self.state_manager
        if sm is None:
            return []
        if getattr(sm, "demo_mode", False) or getattr(sm, "client", None) is None:
            return [_demo_log_line() for _ in range(8)]
        start = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        entity_filter = str(self.get_prop("logbook_entity", "") or "").strip() or None
        entries = sm.client.get_logbook(start, entity_filter)
        lines: list[str] = []
        for entry in entries:
            raw_when = str(entry.get("when", ""))
            try:
                ts = datetime.fromisoformat(raw_when.replace("Z", "+00:00")).strftime("%H:%M:%S")
            except ValueError:
                ts = "??:??:??"
            who = entry.get("name") or entry.get("entity_id") or "?"
            message = entry.get("message") or f"-> {entry.get('state', '')}"
            lines.append(f"{ts}  {who}: {message}")
        return lines[-int(self.get_prop("max_lines", 200)):]

    def _fetch_system_lines(self) -> list[str]:
        count = int(self.get_prop("max_lines", 200))
        commands = (
            ["journalctl", "--user", "-u", "homepanel.service", "-n", str(count), "--no-pager"],
            ["journalctl", "-u", "homepanel.service", "-n", str(count), "--no-pager"],
        )
        for cmd in commands:
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if proc.returncode == 0 and proc.stdout.strip():
                    return proc.stdout.strip().splitlines()
            except (OSError, subprocess.TimeoutExpired):
                continue
        return [f"{datetime.now():%H:%M:%S} HINWEIS: journalctl nicht verfuegbar"]

    def hideEvent(self, event) -> None:
        if self._poll_timer is not None:
            self._poll_timer.stop()
        super().hideEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._poll_timer is not None and not self._poll_timer.isActive():
            self._start_polling()
            self._refresh_log()
