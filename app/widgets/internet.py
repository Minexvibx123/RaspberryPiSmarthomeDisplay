"""Widgets that fetch live information from the internet directly (not via
Home Assistant). Each one polls a public API on a configurable interval
using the non-blocking app.core.http_fetch helper, so a slow/unreachable
service never freezes the panel - it just shows its last good value.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from app.core.http_fetch import fetch
from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph

MINUTE = 60_000


def _value_label(color: str, size: int, bold: bool = True) -> QLabel:
    label = QLabel("--")
    label.setAlignment(Qt.AlignCenter)
    label.setWordWrap(True)
    weight = 700 if bold else 400
    label.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: {weight}; border: none; background: transparent;")
    return label


class CryptoPriceWidget(BaseWidget):
    """Live crypto price via the free, key-less CoinGecko API."""

    type_name = "crypto_price"
    display_name = "Kryptokurs"
    category = "Internet"
    icon = "coin"
    default_size = (200, 140)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("coin_id", "Coin (CoinGecko-ID)", "text", "bitcoin", group="Quelle"),
        PropertyDef("vs_currency", "Währung", "text", "eur", group="Quelle"),
        PropertyDef("refresh_minutes", "Aktualisierung (Minuten)", "number", 10, min=1, max=120, group="Quelle"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.icon_label = IconGlyph("coin", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(36, 36)
        self.name_label = QLabel((self.get_prop("coin_id", "bitcoin") or "").capitalize())
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: 13px; border: none; background: transparent;")
        self.value_label = _value_label(self.get_prop("accent_color", "#4C8DFF"), int(self.get_prop("font_size", 16)) + 10)
        for w in (self.icon_label, self.name_label, self.value_label):
            self.content_layout.addWidget(w, alignment=Qt.AlignCenter)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_remote)
        self._timer.start(max(1, int(self.get_prop("refresh_minutes", 10))) * MINUTE)

    def refresh_from_state(self) -> None:
        self._refresh_remote()

    def _refresh_remote(self) -> None:
        coin = self.get_prop("coin_id", "bitcoin")
        currency = self.get_prop("vs_currency", "eur")
        fetch(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin, "vs_currencies": currency},
            on_success=self._on_result,
            on_error=lambda _err: self.value_label.setText("Offline"),
            parent=self,
        )

    def _on_result(self, data: dict) -> None:
        coin = self.get_prop("coin_id", "bitcoin")
        currency = self.get_prop("vs_currency", "eur")
        try:
            price = data[coin][currency]
            self.value_label.setText(f"{price:,.2f} {currency.upper()}")
        except (KeyError, TypeError):
            self.value_label.setText("--")


class StockPriceWidget(BaseWidget):
    """Stock price via Alpha Vantage (requires a free API key from the user)."""

    type_name = "stock_price"
    display_name = "Aktienkurs"
    category = "Internet"
    icon = "chart"
    default_size = (200, 140)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("symbol", "Symbol (z. B. AAPL)", "text", "AAPL", group="Quelle"),
        PropertyDef("api_key", "Alpha Vantage API-Key", "text", "", group="Quelle"),
        PropertyDef("refresh_minutes", "Aktualisierung (Minuten)", "number", 30, min=5, max=240, group="Quelle"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.icon_label = IconGlyph("chart", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(36, 36)
        self.name_label = QLabel(self.get_prop("symbol", "AAPL"))
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: 13px; border: none; background: transparent;")
        self.value_label = _value_label(self.get_prop("accent_color", "#4C8DFF"), int(self.get_prop("font_size", 16)) + 10)
        for w in (self.icon_label, self.name_label, self.value_label):
            self.content_layout.addWidget(w, alignment=Qt.AlignCenter)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_remote)
        self._timer.start(max(5, int(self.get_prop("refresh_minutes", 30))) * MINUTE)

    def refresh_from_state(self) -> None:
        if self.get_prop("api_key"):
            self._refresh_remote()
        else:
            self.value_label.setText("Kein API-Key")

    def _refresh_remote(self) -> None:
        key = self.get_prop("api_key")
        if not key:
            self.value_label.setText("Kein API-Key")
            return
        fetch(
            "https://www.alphavantage.co/query",
            params={"function": "GLOBAL_QUOTE", "symbol": self.get_prop("symbol", "AAPL"), "apikey": key},
            on_success=self._on_result,
            on_error=lambda _err: self.value_label.setText("Offline"),
            parent=self,
        )

    def _on_result(self, data: dict) -> None:
        try:
            price = float(data["Global Quote"]["05. price"])
            self.value_label.setText(f"{price:,.2f}")
        except (KeyError, TypeError, ValueError):
            self.value_label.setText("--")


class CurrencyWidget(BaseWidget):
    """Currency exchange rate via the free, key-less frankfurter.app API."""

    type_name = "currency"
    display_name = "Wechselkurs"
    category = "Internet"
    icon = "currency"
    default_size = (200, 140)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("from_currency", "Von", "text", "EUR", group="Quelle"),
        PropertyDef("to_currency", "Nach", "text", "USD", group="Quelle"),
        PropertyDef("refresh_minutes", "Aktualisierung (Minuten)", "number", 60, min=5, max=1440, group="Quelle"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.icon_label = IconGlyph("currency", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(36, 36)
        self.pair_label = QLabel(f"{self.get_prop('from_currency', 'EUR')} → {self.get_prop('to_currency', 'USD')}")
        self.pair_label.setAlignment(Qt.AlignCenter)
        self.pair_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: 13px; border: none; background: transparent;")
        self.value_label = _value_label(self.get_prop("accent_color", "#4C8DFF"), int(self.get_prop("font_size", 16)) + 10)
        for w in (self.icon_label, self.pair_label, self.value_label):
            self.content_layout.addWidget(w, alignment=Qt.AlignCenter)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_remote)
        self._timer.start(max(5, int(self.get_prop("refresh_minutes", 60))) * MINUTE)

    def refresh_from_state(self) -> None:
        self._refresh_remote()

    def _refresh_remote(self) -> None:
        fetch(
            "https://api.frankfurter.app/latest",
            params={"from": self.get_prop("from_currency", "EUR"), "to": self.get_prop("to_currency", "USD")},
            on_success=self._on_result,
            on_error=lambda _err: self.value_label.setText("Offline"),
            parent=self,
        )

    def _on_result(self, data: dict) -> None:
        try:
            to_cur = self.get_prop("to_currency", "USD")
            rate = data["rates"][to_cur]
            self.value_label.setText(f"1 {data['base']} = {rate:.4f} {to_cur}")
        except (KeyError, TypeError):
            self.value_label.setText("--")


class QuoteWidget(BaseWidget):
    """Random inspirational quote via the free quotable.io API."""

    type_name = "quote"
    display_name = "Zitat des Tages"
    category = "Internet"
    icon = "quote"
    default_size = (260, 160)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("refresh_minutes", "Aktualisierung (Minuten)", "number", 360, min=15, max=1440, group="Quelle"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.text_label = QLabel("\u201e\u2026\u201c")
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-style: italic; border: none; background: transparent;")
        self.author_label = QLabel("")
        self.author_label.setAlignment(Qt.AlignCenter)
        self.author_label.setStyleSheet(f"color: {self.get_prop('accent_color', '#4C8DFF')}; font-size: 12px; border: none; background: transparent;")
        self.content_layout.addWidget(self.text_label, 1)
        self.content_layout.addWidget(self.author_label)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_remote)
        self._timer.start(max(15, int(self.get_prop("refresh_minutes", 360))) * MINUTE)

    def refresh_from_state(self) -> None:
        self._refresh_remote()

    def _refresh_remote(self) -> None:
        fetch("https://api.quotable.io/random", on_success=self._on_result, on_error=lambda _e: None, parent=self)

    def _on_result(self, data: dict) -> None:
        content = data.get("content")
        author = data.get("author")
        if content:
            self.text_label.setText(f"„{content}“")
            self.author_label.setText(f"— {author}" if author else "")


class JokeWidget(BaseWidget):
    """Random joke via the free official-joke-api."""

    type_name = "joke"
    display_name = "Witz des Tages"
    category = "Internet"
    icon = "smile"
    default_size = (260, 160)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("refresh_minutes", "Aktualisierung (Minuten)", "number", 360, min=15, max=1440, group="Quelle"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.setup_label = QLabel("…")
        self.setup_label.setWordWrap(True)
        self.setup_label.setAlignment(Qt.AlignCenter)
        self.setup_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 600; border: none; background: transparent;")
        self.punchline_label = QLabel("")
        self.punchline_label.setWordWrap(True)
        self.punchline_label.setAlignment(Qt.AlignCenter)
        self.punchline_label.setStyleSheet(f"color: {self.get_prop('accent_color', '#4C8DFF')}; font-size: {self.get_prop('font_size', 16)}px; border: none; background: transparent;")
        self.content_layout.addWidget(self.setup_label, 1)
        self.content_layout.addWidget(self.punchline_label, 1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_remote)
        self._timer.start(max(15, int(self.get_prop("refresh_minutes", 360))) * MINUTE)

    def refresh_from_state(self) -> None:
        self._refresh_remote()

    def _refresh_remote(self) -> None:
        fetch("https://official-joke-api.appspot.com/random_joke", on_success=self._on_result, on_error=lambda _e: None, parent=self)

    def _on_result(self, data: dict) -> None:
        self.setup_label.setText(data.get("setup", ""))
        self.punchline_label.setText(data.get("punchline", ""))


class HolidayWidget(BaseWidget):
    """Next public holiday via the free date.nager.at API."""

    type_name = "holiday"
    display_name = "Nächster Feiertag"
    category = "Internet"
    icon = "holiday"
    default_size = (240, 140)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("country_code", "Ländercode (z. B. DE, AT, CH)", "text", "DE", group="Quelle"),
        PropertyDef("refresh_minutes", "Aktualisierung (Minuten)", "number", 720, min=60, max=2880, group="Quelle"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.icon_label = IconGlyph("holiday", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(36, 36)
        self.name_label = _value_label(self.get_prop("text_color", "#FFFFFF"), self.get_prop("font_size", 16), bold=True)
        self.date_label = _value_label(self.get_prop("accent_color", "#4C8DFF"), int(self.get_prop("font_size", 16)) - 2, bold=False)
        for w in (self.icon_label, self.name_label, self.date_label):
            self.content_layout.addWidget(w, alignment=Qt.AlignCenter)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_remote)
        self._timer.start(max(60, int(self.get_prop("refresh_minutes", 720))) * MINUTE)

    def refresh_from_state(self) -> None:
        self._refresh_remote()

    def _refresh_remote(self) -> None:
        import datetime
        year = datetime.date.today().year
        country = self.get_prop("country_code", "DE")
        fetch(
            f"https://date.nager.at/api/v3/NextPublicHolidays/{country}",
            on_success=self._on_result,
            on_error=lambda _err: self.name_label.setText("Offline"),
            parent=self,
        )

    def _on_result(self, data) -> None:
        if not data:
            self.name_label.setText("Keine Daten")
            return
        first = data[0]
        self.name_label.setText(first.get("localName", "?"))
        self.date_label.setText(first.get("date", ""))


class InternetStatusWidget(BaseWidget):
    """Shows whether the panel currently has a working internet connection."""

    type_name = "internet_status"
    display_name = "Internet-Status"
    category = "Internet"
    icon = "wifi"
    default_size = (200, 120)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("check_url", "Prüf-URL", "text", "https://1.1.1.1", group="Quelle"),
        PropertyDef("refresh_minutes", "Prüfintervall (Minuten)", "number", 2, min=1, max=60, group="Quelle"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.icon_label = IconGlyph("wifi", "#777777")
        self.icon_label.setFixedSize(40, 40)
        self.state_label = _value_label("#777777", self.get_prop("font_size", 16))
        for w in (self.icon_label, self.state_label):
            self.content_layout.addWidget(w, alignment=Qt.AlignCenter)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_remote)
        self._timer.start(max(1, int(self.get_prop("refresh_minutes", 2))) * MINUTE)

    def refresh_from_state(self) -> None:
        self._refresh_remote()

    def _refresh_remote(self) -> None:
        fetch(
            self.get_prop("check_url", "https://1.1.1.1"),
            on_success=lambda _d: self._set_status(True),
            on_error=lambda _e: self._set_status(False),
            as_json=False,
            parent=self,
        )

    def _set_status(self, online: bool) -> None:
        color = self.get_prop("accent_color", "#4C8DFF") if online else "#E05555"
        self.icon_label.set_color(color)
        self.state_label.setStyleSheet(f"color: {color}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 700; border: none; background: transparent;")
        self.state_label.setText("Online" if online else "Offline")
        self.set_active(online)


class SystemMonitorWidget(BaseWidget):
    """CPU load, temperature and RAM usage of the Raspberry Pi itself."""

    type_name = "system_monitor"
    display_name = "System-Monitor"
    category = "System"
    icon = "cpu"
    default_size = (220, 160)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("refresh_seconds", "Aktualisierung (Sekunden)", "number", 10, min=2, max=120, group="Verhalten"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        header_row = QVBoxLayout()
        self.icon_label = IconGlyph("cpu", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(32, 32)
        self.cpu_label = _value_label(self.get_prop("text_color", "#FFFFFF"), self.get_prop("font_size", 16))
        self.ram_label = _value_label(self.get_prop("text_color", "#FFFFFF"), self.get_prop("font_size", 16))
        self.temp_label = _value_label(self.get_prop("accent_color", "#4C8DFF"), self.get_prop("font_size", 16))
        for w in (self.icon_label, self.cpu_label, self.ram_label, self.temp_label):
            self.content_layout.addWidget(w, alignment=Qt.AlignCenter)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_from_state)
        self._timer.start(max(2, int(self.get_prop("refresh_seconds", 10))) * 1000)

    def refresh_from_state(self) -> None:
        cpu_percent = self._read_cpu_percent()
        ram_percent = self._read_ram_percent()
        temp_c = self._read_cpu_temp()
        self.cpu_label.setText(f"CPU: {cpu_percent}" if cpu_percent is not None else "CPU: --")
        self.ram_label.setText(f"RAM: {ram_percent}" if ram_percent is not None else "RAM: --")
        self.temp_label.setText(f"{temp_c:.1f}°C" if temp_c is not None else "--°C")

    @staticmethod
    def _read_cpu_percent() -> str | None:
        try:
            import psutil
            return f"{psutil.cpu_percent(interval=None):.0f}%"
        except Exception:
            return None

    @staticmethod
    def _read_ram_percent() -> str | None:
        try:
            import psutil
            return f"{psutil.virtual_memory().percent:.0f}%"
        except Exception:
            return None

    @staticmethod
    def _read_cpu_temp() -> float | None:
        try:
            path = Path("/sys/class/thermal/thermal_zone0/temp")
            if path.exists():
                return int(path.read_text().strip()) / 1000.0
        except Exception:
            pass
        return None


class NewsWidget(BaseWidget):
    """Latest headlines from an arbitrary RSS feed."""

    type_name = "news"
    display_name = "News-Feed"
    category = "Internet"
    icon = "list"
    default_size = (280, 220)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("feed_url", "RSS-Feed-URL", "text", "https://www.tagesschau.de/xml/rss2/", group="Quelle"),
        PropertyDef("max_items", "Max. Schlagzeilen", "number", 5, min=1, max=15, group="Quelle"),
        PropertyDef("refresh_minutes", "Aktualisierung (Minuten)", "number", 20, min=5, max=240, group="Quelle"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(6)
        self.scroll.setWidget(self.list_container)
        self.content_layout.addWidget(self.scroll)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_remote)
        self._timer.start(max(5, int(self.get_prop("refresh_minutes", 20))) * MINUTE)

    def refresh_from_state(self) -> None:
        self._refresh_remote()

    def _refresh_remote(self) -> None:
        fetch(
            self.get_prop("feed_url", "https://www.tagesschau.de/xml/rss2/"),
            on_success=self._on_result,
            on_error=lambda _e: None,
            as_json=False,
            parent=self,
        )

    def _on_result(self, xml_text: str) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        try:
            root = ET.fromstring(xml_text)
            titles = [el.text for el in root.iter("title") if el.text][1:]  # skip channel title
        except ET.ParseError:
            titles = []
        max_items = int(self.get_prop("max_items", 5))
        for title in titles[:max_items]:
            label = QLabel(f"•  {title}")
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: 13px; border: none; background: transparent;")
            self.list_layout.addWidget(label)
        self.list_layout.addStretch()
