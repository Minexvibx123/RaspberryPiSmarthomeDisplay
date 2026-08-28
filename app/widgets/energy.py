"""Energie-Übersichts-Widget: Leistung, Tagesverbrauch, Kosten, Sparkline."""
from __future__ import annotations

import time
from collections import deque
from typing import Any

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel

from app.widgets.base import BaseWidget, PropertyDef


class EnergyWidget(BaseWidget):
    type_name = "energy"
    display_name = "Energie"
    category = "Anzeige"
    icon = "bolt"
    default_size = (360, 220)

    PROPERTY_SCHEMA = [
        PropertyDef(
            "power_entity", "Leistungs-Sensor", "entity", "",
            entity_domains=["sensor"], group="Daten",
        ),
        PropertyDef(
            "energy_today_entity", "Verbrauch heute (kWh)", "entity", "",
            entity_domains=["sensor"], group="Daten",
        ),
        PropertyDef(
            "price_per_kwh", "Preis pro kWh (€)", "number", 0.0,
            min=0, max=5, group="Daten",
        ),
        PropertyDef(
            "graph_minutes", "Verlauf (Minuten)", "number", 60,
            min=5, max=720, group="Darstellung",
        ),
        PropertyDef(
            "show_graph", "Verlauf anzeigen", "bool", True,
            group="Darstellung",
        ),
    ]

    def __init__(self, widget_id: int, config: dict, state_manager=None, parent=None):
        self._history: deque[tuple[float, float]] = deque()
        self._last_redraw: float = 0.0
        self._throttle_ms: int = 1000
        super().__init__(widget_id, config, state_manager, parent)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        fs = int(self.get_prop("font_size", 16))

        self.power_label = QLabel("–")
        self.power_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.power_label.setStyleSheet(
            f"color: {self.get_prop('accent_color', '#4C8DFF')}; "
            f"font-size: {fs + 18}px; font-weight: 700; "
            f"border: none; background: transparent;"
        )

        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; "
            f"font-size: {fs}px; border: none; background: transparent;"
        )

        self.hint_label = QLabel("Sensor nicht konfiguriert")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; "
            f"font-size: {max(fs - 4, 9)}px; opacity: 0.45; "
            f"border: none; background: transparent;"
        )
        self.hint_label.hide()

        self.content_layout.addWidget(self.power_label)
        self.content_layout.addWidget(self.detail_label)
        self.content_layout.addWidget(self.hint_label)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    def _get_entity(self, key: str):
        eid = self.get_prop(key, "")
        if not eid or not self.state_manager:
            return None
        return self.state_manager.get_entity(eid)

    @staticmethod
    def _parse_float(value: Any) -> float | None:
        if value is None:
            return None
        s = str(value).strip()
        if s.lower() in ("", "unavailable", "unknown", "none"):
            return None
        try:
            return float(s)
        except (ValueError, TypeError):
            return None

    def _watts_from(self, entity) -> float | None:
        """Return watts from a power entity, handling kW vs W."""
        val = self._parse_float(entity.state)
        if val is None:
            return None
        unit = str(entity.attributes.get("unit_of_measurement", "")).lower()
        if unit in ("kw", "kilowatt", "kilowatts"):
            val *= 1000.0
        return val

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------
    def refresh_from_state(self) -> None:
        both_empty = not self.get_prop("power_entity") and not self.get_prop("energy_today_entity")
        self.hint_label.setVisible(both_empty)

        # -- power --
        pw_ent = self._get_entity("power_entity")
        watts = self._watts_from(pw_ent) if pw_ent else None

        if watts is not None:
            self.power_label.setText(f"{watts:,.0f} W".replace(",", "."))
            # record history sample
            now = time.time()
            self._history.append((now, watts))
            self._prune_history(now)
            self._maybe_redraw_sparkline(now)
        else:
            self.power_label.setText("–")

        # -- today energy + cost --
        en_ent = self._get_entity("energy_today_entity")
        kwh = self._parse_float(en_ent.state) if en_ent else None
        price = float(self.get_prop("price_per_kwh", 0.0))

        parts: list[str] = []
        if kwh is not None:
            parts.append(f"Heute: {kwh:,.1f} kWh".replace(",", "X").replace(".", ",").replace("X", "."))
            if price > 0:
                cost = kwh * price
                parts.append(f"≈ {cost:,.2f} €/Tag".replace(",", "X").replace(".", ",").replace("X", "."))
        self.detail_label.setText("  |  ".join(parts) if parts else "")

    def on_state_changed(self, entity_id: str, new_state: dict) -> None:
        pe = self.get_prop("power_entity", "")
        ee = self.get_prop("energy_today_entity", "")
        if entity_id in (pe, ee):
            self._safe_refresh_from_state()

    # ------------------------------------------------------------------
    # History / sparkline
    # ------------------------------------------------------------------
    def _prune_history(self, now: float) -> None:
        limit = float(self.get_prop("graph_minutes", 60)) * 60.0
        while self._history and self._history[0][0] < now - limit:
            self._history.popleft()

    def _maybe_redraw_sparkline(self, now: float) -> None:
        if not self.get_prop("show_graph", True):
            return
        if (now - self._last_redraw) * 1000 >= self._throttle_ms:
            self._last_redraw = now
            self.update()

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        if not self.get_prop("show_graph", True):
            return
        if len(self._history) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        pad_x = 16
        pad_bottom = 10
        pad_top = rect.height() - 70  # sparkline sits in bottom ~60 px

        graph = QRectF(
            pad_x, pad_top,
            rect.width() - pad_x * 2,
            rect.height() - pad_top - pad_bottom,
        )
        if graph.width() <= 0 or graph.height() <= 0:
            painter.end()
            return

        times = [p[0] for p in self._history]
        values = [p[1] for p in self._history]
        min_t, max_t = times[0], times[-1]
        min_v = min(values)
        max_v = max(values)

        # zero baseline, small headroom above max
        if min_v > 0:
            min_v = 0.0
        headroom = (max_v - min_v) * 0.12 if max_v > min_v else 50.0
        max_v += headroom

        t_span = max_t - min_t if max_t > min_t else 1.0
        v_span = max_v - min_v if max_v > min_v else 1.0

        path = QPainterPath()
        first = True
        for t, v in self._history:
            x = graph.left() + ((t - min_t) / t_span) * graph.width()
            y = graph.bottom() - ((v - min_v) / v_span) * graph.height()
            if first:
                path.moveTo(x, y)
                first = False
            else:
                path.lineTo(x, y)

        # gradient fill
        fill = QPainterPath(path)
        fill.lineTo(graph.right(), graph.bottom())
        fill.lineTo(graph.left(), graph.bottom())
        fill.closeSubpath()

        accent = QColor(self.get_prop("accent_color", "#4C8DFF"))
        grad = QLinearGradient(0, graph.top(), 0, graph.bottom())
        top_c = QColor(accent); top_c.setAlpha(80)
        bot_c = QColor(accent); bot_c.setAlpha(5)
        grad.setColorAt(0.0, top_c)
        grad.setColorAt(1.0, bot_c)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawPath(fill)

        # line
        pen = QPen(accent)
        pen.setWidthF(2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        painter.end()
