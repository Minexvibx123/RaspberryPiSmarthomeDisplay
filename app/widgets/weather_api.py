"""Weather widget - live forecast via the free, key-less Open-Meteo API.

Falls a Home Assistant setup ganz fehlt oder die weather-Entity nicht
verfuegbar ist, liefert dieses Widget aktuelle Daten und eine 3-Tage-Vorschau
direkt aus dem Internet. Kein API-Key noetig, nur Ort (Lat/Lon) einstellen.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from app.core.http_fetch import fetch
from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph

MINUTE = 60_000

WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("sun", "Klar"),
    1: ("sun", "Fast klar"),
    2: ("cloud", "Teilweise bewölkt"),
    3: ("cloud", "Bewölkt"),
    45: ("cloud", "Nebel"),
    48: ("cloud", "Reifnebel"),
    51: ("rain", "Leichte Nieselregen"),
    53: ("rain", "Nieselregen"),
    55: ("rain", "Starker Nieselregen"),
    61: ("rain", "Leichter Regen"),
    63: ("rain", "Regen"),
    65: ("rain", "Starker Regen"),
    66: ("rain", "Eisregen"),
    67: ("rain", "Starker Eisregen"),
    71: ("snow", "Leichter Schneefall"),
    73: ("snow", "Schneefall"),
    75: ("snow", "Starker Schneefall"),
    77: ("snow", "Schneekörner"),
    80: ("rain", "Regenschauer"),
    81: ("rain", "Regenschauer"),
    82: ("storm", "Kräftige Schauer"),
    85: ("snow", "Schneeschauer"),
    86: ("snow", "Starke Schneeschauer"),
    95: ("storm", "Gewitter"),
    96: ("storm", "Gewitter mit Hagel"),
    99: ("storm", "Gewitter mit Hagel"),
}

DOW_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def _lookup(code: int, day: bool = True) -> tuple[str, str]:
    icon, text = WMO_CODES.get(code, ("cloud", "Unbekannt"))
    if not day and code in (0, 1):
        return "night", "Klar"
    return icon, text


class WeatherApiWidget(BaseWidget):
    type_name = "weather_api"
    display_name = "Wetter (Open-Meteo)"
    category = "Anzeige"
    icon = "sun"
    default_size = (260, 220)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("city", "Ortsname", "text", "München", group="Quelle"),
        PropertyDef("latitude", "Breitengrad", "number", 48.137154, group="Quelle"),
        PropertyDef("longitude", "Längengrad", "number", 11.576124, group="Quelle"),
        PropertyDef("refresh_minutes", "Aktualisierung (Minuten)", "number", 15, min=5, max=240, group="Quelle"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.setAlignment(Qt.AlignCenter)

        accent = self.get_prop("accent_color", "#4C8DFF")
        text_color = self.get_prop("text_color", "#FFFFFF")
        font_size = int(self.get_prop("font_size", 16))

        self.city_label = QLabel(self.get_prop("city", "München"))
        self.city_label.setAlignment(Qt.AlignCenter)
        self.city_label.setStyleSheet(f"color: #AAAAAA; font-size: 13px; border: none; background: transparent;")

        self.icon_label = IconGlyph("sun", accent)
        icon_size = font_size + 28
        self.icon_label.setFixedSize(icon_size, icon_size)

        self.temp_label = QLabel("--°")
        self.temp_label.setAlignment(Qt.AlignCenter)
        self.temp_label.setStyleSheet(
            f"color: {accent}; font-size: {font_size + 16}px; font-weight: 800; border: none; background: transparent;"
        )

        current_row = QHBoxLayout()
        current_row.setSpacing(8)
        current_row.addStretch(1)
        current_row.addWidget(self.icon_label, alignment=Qt.AlignCenter)
        current_row.addWidget(self.temp_label, alignment=Qt.AlignCenter)
        current_row.addStretch(1)

        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet(f"color: {text_color}; font-size: 12px; border: none; background: transparent;")

        self.forecast_row = QHBoxLayout()
        self.forecast_row.setSpacing(6)
        self.forecast_cells = []

        self.content_layout.addWidget(self.city_label, alignment=Qt.AlignCenter)
        self.content_layout.addLayout(current_row)
        self.content_layout.addWidget(self.detail_label)
        self.content_layout.addStretch(1)
        self.content_layout.addLayout(self.forecast_row)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_remote)
        self._timer.start(max(5, int(self.get_prop("refresh_minutes", 15))) * MINUTE)

    def refresh_from_state(self) -> None:
        self._refresh_remote()

    def _refresh_remote(self) -> None:
        fetch(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": self.get_prop("latitude", 48.137154),
                "longitude": self.get_prop("longitude", 11.576124),
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,is_day",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "forecast_days": 4,
                "timezone": "auto",
                "wind_speed_unit": "kmh",
            },
            on_success=self._on_result,
            on_error=lambda _error: self.detail_label.setText("Wetter offline"),
            parent=self,
        )

    def _on_result(self, data: dict) -> None:
        try:
            current = data["current"]
            temp = current.get("temperature_2m")
            humidity = current.get("relative_humidity_2m")
            feels = current.get("apparent_temperature")
            wind = current.get("wind_speed_10m")
            icon, _text = _lookup(int(current.get("weather_code", 0)), bool(current.get("is_day", 1)))
            self.icon_label.set_icon(icon)
            self.temp_label.setText(f"{float(temp):.0f}°" if temp is not None else "--°")
            parts = []
            if feels is not None:
                parts.append(f"gefühlt {float(feels):.0f}°")
            if humidity is not None:
                parts.append(f"{int(humidity)} %")
            if wind is not None:
                parts.append(f"{float(wind):.0f} km/h")
            self.detail_label.setText("  ·  ".join(parts))
            self._update_forecast(data.get("daily", {}))
        except (KeyError, TypeError, ValueError):
            self.detail_label.setText("Keine Daten")

    def _update_forecast(self, daily: dict) -> None:
        while self.forecast_row.count():
            item = self.forecast_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        times = daily.get("time", []) or []
        codes = daily.get("weather_code", []) or []
        highs = daily.get("temperature_2m_max", []) or []
        lows = daily.get("temperature_2m_min", []) or []
        accent = self.get_prop("accent_color", "#4C8DFF")
        for index in range(1, 4):
            if index >= len(times):
                break
            column = QVBoxLayout()
            column.setSpacing(1)
            try:
                day = datetime.fromisoformat(times[index]).weekday()
            except (ValueError, TypeError):
                day = index
            dow = QLabel(DOW_DE[day])
            dow.setAlignment(Qt.AlignCenter)
            dow.setStyleSheet(f"color: #AAAAAA; font-size: 11px; border: none; background: transparent;")
            icon, _text = _lookup(int(codes[index] or 0))
            glyph = IconGlyph(icon, accent)
            glyph.setFixedSize(24, 24)
            temp = QLabel(
                f"{float(highs[index]):.0f}°/{float(lows[index]):.0f}°" if index < len(highs) and index < len(lows) else "--"
            )
            temp.setAlignment(Qt.AlignCenter)
            temp.setStyleSheet(f"color: #FFFFFF; font-size: 11px; font-weight: 600; border: none; background: transparent;")
            column.addWidget(dow, alignment=Qt.AlignCenter)
            column.addWidget(glyph, alignment=Qt.AlignCenter)
            column.addWidget(temp, alignment=Qt.AlignCenter)
            self.forecast_cells.append((dow, glyph, temp))
            self.forecast_row.addLayout(column)