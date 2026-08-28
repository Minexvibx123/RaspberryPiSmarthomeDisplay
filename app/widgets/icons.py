"""Self-contained vector icon set, drawn with QPainter.

Why not fonts/emoji: Raspberry Pi OS Lite ships no color-emoji or icon font
by default, so Unicode glyphs like the ones used in earlier iterations show
up as empty boxes. Drawing icons as simple vector shapes guarantees crisp,
consistent rendering on every system, at any size, with no font dependency.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

ICON_NAMES: list[str] = [
    "bulb", "power", "thermometer", "gauge", "blinds", "sun", "cloud", "rain",
    "snow", "storm", "night", "clock", "camera", "chart", "battery", "door",
    "star", "home", "sofa", "kitchen", "bed", "flash", "list", "gear",
    "media", "scene", "drop", "wind", "leaf", "speaker",
    "wifi", "cpu", "calendar", "shield", "vacuum", "fan", "lock", "person",
    "coin", "quote", "smile", "currency",
]


def _pen(color: QColor, width: float = 2.2) -> QPen:
    pen = QPen(color)
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def paint_icon(painter: QPainter, name: str, rect: QRectF, color: QColor) -> None:
    """Draw `name` centered/scaled inside `rect` using `color`."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    side = min(rect.width(), rect.height())
    cx, cy = rect.center().x(), rect.center().y()
    r = side / 2 * 0.8
    painter.setPen(_pen(color, side * 0.09))
    painter.setBrush(Qt.NoBrush)

    if name == "bulb":
        painter.drawEllipse(QPointF(cx, cy - r * 0.15), r * 0.65, r * 0.65)
        painter.drawLine(QPointF(cx - r * 0.3, cy + r * 0.55), QPointF(cx + r * 0.3, cy + r * 0.55))
        painter.drawLine(QPointF(cx - r * 0.22, cy + r * 0.8), QPointF(cx + r * 0.22, cy + r * 0.8))
    elif name == "power":
        painter.drawRoundedRect(QRectF(cx - r * 0.55, cy - r * 0.15, r * 1.1, r * 1.0), r * 0.15, r * 0.15)
        painter.drawLine(QPointF(cx, cy - r * 0.15), QPointF(cx, cy - r * 0.75))
        painter.drawLine(QPointF(cx - r * 0.3, cy - r * 0.75), QPointF(cx + r * 0.3, cy - r * 0.75))
    elif name == "thermometer":
        painter.drawRoundedRect(QRectF(cx - r * 0.2, cy - r * 0.85, r * 0.4, r * 1.3), r * 0.2, r * 0.2)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(cx, cy + r * 0.6), r * 0.32, r * 0.32)
    elif name == "gauge":
        painter.drawArc(QRectF(cx - r * 0.75, cy - r * 0.6, r * 1.5, r * 1.5), 30 * 16, 300 * 16)
        painter.drawLine(QPointF(cx, cy), QPointF(cx + r * 0.4, cy - r * 0.35))
    elif name == "blinds":
        for i in range(4):
            y = cy - r * 0.6 + i * (r * 0.4)
            painter.drawLine(QPointF(cx - r * 0.7, y), QPointF(cx + r * 0.7, y))
        painter.drawLine(QPointF(cx - r * 0.7, cy - r * 0.6), QPointF(cx - r * 0.7, cy + r * 0.6))
        painter.drawLine(QPointF(cx + r * 0.7, cy - r * 0.6), QPointF(cx + r * 0.7, cy + r * 0.6))
    elif name in ("sun",):
        painter.drawEllipse(QPointF(cx, cy), r * 0.45, r * 0.45)
        for angle in range(0, 360, 45):
            path = QPainterPath()
            import math
            rad = math.radians(angle)
            path.moveTo(cx + math.cos(rad) * r * 0.65, cy + math.sin(rad) * r * 0.65)
            path.lineTo(cx + math.cos(rad) * r * 0.95, cy + math.sin(rad) * r * 0.95)
            painter.drawPath(path)
    elif name in ("cloud", "storm", "rain", "snow"):
        path = QPainterPath()
        path.addEllipse(QPointF(cx - r * 0.35, cy), r * 0.4, r * 0.4)
        path.addEllipse(QPointF(cx + r * 0.15, cy - r * 0.15), r * 0.5, r * 0.5)
        path.addEllipse(QPointF(cx + r * 0.55, cy + r * 0.05), r * 0.35, r * 0.35)
        path.addRect(QRectF(cx - r * 0.35, cy, r * 1.0, r * 0.4))
        painter.drawPath(path.simplified())
        if name == "rain":
            for dx in (-0.2, 0.15, 0.5):
                painter.drawLine(QPointF(cx + r * dx, cy + r * 0.55), QPointF(cx + r * dx - r * 0.1, cy + r * 0.9))
        elif name == "snow":
            for dx in (-0.2, 0.15, 0.5):
                painter.drawEllipse(QPointF(cx + r * dx, cy + r * 0.75), r * 0.05, r * 0.05)
        elif name == "storm":
            bolt = QPainterPath()
            bolt.moveTo(cx + r * 0.1, cy + r * 0.5)
            bolt.lineTo(cx - r * 0.15, cy + r * 0.95)
            bolt.lineTo(cx + r * 0.05, cy + r * 0.85)
            bolt.lineTo(cx - r * 0.1, cy + r * 1.15)
            painter.setBrush(color)
            painter.drawPath(bolt)
    elif name == "night":
        path = QPainterPath()
        path.addEllipse(QRectF(cx - r * 0.6, cy - r * 0.6, r * 1.2, r * 1.2))
        cut = QPainterPath()
        cut.addEllipse(QRectF(cx - r * 0.3, cy - r * 0.75, r * 1.2, r * 1.2))
        painter.drawPath(path.subtracted(cut))
    elif name == "clock":
        painter.drawEllipse(QPointF(cx, cy), r * 0.8, r * 0.8)
        painter.drawLine(QPointF(cx, cy), QPointF(cx, cy - r * 0.45))
        painter.drawLine(QPointF(cx, cy), QPointF(cx + r * 0.35, cy + r * 0.1))
    elif name == "camera":
        painter.drawRoundedRect(QRectF(cx - r * 0.75, cy - r * 0.45, r * 1.5, r * 0.95), r * 0.15, r * 0.15)
        painter.drawEllipse(QPointF(cx, cy + r * 0.02), r * 0.32, r * 0.32)
        painter.drawRect(QRectF(cx - r * 0.25, cy - r * 0.75, r * 0.5, r * 0.3))
    elif name == "chart":
        painter.drawLine(QPointF(cx - r * 0.8, cy + r * 0.8), QPointF(cx + r * 0.8, cy + r * 0.8))
        painter.drawLine(QPointF(cx - r * 0.8, cy + r * 0.8), QPointF(cx - r * 0.8, cy - r * 0.8))
        path = QPainterPath()
        path.moveTo(cx - r * 0.7, cy + r * 0.3)
        path.lineTo(cx - r * 0.25, cy - r * 0.2)
        path.lineTo(cx + r * 0.15, cy + r * 0.1)
        path.lineTo(cx + r * 0.7, cy - r * 0.6)
        painter.drawPath(path)
    elif name == "battery":
        painter.drawRoundedRect(QRectF(cx - r * 0.75, cy - r * 0.45, r * 1.35, r * 0.9), r * 0.15, r * 0.15)
        painter.drawRect(QRectF(cx + r * 0.62, cy - r * 0.18, r * 0.15, r * 0.36))
        painter.setBrush(color)
        painter.drawRect(QRectF(cx - r * 0.6, cy - r * 0.28, r * 0.9, r * 0.56))
    elif name == "door":
        painter.drawRoundedRect(QRectF(cx - r * 0.5, cy - r * 0.85, r * 1.0, r * 1.7), r * 0.08, r * 0.08)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(cx + r * 0.25, cy), r * 0.08, r * 0.08)
    elif name == "star":
        path = QPainterPath()
        import math
        points = []
        for i in range(10):
            angle = math.radians(-90 + i * 36)
            radius = r * (0.95 if i % 2 == 0 else 0.4)
            points.append(QPointF(cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
        path.moveTo(points[0])
        for p in points[1:]:
            path.lineTo(p)
        path.closeSubpath()
        painter.setBrush(color)
        painter.drawPath(path)
    elif name == "home":
        path = QPainterPath()
        path.moveTo(cx - r * 0.8, cy + r * 0.1)
        path.lineTo(cx, cy - r * 0.8)
        path.lineTo(cx + r * 0.8, cy + r * 0.1)
        painter.drawPath(path)
        painter.drawRect(QRectF(cx - r * 0.55, cy + r * 0.1, r * 1.1, r * 0.7))
    elif name in ("sofa", "kitchen", "bed"):
        painter.drawRoundedRect(QRectF(cx - r * 0.8, cy - r * 0.1, r * 1.6, r * 0.75), r * 0.15, r * 0.15)
        painter.drawRoundedRect(QRectF(cx - r * 0.8, cy - r * 0.7, r * 1.6, r * 0.55), r * 0.15, r * 0.15)
    elif name == "flash":
        path = QPainterPath()
        path.moveTo(cx + r * 0.15, cy - r * 0.85)
        path.lineTo(cx - r * 0.45, cy + r * 0.15)
        path.lineTo(cx, cy + r * 0.15)
        path.lineTo(cx - r * 0.15, cy + r * 0.85)
        path.lineTo(cx + r * 0.5, cy - r * 0.1)
        path.lineTo(cx + r * 0.05, cy - r * 0.1)
        path.closeSubpath()
        painter.setBrush(color)
        painter.drawPath(path)
    elif name == "list":
        for i, dy in enumerate((-0.5, 0, 0.5)):
            painter.drawEllipse(QPointF(cx - r * 0.7, cy + r * dy), r * 0.08, r * 0.08)
            painter.drawLine(QPointF(cx - r * 0.45, cy + r * dy), QPointF(cx + r * 0.75, cy + r * dy))
    elif name == "gear":
        painter.drawEllipse(QPointF(cx, cy), r * 0.4, r * 0.4)
        import math
        for i in range(8):
            angle = math.radians(i * 45)
            x1, y1 = cx + math.cos(angle) * r * 0.55, cy + math.sin(angle) * r * 0.55
            x2, y2 = cx + math.cos(angle) * r * 0.9, cy + math.sin(angle) * r * 0.9
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    elif name == "media":
        painter.drawEllipse(QPointF(cx, cy), r * 0.85, r * 0.85)
        path = QPainterPath()
        path.moveTo(cx - r * 0.25, cy - r * 0.4)
        path.lineTo(cx - r * 0.25, cy + r * 0.4)
        path.lineTo(cx + r * 0.45, cy)
        path.closeSubpath()
        painter.setBrush(color)
        painter.drawPath(path)
    elif name == "scene":
        painter.drawEllipse(QPointF(cx - r * 0.25, cy - r * 0.25), r * 0.5, r * 0.5)
        painter.drawEllipse(QPointF(cx + r * 0.3, cy + r * 0.3), r * 0.35, r * 0.35)
    elif name == "drop":
        path = QPainterPath()
        path.moveTo(cx, cy - r * 0.85)
        path.cubicTo(cx + r * 0.8, cy + r * 0.1, cx + r * 0.5, cy + r * 0.85, cx, cy + r * 0.85)
        path.cubicTo(cx - r * 0.5, cy + r * 0.85, cx - r * 0.8, cy + r * 0.1, cx, cy - r * 0.85)
        painter.drawPath(path)
    elif name == "wind":
        for dy in (-0.3, 0, 0.3):
            painter.drawLine(QPointF(cx - r * 0.8, cy + r * dy), QPointF(cx + r * 0.6, cy + r * dy))
    elif name == "leaf":
        path = QPainterPath()
        path.moveTo(cx - r * 0.7, cy + r * 0.7)
        path.cubicTo(cx - r * 0.9, cy - r * 0.3, cx + r * 0.3, cy - r * 0.9, cx + r * 0.8, cy - r * 0.8)
        path.cubicTo(cx + r * 0.7, cy - r * 0.1, cx + r * 0.1, cy + r * 0.6, cx - r * 0.7, cy + r * 0.7)
        painter.drawPath(path)
    elif name == "speaker":
        painter.drawRoundedRect(QRectF(cx - r * 0.3, cy - r * 0.75, r * 0.6, r * 1.5), r * 0.15, r * 0.15)
        painter.drawEllipse(QPointF(cx, cy - r * 0.4), r * 0.15, r * 0.15)
        painter.drawEllipse(QPointF(cx, cy + r * 0.25), r * 0.22, r * 0.22)
    elif name == "wifi":
        for i, radius in enumerate((0.9, 0.6, 0.3)):
            span = 100 + i * 10
            painter.drawArc(QRectF(cx - r * radius, cy - r * radius, r * radius * 2, r * radius * 2), (90 - span // 2) * 16, span * 16)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(cx, cy + r * 0.75), r * 0.1, r * 0.1)
    elif name == "cpu":
        painter.drawRoundedRect(QRectF(cx - r * 0.5, cy - r * 0.5, r * 1.0, r * 1.0), r * 0.1, r * 0.1)
        painter.setBrush(color)
        painter.drawRoundedRect(QRectF(cx - r * 0.22, cy - r * 0.22, r * 0.44, r * 0.44), r * 0.05, r * 0.05)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            painter.drawLine(
                QPointF(cx + dx * r * 0.5, cy + dy * r * 0.5),
                QPointF(cx + dx * r * 0.85, cy + dy * r * 0.85),
            )
    elif name in ("calendar", "holiday"):
        painter.drawRoundedRect(QRectF(cx - r * 0.8, cy - r * 0.6, r * 1.6, r * 1.4), r * 0.12, r * 0.12)
        painter.drawLine(QPointF(cx - r * 0.8, cy - r * 0.15), QPointF(cx + r * 0.8, cy - r * 0.15))
        painter.drawLine(QPointF(cx - r * 0.4, cy - r * 0.75), QPointF(cx - r * 0.4, cy - r * 0.45))
        painter.drawLine(QPointF(cx + r * 0.4, cy - r * 0.75), QPointF(cx + r * 0.4, cy - r * 0.45))
    elif name == "shield":
        path = QPainterPath()
        path.moveTo(cx, cy - r * 0.9)
        path.cubicTo(cx + r * 0.7, cy - r * 0.65, cx + r * 0.7, cy - r * 0.65, cx + r * 0.7, cy - r * 0.2)
        path.cubicTo(cx + r * 0.7, cy + r * 0.55, cx + r * 0.3, cy + r * 0.85, cx, cy + r * 0.95)
        path.cubicTo(cx - r * 0.3, cy + r * 0.85, cx - r * 0.7, cy + r * 0.55, cx - r * 0.7, cy - r * 0.2)
        path.cubicTo(cx - r * 0.7, cy - r * 0.65, cx - r * 0.7, cy - r * 0.65, cx, cy - r * 0.9)
        painter.drawPath(path)
    elif name == "vacuum":
        painter.drawEllipse(QPointF(cx, cy), r * 0.85, r * 0.85)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(cx, cy), r * 0.28, r * 0.28)
    elif name == "fan":
        import math
        painter.setBrush(color)
        for i in range(3):
            angle = math.radians(i * 120)
            path = QPainterPath()
            path.moveTo(cx, cy)
            path.quadTo(
                cx + math.cos(angle - 0.4) * r * 0.9, cy + math.sin(angle - 0.4) * r * 0.9,
                cx + math.cos(angle) * r * 0.95, cy + math.sin(angle) * r * 0.95,
            )
            path.quadTo(
                cx + math.cos(angle + 0.4) * r * 0.9, cy + math.sin(angle + 0.4) * r * 0.9,
                cx, cy,
            )
            painter.drawPath(path)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), r * 0.15, r * 0.15)
    elif name == "lock":
        painter.drawRoundedRect(QRectF(cx - r * 0.55, cy - r * 0.05, r * 1.1, r * 0.9), r * 0.12, r * 0.12)
        painter.drawArc(QRectF(cx - r * 0.35, cy - r * 0.75, r * 0.7, r * 0.85), 0, 180 * 16)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(cx, cy + r * 0.35), r * 0.1, r * 0.1)
    elif name == "person":
        painter.drawEllipse(QPointF(cx, cy - r * 0.4), r * 0.32, r * 0.32)
        path = QPainterPath()
        path.moveTo(cx - r * 0.55, cy + r * 0.85)
        path.cubicTo(cx - r * 0.55, cy + r * 0.15, cx + r * 0.55, cy + r * 0.15, cx + r * 0.55, cy + r * 0.85)
        painter.drawPath(path)
    elif name == "coin":
        painter.drawEllipse(QPointF(cx, cy), r * 0.85, r * 0.85)
        painter.drawEllipse(QPointF(cx, cy), r * 0.55, r * 0.55)
    elif name == "quote":
        painter.setBrush(color)
        for dx in (-0.4, 0.25):
            path = QPainterPath()
            path.moveTo(cx + r * dx, cy - r * 0.3)
            path.cubicTo(cx + r * (dx - 0.35), cy - r * 0.1, cx + r * (dx - 0.35), cy + r * 0.4, cx + r * dx, cy + r * 0.55)
            path.cubicTo(cx + r * (dx + 0.05), cy + r * 0.35, cx + r * (dx + 0.05), cy - r * 0.15, cx + r * dx, cy - r * 0.3)
            painter.drawPath(path)
    elif name == "smile":
        painter.drawEllipse(QPointF(cx, cy), r * 0.85, r * 0.85)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(cx - r * 0.3, cy - r * 0.15), r * 0.08, r * 0.08)
        painter.drawEllipse(QPointF(cx + r * 0.3, cy - r * 0.15), r * 0.08, r * 0.08)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(QRectF(cx - r * 0.45, cy - r * 0.15, r * 0.9, r * 0.7), 200 * 16, 140 * 16)
    elif name == "currency":
        painter.drawArc(QRectF(cx - r * 0.8, cy - r * 0.55, r * 1.2, r * 1.0), 30 * 16, 200 * 16)
        painter.drawArc(QRectF(cx - r * 0.4, cy - r * 0.45, r * 1.2, r * 1.0), 210 * 16, 200 * 16)
    else:
        # generic fallback: rounded square
        painter.drawRoundedRect(QRectF(cx - r * 0.7, cy - r * 0.7, r * 1.4, r * 1.4), r * 0.25, r * 0.25)

    painter.restore()


def icon_pixmap(name: str, size: int = 48, color: str = "#FFFFFF") -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    paint_icon(painter, name, QRectF(0, 0, size, size), QColor(color))
    painter.end()
    return pixmap


def icon_qicon(name: str, size: int = 48, color: str = "#FFFFFF") -> QIcon:
    return QIcon(icon_pixmap(name, size, color))


class IconGlyph(QWidget):
    """A tiny widget that paints a single vector icon, scaling with its size."""

    def __init__(self, name: str = "star", color: str = "#FFFFFF", parent=None):
        super().__init__(parent)
        self.name = name
        self.color = QColor(color)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

    def set_icon(self, name: str) -> None:
        self.name = name
        self.update()

    def set_color(self, color: str) -> None:
        self.color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        paint_icon(painter, self.name, QRectF(0, 0, self.width(), self.height()), self.color)
