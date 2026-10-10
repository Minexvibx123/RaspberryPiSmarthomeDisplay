"""Apps that use the internet or the network; all requests run in background threads."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html import unescape
import re

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QWidget,
)

from app.apps.kit import AppContext, AppPage, big_button, card
from app.core.http_fetch import fetch

_WEATHER = {0: "Klar", 1: "Überwiegend klar", 2: "Teils bewölkt", 3: "Bedeckt", 45: "Nebel", 48: "Reifnebel",
            51: "Leichter Niesel", 53: "Niesel", 55: "Starker Niesel", 61: "Leichter Regen", 63: "Regen",
            65: "Starker Regen", 66: "Gefrierender Regen", 67: "Gefrierender Regen", 71: "Leichter Schnee",
            73: "Schnee", 75: "Starker Schnee", 77: "Schneegriesel", 80: "Schauer", 81: "Kräftige Schauer",
            82: "Starkregen", 85: "Schneeschauer", 86: "Starke Schneeschauer", 95: "Gewitter",
            96: "Gewitter mit Hagel", 99: "Schweres Gewitter"}


def _home_location(ctx: AppContext) -> tuple[float, float, str]:
    if ctx.load("lat") is not None:
        return float(ctx.load("lat")), float(ctx.load("lon")), ctx.load("place", "Eigener Ort")
    zone = ctx.state_manager.get_entity("zone.home") if ctx.state_manager else None
    if zone and zone.attributes.get("latitude") is not None:
        return float(zone.attributes["latitude"]), float(zone.attributes["longitude"]), "Zuhause"
    return 52.52, 13.405, "Berlin"


def weather(ctx: AppContext) -> QWidget:
    page = AppPage("Wetter")
    search = QLineEdit()
    search.setPlaceholderText("Ort suchen und Enter drücken")
    status, now, forecast = QLabel("Lade Wetter …"), QLabel(), QGridLayout()
    now.setStyleSheet("font-size: 34px; font-weight: 800;")
    forecast.setSpacing(10)

    def show(data: dict, place: str) -> None:
        current, daily = data.get("current", {}), data.get("daily", {})
        status.setText(place)
        text = _WEATHER.get(current.get("weather_code"), "–")
        now.setText(f"{current.get('temperature_2m', '–')} °C · {text}\n"
                    f"gefühlt {current.get('apparent_temperature', '–')} °C · Wind {current.get('wind_speed_10m', '–')} km/h"
                    f" · Feuchte {current.get('relative_humidity_2m', '–')} %")
        while forecast.count():
            item = forecast.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for index, day in enumerate(daily.get("time", [])[:7]):
            frame, layout = card()
            name = datetime.fromisoformat(day).strftime("%a %d.%m.")
            for line, style in ((name, "font-weight: 700;"),
                                (_WEATHER.get(daily["weather_code"][index], "–"), ""),
                                (f"{daily['temperature_2m_max'][index]:.0f}° / {daily['temperature_2m_min'][index]:.0f}°",
                                 "font-size: 18px; font-weight: 800;"),
                                (f"Regen {daily['precipitation_sum'][index]:.1f} mm", "")):
                label = QLabel(line)
                label.setStyleSheet(style)
                label.setWordWrap(True)
                layout.addWidget(label)
            forecast.addWidget(frame, 0, index)

    def load() -> None:
        lat, lon, place = _home_location(ctx)
        status.setText("Lade Wetter …")
        fetch("https://api.open-meteo.com/v1/forecast", lambda data: show(data, place),
              lambda error: status.setText(f"Wetter nicht verfügbar: {error}"), params={
                  "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 7,
                  "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
                  "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"}, parent=page)

    def find_place() -> None:
        name = search.text().strip()
        if not name:
            return

        def found(data: dict) -> None:
            results = data.get("results") or []
            if not results:
                status.setText("Ort nicht gefunden.")
                return
            first = results[0]
            ctx.save("lat", first["latitude"])
            ctx.save("lon", first["longitude"])
            ctx.save("place", f"{first['name']}, {first.get('country', '')}")
            load()

        fetch("https://geocoding-api.open-meteo.com/v1/search", found, lambda e: status.setText(f"Suche fehlgeschlagen: {e}"),
              params={"name": name, "count": 1, "language": "de"}, parent=page)

    search.returnPressed.connect(find_place)
    page.root.addWidget(search)
    page.root.addWidget(status)
    page.root.addWidget(now)
    page.root.addLayout(forecast)
    page.root.addStretch(1)
    page.root.addWidget(big_button("Aktualisieren", load, "primary"))
    load()
    return page


FEEDS = {"Tagesschau": "https://www.tagesschau.de/index~rss2.xml",
         "Spiegel": "https://www.spiegel.de/schlagzeilen/index.rss"}


def parse_feed(text: str) -> list[dict]:
    """Parse an RSS 2.0 feed; DTDs/entities are rejected to rule out entity expansion attacks."""
    lowered = text[:4000].lower()
    if "<!doctype" in lowered or "<!entity" in lowered or len(text) > 2_000_000:
        raise ValueError("Feed abgelehnt")
    root = ET.fromstring(text)
    items = []
    for item in root.iter("item"):
        summary = re.sub(r"<[^>]+>", "", unescape(item.findtext("description", "")))
        items.append({"title": item.findtext("title", "").strip(), "summary": summary.strip(),
                      "date": item.findtext("pubDate", "")[:22]})
    return items[:60]


def news(ctx: AppContext) -> QWidget:
    page = AppPage("Nachrichten")
    source, status, headlines, detail = QComboBox(), QLabel(), QListWidget(), QPlainTextEdit()
    detail.setReadOnly(True)
    detail.setMaximumHeight(130)
    source.addItems(list(FEEDS))
    items: list[dict] = []

    def show(text: str) -> None:
        try:
            items[:] = parse_feed(text)
        except (ET.ParseError, ValueError):
            status.setText("Der Feed konnte nicht gelesen werden.")
            return
        status.setText(f"{len(items)} Meldungen")
        headlines.clear()
        for item in items:
            headlines.addItem(QListWidgetItem(f"{item['title']}"))

    def load() -> None:
        status.setText("Lade …")
        fetch(FEEDS[source.currentText()], show, lambda e: status.setText(f"Fehler: {e}"), as_json=False, parent=page)

    headlines.currentRowChanged.connect(lambda row: detail.setPlainText(
        f"{items[row]['date']}\n\n{items[row]['summary']}" if 0 <= row < len(items) else ""))
    source.currentTextChanged.connect(lambda _text: load())
    page.root.addWidget(source)
    page.root.addWidget(status)
    page.root.addWidget(headlines, 1)
    page.root.addWidget(detail)
    page.root.addWidget(big_button("Aktualisieren", load, "primary"))
    load()
    return page


class _Scan(QThread):
    done, failed = Signal(object), Signal(str)

    def __init__(self, cidr: str):
        super().__init__()
        self.cidr = cidr

    def run(self) -> None:
        try:
            from plugins.network.api import NetworkMonitor
            self.done.emit(NetworkMonitor().discover(self.cidr or None))
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            self.failed.emit(str(exc))


_SCANS: set[QThread] = set()


def network_scan(ctx: AppContext) -> QWidget:
    page = AppPage("Netzwerk-Scanner")
    note = QLabel("Sendet je Gerät einen Ping im eigenen privaten Netz (max. /24). Es werden keine Ports geprüft.")
    note.setWordWrap(True)
    cidr = QLineEdit(ctx.load("cidr", ""))
    cidr.setPlaceholderText("Automatisch (z. B. 192.168.1.0/24)")
    table = QTableWidget(0, 3)
    table.setHorizontalHeaderLabels(["Adresse", "Name", "Antwortzeit"])
    table.horizontalHeader().setStretchLastSection(True)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    status = QLabel()
    start = big_button("Netzwerk durchsuchen", lambda: run(), "primary")

    def finished(devices: list) -> None:
        start.setEnabled(True)
        status.setText(f"{len(devices)} aktive Geräte gefunden")
        table.setRowCount(len(devices))
        for row, device in enumerate(devices):
            ms = device.get("response_ms")
            for column, text in enumerate((device["host"], device.get("name") or "–", f"{ms:.0f} ms" if ms is not None else "–")):
                table.setItem(row, column, QTableWidgetItem(text))

    def failed(message: str) -> None:
        start.setEnabled(True)
        status.setText(message)

    def run() -> None:
        ctx.save("cidr", cidr.text().strip())
        start.setEnabled(False)
        status.setText("Suche läuft …")
        job = _Scan(cidr.text().strip())
        _SCANS.add(job)
        job.done.connect(finished)
        job.failed.connect(failed)
        job.finished.connect(lambda j=job: _SCANS.discard(j))
        job.start()

    for widget in (note, cidr, start, status):
        page.root.addWidget(widget)
    page.root.addWidget(table, 1)
    return page


def logbook(ctx: AppContext) -> QWidget:
    page = AppPage("Verlauf")
    status, table = QLabel(), QTableWidget(0, 3)
    table.setHorizontalHeaderLabels(["Zeit", "Gerät", "Ereignis"])
    table.horizontalHeader().setStretchLastSection(True)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    hours = QComboBox()
    hours.addItems(["1", "6", "24"])
    hours.setCurrentText("6")

    def show(entries: list) -> None:
        entries = [e for e in entries if e.get("name")][::-1][:150]
        status.setText(f"{len(entries)} Ereignisse")
        table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            when = datetime.fromisoformat(entry["when"].replace("Z", "+00:00")).astimezone().strftime("%d.%m. %H:%M:%S")
            what = entry.get("message") or entry.get("state", "")
            for column, text in enumerate((when, entry["name"], str(what))):
                table.setItem(row, column, QTableWidgetItem(text))

    def load() -> None:
        settings = getattr(ctx.state_manager, "settings", None)
        if not settings or not settings.ha_url or ctx.state_manager.demo_mode:
            status.setText("Der Verlauf braucht eine Verbindung zu Home Assistant.")
            return
        start = (datetime.now(timezone.utc) - timedelta(hours=int(hours.currentText()))).isoformat()
        status.setText("Lade …")
        fetch(f"{settings.ha_url}/api/logbook/{start}", show, lambda e: status.setText(f"Fehler: {e}"),
              headers={"Authorization": f"Bearer {settings.ha_token}"}, parent=page)

    row = QHBoxLayout()
    row.addWidget(QLabel("Zeitraum (Stunden):"))
    row.addWidget(hours)
    row.addWidget(big_button("Aktualisieren", load, "primary"))
    page.root.addLayout(row)
    page.root.addWidget(status)
    page.root.addWidget(table, 1)
    load()
    return page
