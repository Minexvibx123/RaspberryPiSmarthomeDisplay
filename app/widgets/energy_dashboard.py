"""Home Assistant Energy dashboard widget backed by recorder statistics."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QWidget

from app.widgets.base import BaseWidget, PropertyDef


class _EnergyHistoryChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.labels: list[str] = []
        self.series: list[tuple[str, QColor, list[float]]] = []
        self.setMinimumHeight(72)

    def set_data(self, labels: list[str], series: list[tuple[str, QColor, list[float]]]) -> None:
        self.labels = labels
        self.series = series
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.labels or not self.series:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(8, 6, -8, -18)
        maximum = max((max(values, default=0.0) for _, _, values in self.series), default=0.0)
        if maximum <= 0 or rect.width() <= 0 or rect.height() <= 0:
            painter.end()
            return

        group_width = rect.width() / len(self.labels)
        bar_width = min(12.0, group_width / (len(self.series) + 1))
        for series_index, (_, color, values) in enumerate(self.series):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            for index, value in enumerate(values):
                height = max(0.0, value) / maximum * (rect.height() - 3)
                x = rect.left() + group_width * index + group_width / 2
                x += (series_index - (len(self.series) - 1) / 2) * (bar_width + 2)
                painter.drawRoundedRect(QRectF(x - bar_width / 2, rect.bottom() - height, bar_width, height), 2, 2)

        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        count = len(self.labels)
        label_indices = sorted({0, count // 2, count - 1})
        for index in label_indices:
            x = rect.left() + group_width * index
            painter.drawText(QRectF(x - group_width / 2, rect.bottom() + 3, group_width, 14),
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                             self.labels[index])
        painter.end()


class EnergyDashboardWidget(BaseWidget):
    type_name = "energy_dashboard"
    display_name = "HA-Energiedashboard"
    category = "Anzeige"
    icon = "bolt"
    default_size = (420, 330)

    PROPERTY_SCHEMA = [
        PropertyDef("refresh_minutes", "Aktualisierung (Minuten)", "number", 15,
                    min=1, max=60, group="Daten"),
    ]

    def __init__(self, widget_id: int, config: dict, state_manager=None, parent=None):
        self._period = "today"
        self._sources: list[dict] = []
        self._device_sources: list[dict] = []
        self._prefs_loaded = False
        self._prefs_request_in_flight = False
        self._request_generation = 0
        self._power_entity_ids: set[str] = set()
        self._soc_entity_ids: set[str] = set()
        self._pending_rpc_ids: set[int] = set()
        super().__init__(widget_id, config, state_manager, parent)

        self.destroyed.connect(self._cancel_pending_requests)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_from_state)
        self._update_refresh_interval()
        if self.state_manager:
            self.state_manager.connection_status_changed.connect(self._on_connection_changed)
            self.state_manager.entity_updated.connect(self._on_entity_updated)
            if self.state_manager.connected:
                self.refresh_from_state()

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item is not None and item.widget():
                item.widget().deleteLater()
        self.content_layout.setSpacing(5)

        header = QHBoxLayout()
        title = QLabel("Energie")
        title.setStyleSheet("font-weight: 700; border: none; background: transparent;")
        self.period_combo = QComboBox()
        self.period_combo.addItem("Heute", "today")
        self.period_combo.addItem("7 Tage", "week")
        self.period_combo.addItem("Monat", "month")
        self.period_combo.setCurrentIndex(max(0, self.period_combo.findData(self._period)))
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        self.reload_button = QPushButton("Aktualisieren")
        self.reload_button.clicked.connect(self.refresh_from_state)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.period_combo)
        header.addWidget(self.reload_button)
        self.content_layout.addLayout(header)

        self.live_label = QLabel("PV —  ·  Netz —")
        self.live_label.setStyleSheet("font-weight: 600; border: none; background: transparent;")
        self.content_layout.addWidget(self.live_label)

        self._metric_labels: dict[str, QLabel] = {}
        metric_names = [
            ("solar", "PV"), ("home", "Hausverbrauch"),
            ("grid_import", "Netzbezug"), ("grid_export", "Einspeisung"),
            ("battery_out", "Akku Entladen"), ("battery_in", "Akku Laden"),
        ]
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(2)
        for index, (key, label) in enumerate(metric_names):
            column, row = index % 3, index // 3
            name = QLabel(label)
            name.setStyleSheet("opacity: 0.65; border: none; background: transparent;")
            value = QLabel("—")
            value.setStyleSheet("font-size: 16px; font-weight: 700; border: none; background: transparent;")
            grid.addWidget(name, row * 2, column)
            grid.addWidget(value, row * 2 + 1, column)
            self._metric_labels[key] = value
        self.content_layout.addLayout(grid)

        self.devices_label = QLabel("")
        self.devices_label.setWordWrap(True)
        self.devices_label.setStyleSheet("font-size: 11px; border: none; background: transparent;")
        self.devices_label.hide()
        self.content_layout.addWidget(self.devices_label)

        self.chart = _EnergyHistoryChart(self)
        self.chart_caption = QLabel("PV und Netzbezug")
        self.chart_caption.setStyleSheet("font-size: 11px; opacity: 0.65; border: none; background: transparent;")
        self.content_layout.addWidget(self.chart_caption)
        self.content_layout.addWidget(self.chart, 1)
        self.status_label = QLabel("Warte auf Home Assistant …")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 11px; opacity: 0.65; border: none; background: transparent;")
        self.content_layout.addWidget(self.status_label)

    def refresh_from_state(self) -> None:
        self._update_refresh_interval()
        if not self.state_manager:
            self.status_label.setText("Kein Home-Assistant-State-Manager verfügbar")
            return
        if self.state_manager.demo_mode:
            self.status_label.setText("Historische Energiedaten sind im Demo-Modus nicht verfügbar")
            return
        if not self.state_manager.connected:
            self.status_label.setText("Warte auf Home-Assistant-Verbindung …")
            return
        if self._prefs_request_in_flight:
            return
        self._prefs_request_in_flight = True
        self.status_label.setText("Lade HA-Energiekonfiguration …")
        self._send_rpc({"type": "energy/get_prefs"}, self._on_preferences_loaded)

    def _send_rpc(self, command: dict, callback) -> None:
        request_id_holder: dict[str, int] = {}

        def on_result(success: bool, result: Any, error: str) -> None:
            request_id = request_id_holder.get("id")
            if request_id is not None:
                self._pending_rpc_ids.discard(request_id)
            callback(success, result, error)

        request_id = self.state_manager.send_websocket_command(command, on_result)
        if request_id is not None:
            request_id_holder["id"] = request_id
            self._pending_rpc_ids.add(request_id)

    def _cancel_pending_requests(self, *_args) -> None:
        if self.state_manager:
            for request_id in tuple(self._pending_rpc_ids):
                self.state_manager.cancel_websocket_command(request_id)
        self._pending_rpc_ids.clear()

    def _update_refresh_interval(self) -> None:
        if hasattr(self, "_refresh_timer"):
            minutes = max(1, min(60, int(self.get_prop("refresh_minutes", 15))))
            self._refresh_timer.start(minutes * 60 * 1000)

    def _on_connection_changed(self, connected: bool) -> None:
        if connected:
            self.refresh_from_state()
        else:
            self.status_label.setText("Home Assistant nicht verbunden; letzte Werte bleiben erhalten")

    def _on_period_changed(self, _index: int) -> None:
        self._period = self.period_combo.currentData() or "today"
        if self._prefs_loaded:
            self._request_statistics()

    def _on_preferences_loaded(self, success: bool, result: Any, error: str) -> None:
        self._prefs_request_in_flight = False
        if not success:
            self.status_label.setText(f"HA-Energiedashboard nicht erreichbar: {error}")
            return
        sources = result.get("energy_sources", []) if isinstance(result, dict) else []
        if not isinstance(sources, list) or not sources:
            self._prefs_loaded = False
            self.status_label.setText("Im HA-Energiedashboard sind keine Energiequellen eingerichtet")
            return
        self._sources = [source for source in sources if isinstance(source, dict)]
        devices = result.get("device_consumption", [])
        self._device_sources = [device for device in devices if isinstance(device, dict)] if isinstance(devices, list) else []
        self._prefs_loaded = True
        self._power_entity_ids = {
            str(source["stat_rate"]) for source in self._sources if source.get("stat_rate")
        }
        self._soc_entity_ids = {
            str(source["stat_soc"]) for source in self._sources if source.get("stat_soc")
        }
        self._update_live_values()
        self._request_statistics()

    def _statistics_ids(self) -> list[str]:
        ids: set[str] = set()
        for source in self._sources:
            source_type = source.get("type")
            keys = ("stat_energy_from", "stat_energy_to")
            if source_type in ("solar", "grid", "battery"):
                for key in keys:
                    value = source.get(key)
                    if value:
                        ids.add(str(value))
        for device in self._device_sources:
            value = device.get("stat_consumption")
            if value:
                ids.add(str(value))
        return sorted(ids)

    def _request_statistics(self) -> None:
        statistic_ids = self._statistics_ids()
        if not statistic_ids:
            self.status_label.setText("Die HA-Energiequellen enthalten keine Langzeitstatistiken")
            return
        now = datetime.now().astimezone()
        if self._period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period = "hour"
        elif self._period == "week":
            start = now - timedelta(days=7)
            period = "day"
        else:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period = "day"
        self._request_generation += 1
        generation = self._request_generation
        self.status_label.setText("Lade Langzeitstatistiken …")
        command = {
            "type": "recorder/statistics_during_period",
            "start_time": start.isoformat(),
            "end_time": now.isoformat(),
            "statistic_ids": statistic_ids,
            "period": period,
            "types": ["change"],
        }
        self._send_rpc(
            command,
            lambda success, result, error: self._on_statistics_loaded(
                generation, success, result, error,
            ),
        )

    def _on_statistics_loaded(self, generation: int, success: bool,
                              result: Any, error: str) -> None:
        if generation != self._request_generation:
            return
        if not success or not isinstance(result, dict):
            self.status_label.setText(f"HA-Statistiken nicht verfügbar: {error or 'Ungültige Antwort'}")
            return

        totals: dict[str, float] = {}
        buckets: dict[str, dict[str, float]] = {}
        bucket_labels: dict[str, str] = {}
        for statistic_id, rows in result.items():
            if not isinstance(rows, list):
                continue
            per_bucket: dict[str, float] = {}
            total = 0.0
            has_value = False
            for row in rows:
                if not isinstance(row, dict) or row.get("change") is None:
                    continue
                try:
                    change = float(row["change"])
                    timestamp = float(row["start"])
                    if timestamp > 100_000_000_000:
                        timestamp /= 1000.0
                except (KeyError, TypeError, ValueError):
                    continue
                moment = datetime.fromtimestamp(timestamp).astimezone()
                bucket = moment.strftime("%Y-%m-%d-%H" if self._period == "today" else "%Y-%m-%d")
                bucket_labels[bucket] = moment.strftime("%H" if self._period == "today" else "%d.%m")
                per_bucket[bucket] = per_bucket.get(bucket, 0.0) + change
                total += change
                has_value = True
            if has_value:
                totals[statistic_id] = total
                buckets[statistic_id] = per_bucket

        solar_ids = self._source_ids("solar", "stat_energy_from")
        grid_in_ids = self._source_ids("grid", "stat_energy_from")
        grid_out_ids = self._source_ids("grid", "stat_energy_to")
        battery_out_ids = self._source_ids("battery", "stat_energy_from")
        battery_in_ids = self._source_ids("battery", "stat_energy_to")
        solar = self._sum_stats(solar_ids, totals)
        grid_import = self._sum_stats(grid_in_ids, totals)
        grid_export = self._sum_stats(grid_out_ids, totals)
        battery_out = self._sum_stats(battery_out_ids, totals)
        battery_in = self._sum_stats(battery_in_ids, totals)
        measured = [solar, grid_import, grid_export, battery_out, battery_in]
        home = None if all(value is None for value in measured) else (
            (solar or 0.0) + (grid_import or 0.0) + (battery_out or 0.0)
            - (grid_export or 0.0) - (battery_in or 0.0)
        )
        self._set_metric("solar", solar)
        self._set_metric("home", home)
        self._set_metric("grid_import", grid_import)
        self._set_metric("grid_export", grid_export)
        self._set_metric("battery_out", battery_out)
        self._set_metric("battery_in", battery_in)

        device_lines = []
        for device in self._device_sources:
            statistic_id = str(device.get("stat_consumption", ""))
            if not statistic_id:
                continue
            entity = self.state_manager.get_entity(statistic_id) if self.state_manager else None
            name = device.get("name") or (entity.friendly_name if entity else statistic_id.split(".")[-1])
            value = totals.get(statistic_id)
            formatted = "—" if value is None else f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + " kWh"
            device_lines.append(f"{name}: {formatted}")
        if device_lines:
            self.devices_label.setText("Einzelgeräte · " + "  |  ".join(device_lines))
            self.devices_label.show()
        else:
            self.devices_label.hide()

        ordered_buckets = sorted(bucket_labels)
        labels = [bucket_labels[key] for key in ordered_buckets]
        chart_series = []
        for label, color, statistic_ids in (
            ("PV", QColor("#E7B93F"), solar_ids),
            ("Netz", QColor("#5AA7D8"), grid_in_ids),
        ):
            values = [
                sum(buckets.get(statistic_id, {}).get(key, 0.0) for statistic_id in statistic_ids)
                for key in ordered_buckets
            ]
            if any(values):
                chart_series.append((label, color, values))
        self.chart.set_data(labels, chart_series)
        if not ordered_buckets:
            self.status_label.setText("Für diesen Zeitraum sind noch keine Statistiken vorhanden")
        else:
            self.status_label.setText(f"HA-Langzeitstatistiken · {len(ordered_buckets)} Zeitabschnitte")
        self._update_live_values()

    def _source_ids(self, source_type: str, key: str) -> list[str]:
        return [
            str(source[key]) for source in self._sources
            if source.get("type") == source_type and source.get(key)
        ]

    @staticmethod
    def _sum_stats(statistic_ids: list[str], totals: dict[str, float]) -> float | None:
        available = [totals[statistic_id] for statistic_id in statistic_ids if statistic_id in totals]
        return sum(available) if available else None

    def _set_metric(self, key: str, value: float | None) -> None:
        text = "—" if value is None else f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + " kWh"
        self._metric_labels[key].setText(text)

    def _update_live_values(self) -> None:
        solar_parts = []
        grid_parts = []
        battery_parts = []
        soc_values: list[tuple[float, float]] = []
        for source in self._sources:
            entity_id = source.get("stat_rate")
            if self.state_manager and entity_id:
                entity = self.state_manager.get_entity(str(entity_id))
                if entity:
                    try:
                        value = float(entity.state)
                    except (TypeError, ValueError):
                        value = None
                    if value is not None:
                        unit = str(entity.attributes.get("unit_of_measurement", "W")).lower()
                        if unit in ("w", "watt", "watts"):
                            value /= 1000.0
                        if source.get("type") == "solar":
                            solar_parts.append(value)
                        elif source.get("type") == "grid":
                            grid_parts.append(value)
                        elif source.get("type") == "battery":
                            battery_parts.append(value)

            soc_entity_id = source.get("stat_soc")
            if self.state_manager and source.get("type") == "battery" and soc_entity_id:
                entity = self.state_manager.get_entity(str(soc_entity_id))
                if entity:
                    try:
                        capacity = max(0.0, float(source.get("capacity", 0.0)))
                        soc_values.append((float(entity.state), capacity))
                    except (TypeError, ValueError):
                        pass
        solar_text = "—" if not solar_parts else f"{sum(solar_parts):.2f} kW"
        grid_value = sum(grid_parts) if grid_parts else None
        if grid_value is None:
            grid_text = "—"
        elif grid_value < 0:
            grid_text = f"{abs(grid_value):.2f} kW Einspeisung"
        else:
            grid_text = f"{grid_value:.2f} kW Bezug"
        live_parts = [f"PV {solar_text}", f"Netz {grid_text}"]
        if battery_parts:
            battery_value = sum(battery_parts)
            direction = "Entladen" if battery_value >= 0 else "Laden"
            live_parts.append(f"Akku {abs(battery_value):.2f} kW {direction}")
        if soc_values:
            total_capacity = sum(capacity for _, capacity in soc_values)
            if total_capacity > 0:
                soc = sum(value * capacity for value, capacity in soc_values) / total_capacity
            else:
                soc = sum(value for value, _ in soc_values) / len(soc_values)
            live_parts.append(f"Ladestand {soc:.0f}%")
        self.live_label.setText("  ·  ".join(live_parts))

    def _on_entity_updated(self, entity_id: str, _state: dict) -> None:
        if entity_id in self._power_entity_ids or entity_id in self._soc_entity_ids:
            self._update_live_values()

    def on_state_changed(self, entity_id: str, new_state: dict) -> None:
        self._on_entity_updated(entity_id, new_state)
