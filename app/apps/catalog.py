"""One catalogue for bundled apps, plugin apps and apps installed from repositories."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Signal

from app.apps import games, home, internet, tools
from app.apps.kit import AppContext

REPO_MARKER = ".homepanel-repo"
CATEGORIES = ["Smart Home", "Werkzeuge", "Familie & Spiele", "Internet", "Erweiterungen"]


@dataclass(frozen=True)
class BuiltinApp:
    id: str
    name: str
    description: str
    category: str
    icon: str
    factory: Callable[[AppContext], object]
    default: bool = False


@dataclass
class AppEntry:
    id: str
    name: str
    description: str
    category: str
    icon: str
    version: str
    author: str
    source: str  # builtin | plugin | repo
    installed: bool
    error: str = ""

    @property
    def removable(self) -> bool:
        return self.source == "repo"


def _board(key: str, name: str, description: str, icon: str, default: bool = False) -> BuiltinApp:
    return BuiltinApp(f"board_{key}", name, description, "Smart Home", icon, home.board_factory(key), default)


BUILTIN_APPS: list[BuiltinApp] = [
    _board("lights", "Lichter", "Alle Lampen und Lichtschalter mit An, Aus und Dimmen.", "bulb", True),
    _board("switches", "Schalter", "Steckdosen und Schalter aus Home Assistant.", "power"),
    _board("scenes", "Szenen & Skripte", "Szenen und Skripte mit einem Tipp starten.", "scene", True),
    _board("climate", "Heizung & Klima", "Solltemperatur einstellen und Geräte schalten.", "thermometer", True),
    _board("covers", "Rollläden", "Rollläden öffnen, stoppen und schließen.", "blinds", True),
    _board("automations", "Automationen", "Automationen ein- und ausschalten oder auslösen.", "gear"),
    _board("batteries", "Batterien", "Ladestand aller Batteriesensoren, schwächste zuerst.", "battery"),
    _board("presence", "Anwesenheit", "Wer ist zuhause? Personen und Geräte.", "person"),
    _board("security", "Sicherheit", "Türen, Fenster, Rauch, Wasser, Schlösser und Alarm.", "shield", True),
    _board("consumers", "Verbraucher", "Welche Geräte verbrauchen gerade am meisten Strom?", "flash"),
    _board("temperatures", "Temperaturen", "Alle Temperatursensoren auf einen Blick.", "thermometer"),
    BuiltinApp("logbook", "Verlauf", "Letzte Ereignisse aus dem Home-Assistant-Logbuch.", "Smart Home", "list", internet.logbook),
    BuiltinApp("calculator", "Rechner", "Taschenrechner mit Klammern und Potenzen.", "Werkzeuge", "gauge", tools.calculator, True),
    BuiltinApp("notes", "Notizen", "Gemeinsamer Notizzettel, wird automatisch gespeichert.", "Werkzeuge", "list", tools.notes, True),
    BuiltinApp("stopwatch_timer", "Timer & Stoppuhr", "Küchentimer und Stoppuhr mit Runden.", "Werkzeuge", "clock", tools.stopwatch_timer, True),
    BuiltinApp("world_clock", "Weltuhr", "Uhrzeiten in zehn Städten der Welt.", "Werkzeuge", "clock", tools.world_clock),
    BuiltinApp("calendar_notes", "Kalender", "Monatskalender mit Notizen pro Tag.", "Werkzeuge", "calendar", tools.calendar_app),
    BuiltinApp("unit_converter", "Umrechner", "Länge, Gewicht, Volumen, Temperatur und mehr.", "Werkzeuge", "gauge", tools.unit_converter),
    BuiltinApp("dice", "Würfel & Zufall", "Würfel, Münze und Entscheidungshilfe.", "Familie & Spiele", "star", tools.dice),
    BuiltinApp("paint", "Zeichenbrett", "Mit dem Finger malen, in Farben und Strichstärken.", "Familie & Spiele", "smile", tools.paint),
    BuiltinApp("lists", "Listen", "Einkaufs- und Aufgabenliste zum Abhaken.", "Werkzeuge", "list", tools.lists, True),
    BuiltinApp("pomodoro", "Fokus-Timer", "Pomodoro: 25 Minuten Fokus, dann Pause.", "Werkzeuge", "clock", tools.pomodoro),
    BuiltinApp("cleaning", "Display reinigen", "Einfarbige Fläche zum Putzen, auch als Taschenlampe.", "Werkzeuge", "sun", tools.cleaning),
    BuiltinApp("photo_frame", "Fotorahmen", "Diashow aus einem Bilderordner.", "Familie & Spiele", "camera", tools.photo_frame),
    BuiltinApp("counters", "Zähler", "Beliebige Strichlisten und Zähler.", "Werkzeuge", "list", tools.counters),
    BuiltinApp("tictactoe", "Tic-Tac-Toe", "Gegen den Computer oder zu zweit.", "Familie & Spiele", "star", games.tictactoe),
    BuiltinApp("memory", "Memory", "Finde alle Kartenpaare in möglichst wenigen Zügen.", "Familie & Spiele", "smile", games.memory),
    BuiltinApp("weather", "Wetter", "Aktuelles Wetter und 7-Tage-Vorhersage für jeden Ort.", "Internet", "cloud", internet.weather, True),
    BuiltinApp("news", "Nachrichten", "Schlagzeilen von Tagesschau und Spiegel.", "Internet", "quote", internet.news),
    BuiltinApp("network_scan", "Netzwerk-Scanner", "Aktive Geräte im Heimnetz finden (nur Ping).", "Internet", "wifi", internet.network_scan),
]
_BUILTIN_BY_ID = {app.id: app for app in BUILTIN_APPS}


class AppCatalog(QObject):
    changed = Signal()

    def __init__(self, db, plugin_manager, state_manager=None, parent=None):
        super().__init__(parent)
        self.db, self.plugin_manager, self.state_manager = db, plugin_manager, state_manager

    def _flag(self, app_id: str) -> str:
        return f"app.installed.{app_id}"

    def entries(self) -> list[AppEntry]:
        result = []
        for app in BUILTIN_APPS:
            installed = bool(self.db.get_setting(self._flag(app.id), app.default))
            result.append(AppEntry(app.id, app.name, app.description, app.category, app.icon,
                                   "1.0.0", "HomePanel", "builtin", installed))
        for info in self.plugin_manager.list_plugins():
            from_repo = (Path(info.plugin_dir) / REPO_MARKER).is_file()
            if info.category != "apps" and not from_repo:
                continue
            result.append(AppEntry(
                info.id, info.name, info.description, "Erweiterungen", "gear", info.version,
                info.author or "Unbekannt", "repo" if from_repo else "plugin",
                info.state in ("enabled", "error"), info.error or "",
            ))
        return result

    def installed(self) -> list[AppEntry]:
        return [entry for entry in self.entries() if entry.installed]

    def get(self, app_id: str) -> AppEntry | None:
        return next((entry for entry in self.entries() if entry.id == app_id), None)

    def install(self, app_id: str) -> bool:
        if app_id in _BUILTIN_BY_ID:
            self.db.set_setting(self._flag(app_id), True)
            ok = True
        else:
            ok = self.plugin_manager.enable(app_id)
        self.changed.emit()
        return ok

    def remove(self, app_id: str) -> bool:
        if app_id in _BUILTIN_BY_ID:
            self.db.set_setting(self._flag(app_id), False)
        else:
            self.plugin_manager.disable(app_id)
        self.changed.emit()
        return True

    def create_view(self, app_id: str, parent=None):
        builtin = _BUILTIN_BY_ID.get(app_id)
        if builtin is not None:
            view = builtin.factory(AppContext(self.db, self.state_manager, app_id))
            if parent is not None:
                view.setParent(parent)
            return view
        plugin = self.plugin_manager.get_instance(app_id)
        return plugin.create_app_view(parent) if plugin else None
