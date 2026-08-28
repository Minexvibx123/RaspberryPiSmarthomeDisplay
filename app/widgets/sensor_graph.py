"""Sensor history graph widget."""
from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel

from app.widgets.base import BaseWidget, PropertyDef


class SensorGraphWidget(BaseWidget):
    type_name = "sensor_graph"
    display_name = "Sensor-Verlauf"
    category = "Anzeige"
    icon = "chart"
    default_size = (220, 140)
    requires_entity = True
    entity_domains = ["sensor", "binary_sensor"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["sensor", "binary_sensor"], group="Verbindung"),
        PropertyDef("history_hours", "Historie (Stunden)", "number", 24, min=1, max=168, group="Inhalt"),
        PropertyDef("show_current", "Aktuellen Wert anzeigen", "bool", True, group="Inhalt"),
    ]

    def __init__(self, widget_id: int, config: dict, state_manager=None, parent=None):
        self._data_points: list[tuple[float, float]] = []
        super().__init__(widget_id, config, state_manager, parent)

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        self.value_label = QLabel("--")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet(
            f"color: {self.get_prop('accent_color', '#4C8DFF')}; font-size: {int(self.get_prop('font_size', 16)) + 10}px; font-weight: 600; border: none; background: transparent;"
        )
        
        self.name_label = QLabel(self.get_prop("name") or self.config.get("entity_id", "Sensor"))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet(
            f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {int(self.get_prop('font_size', 16)) - 2}px; border: none; background: transparent;"
        )
        
        self.content_layout.addWidget(self.value_label)
        self.content_layout.addWidget(self.name_label)
        
        if not self.get_prop("show_current", True):
            self.value_label.hide()
            self.name_label.hide()

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            self.value_label.setText("--")
            return
            
        # Update current value label
        unit = e.attributes.get("unit_of_measurement", "")
        try:
            val_float = float(e.state)
            val_str = f"{val_float:.1f}"
        except (ValueError, TypeError):
            val_str = str(e.state)
            val_float = 1.0 if str(e.state).lower() in ("on", "true", "1") else 0.0
            
        self.value_label.setText(f"{val_str} {unit}".strip())
        
        # Update data points
        now = time.time()
        self._data_points.append((now, val_float))
        
        # Trim old data points
        history_seconds = self.get_prop("history_hours", 24) * 3600
        cutoff_time = now - history_seconds
        self._data_points = [p for p in self._data_points if p[0] >= cutoff_time]
        
        # Limit max points to avoid performance issues
        if len(self._data_points) > 200:
            # Keep every nth point to reduce size but maintain span
            step = len(self._data_points) / 200.0
            self._data_points = [self._data_points[int(i * step)] for i in range(200)]
            
        self.update()  # Trigger repaint

    def paintEvent(self, event) -> None:
        # Draw base widget styling (background, border, shadow)
        super().paintEvent(event)
        
        if len(self._data_points) < 2:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate graph area
        rect = self.rect()
        padding_x = 16
        padding_bottom = 24
        
        # Adjust top padding based on whether labels are shown
        padding_top = 65 if self.get_prop("show_current", True) else 16
        
        graph_rect = QRectF(
            padding_x, 
            padding_top, 
            rect.width() - padding_x * 2, 
            rect.height() - padding_top - padding_bottom
        )
        
        if graph_rect.height() <= 0 or graph_rect.width() <= 0:
            return
            
        # Find min/max for scaling
        times = [p[0] for p in self._data_points]
        values = [p[1] for p in self._data_points]
        
        min_t, max_t = min(times), max(times)
        min_v, max_v = min(values), max(values)
        
        # Add some margin to min/max values so line doesn't touch top/bottom
        v_margin = (max_v - min_v) * 0.1 if max_v > min_v else 1.0
        min_v -= v_margin
        max_v += v_margin
        
        t_range = max_t - min_t if max_t > min_t else 1.0
        v_range = max_v - min_v if max_v > min_v else 1.0
        
        # Build path
        path = QPainterPath()
        first = True
        
        for t, v in self._data_points:
            x = graph_rect.left() + ((t - min_t) / t_range) * graph_rect.width()
            y = graph_rect.bottom() - ((v - min_v) / v_range) * graph_rect.height()
            
            if first:
                path.moveTo(x, y)
                first = False
            else:
                path.lineTo(x, y)
                
        # Draw gradient fill below line
        fill_path = QPainterPath(path)
        fill_path.lineTo(graph_rect.right(), graph_rect.bottom())
        fill_path.lineTo(graph_rect.left(), graph_rect.bottom())
        fill_path.closeSubpath()
        
        accent = QColor(self.get_prop("accent_color", "#4C8DFF"))
        
        gradient = QLinearGradient(0, graph_rect.top(), 0, graph_rect.bottom())
        color_top = QColor(accent)
        color_top.setAlpha(80)
        color_bottom = QColor(accent)
        color_bottom.setAlpha(5)
        
        gradient.setColorAt(0.0, color_top)
        gradient.setColorAt(1.0, color_bottom)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawPath(fill_path)
        
        # Draw line
        pen = QPen(accent)
        pen.setWidthF(2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        
        # Draw time labels (start and end)
        text_color = QColor(self.get_prop("text_color", "#FFFFFF"))
        text_color.setAlpha(120)
        painter.setPen(text_color)
        
        font = painter.font()
        font.setPixelSize(10)
        painter.setFont(font)
        
        # Format times (e.g., "-24h" and "Jetzt")
        hours = self.get_prop("history_hours", 24)
        start_text = f"-{hours}h"
        end_text = "Jetzt"
        
        painter.drawText(
            QRectF(graph_rect.left(), graph_rect.bottom() + 4, 50, 15),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            start_text
        )
        
        painter.drawText(
            QRectF(graph_rect.right() - 50, graph_rect.bottom() + 4, 50, 15),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            end_text
        )
