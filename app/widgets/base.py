"""Base class and shared property-schema plumbing for all panel widgets.

Every concrete widget (button, light, sensor, ...) subclasses BaseWidget and
declares a small PROPERTY_SCHEMA describing which knobs the properties panel
should expose. This is what makes the whole system "no-code": the editor UI
never needs to know anything widget-specific, it just renders whatever
schema the widget provides.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QVBoxLayout, QWidget

from app.core.conditions import OPERATORS, matches_condition
from app.core.animations import ANIMATION_NAMES, animation_engine


@dataclass
class PropertyDef:
    key: str
    label: str
    type: str  # "text" | "number" | "color" | "bool" | "select" | "icon" | "entity" | "font_size" | "image" | "action"
    default: Any = None
    options: Optional[list] = None  # for "select"
    min: Optional[float] = None
    max: Optional[float] = None
    entity_domains: Optional[list[str]] = None  # for "entity"
    action: str = ""  # builder id opened by the properties panel, for "action"
    group: str = "Allgemein"


# Properties every widget has, regardless of type.
COMMON_SCHEMA: list[PropertyDef] = [
    PropertyDef("name", "Name", "text", "", group="Allgemein"),
    PropertyDef("bg_color", "Hintergrundfarbe", "color", "#1E1F29", group="Darstellung"),
    PropertyDef("text_color", "Textfarbe", "color", "#FFFFFF", group="Darstellung"),
    PropertyDef("accent_color", "Akzentfarbe", "color", "#4C8DFF", group="Darstellung"),
    PropertyDef("radius", "Eckenradius", "number", 16, min=0, max=60, group="Darstellung"),
    PropertyDef("opacity", "Transparenz", "number", 100, min=10, max=100, group="Darstellung"),
    PropertyDef("bg_gradient_enabled", "Hintergrund-Verlauf", "bool", False, group="Darstellung"),
    PropertyDef("gradient_color", "Verlauf-Farbe", "color", "#4C8DFF", group="Darstellung"),
    PropertyDef("gradient_direction", "Verlauf-Richtung", "select", "vertical", options=["vertical", "horizontal", "radial"], group="Darstellung"),
    PropertyDef("bg_image_path", "Hintergrundbild", "image", "", group="Darstellung"),
    PropertyDef("bg_image_opacity", "Bild-Transparenz", "number", 30, min=5, max=100, group="Darstellung"),
    PropertyDef("shadow", "Schatten", "bool", True, group="Darstellung"),
    PropertyDef("font_size", "Schriftgröße", "number", 16, min=8, max=48, group="Darstellung"),
    PropertyDef("font_family", "Schriftart", "select", "", options=["", "Inter", "Roboto", "Segoe UI", "monospace"], group="Darstellung"),
    PropertyDef("icon_position", "Icon-Position", "select", "top", options=["top", "left", "right", "hidden"], group="Layout"),
    PropertyDef("padding", "Innenabstand", "number", 12, min=0, max=40, group="Layout"),
    PropertyDef("visible_entity", "Sichtbar wenn Entity", "entity", "", group="Sichtbarkeit"),
    PropertyDef("visible_operator", "Vergleich", "select", "equals", options=OPERATORS, group="Sichtbarkeit"),
    PropertyDef("visible_state", "Erwarteter Zustand", "text", "on", group="Sichtbarkeit"),
    PropertyDef("visible_invert", "Invertiert", "bool", False, group="Sichtbarkeit"),
    PropertyDef("style_enabled", "Styling-Regel aktiv", "bool", False, group="Bedingtes Styling"),
    PropertyDef("style_entity", "Entity", "entity", "", group="Bedingtes Styling"),
    PropertyDef("style_operator", "Vergleich", "select", "equals", options=OPERATORS, group="Bedingtes Styling"),
    PropertyDef("style_value", "Vergleichswert", "text", "", group="Bedingtes Styling"),
    PropertyDef("style_bg_color", "Hintergrundfarbe", "color", "", group="Bedingtes Styling"),
    PropertyDef("style_text_color", "Textfarbe", "color", "", group="Bedingtes Styling"),
    PropertyDef("entrance_animation", "Eintritt", "select", "none", options=ANIMATION_NAMES, group="Animation"),
    PropertyDef("state_animation", "Statuswechsel", "select", "none", options=ANIMATION_NAMES, group="Animation"),
    PropertyDef("animation_speed", "Geschwindigkeit", "number", 1.0, min=0.1, max=3.0, group="Animation"),
]


class BaseWidget(QWidget):
    """Common behaviour: styling, entity binding, edit-mode selection."""

    type_name: str = "base"
    display_name: str = "Basis"
    category: str = "Allgemein"
    icon: str = "\U0001F4E6"
    default_size: tuple[int, int] = (200, 140)
    requires_entity: bool = False
    entity_domains: list[str] = []
    PROPERTY_SCHEMA: list[PropertyDef] = []

    clicked = Signal()

    def __init__(self, widget_id: int, config: dict, state_manager=None, parent=None):
        super().__init__(parent)
        self.widget_id = widget_id
        self.config: dict = dict(config or {})
        self.state_manager = state_manager
        self.selected = False
        self._active = False
        self._conditional_overrides: dict[str, Any] = {}
        self._shadow_effect: Optional[QGraphicsDropShadowEffect] = None

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(12, 10, 12, 10)
        self.content_layout.setSpacing(4)

        self.build_ui()
        self.apply_style()
        self._safe_refresh_from_state()
        QTimer.singleShot(0, lambda: animation_engine.play(
            self,
            self.get_prop("entrance_animation", "none"),
            float(self.get_prop("animation_speed", 1.0)),
        ))

    # -- to be implemented by subclasses ---------------------------------- #
    def build_ui(self) -> None:
        """Create child widgets/layouts for the widget's content."""

    def refresh_from_state(self) -> None:
        """Pull current entity state (if any) and update the visuals."""

    def _safe_refresh_from_state(self) -> None:
        # a bug/unexpected entity shape in one widget must never take down the
        # whole panel - log it and leave the widget showing its last good state
        self.apply_conditional_style()
        try:
            self.refresh_from_state()
        except Exception:
            logging.getLogger(__name__).exception(
                "Widget %s (%s) failed to refresh from state", self.widget_id, self.type_name
            )
        self.check_visibility()

    def check_visibility(self) -> None:
        entity_id = self.get_prop("visible_entity", "")
        if not entity_id:
            self.show()
            return
        expected = self.get_prop("visible_state", "on")
        operator = self.get_prop("visible_operator", "equals")
        invert = self.get_prop("visible_invert", False)
        
        entity = None
        if self.state_manager:
            entity = self.state_manager.get_entity(entity_id)
            
        if entity is None:
            visible = False
        else:
            visible = matches_condition(entity.state, operator, expected)
            
        if invert:
            visible = not visible
            
        if visible:
            self.show()
        else:
            self.hide()

    def paintEvent(self, event):
        gradient_enabled = self.get_prop("bg_gradient_enabled", False)
        bg_image = self.get_prop("bg_image_path", "")
        
        if gradient_enabled or bg_image:
            from PySide6.QtGui import QPainter, QLinearGradient, QRadialGradient, QBrush, QPixmap, QPainterPath
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            radius = self.get_prop("radius", 16)
            rect = self.rect()
            
            if gradient_enabled:
                gradient_color = QColor(self.get_prop("gradient_color", "#4C8DFF"))
                bg = QColor(self.get_prop("bg_color", "#1E1F29"))
                direction = self.get_prop("gradient_direction", "vertical")
                
                if direction == "vertical":
                    grad = QLinearGradient(0, 0, 0, rect.height())
                elif direction == "horizontal":
                    grad = QLinearGradient(0, 0, rect.width(), 0)
                else:  # radial
                    center = rect.center()
                    grad = QRadialGradient(center, max(rect.width(), rect.height()) / 2)
                
                grad.setColorAt(0, bg)
                grad.setColorAt(1, gradient_color)
                
                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect, radius, radius)
                
            if bg_image:
                import os
                if os.path.exists(bg_image):
                    pixmap = QPixmap(bg_image)
                    if not pixmap.isNull():
                        img_opacity = self.get_prop("bg_image_opacity", 30) / 100.0
                        painter.setOpacity(img_opacity)
                        scaled = pixmap.scaled(rect.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                        x = (rect.width() - scaled.width()) // 2
                        y = (rect.height() - scaled.height()) // 2
                        
                        path = QPainterPath()
                        path.addRoundedRect(rect, radius, radius)
                        painter.setClipPath(path)
                        
                        painter.drawPixmap(x, y, scaled)
                        painter.setOpacity(1.0)
            
            painter.end()
            
        super().paintEvent(event)

    def on_state_changed(self, entity_id: str, new_state: dict) -> None:
        """Called by the dashboard when the bound entity updates."""
        monitored_entities = {
            self.config.get("entity_id"),
            self.get_prop("visible_entity", ""),
            self.get_prop("style_entity", ""),
        }
        if entity_id in monitored_entities:
            self._safe_refresh_from_state()
            animation_engine.play(
                self,
                self.get_prop("state_animation", "none"),
                float(self.get_prop("animation_speed", 1.0)),
            )

    def apply_conditional_style(self) -> None:
        """Apply the active style rule without altering the stored base style."""
        overrides: dict[str, Any] = {}
        if self.config.get("style_enabled", False):
            entity_id = self.config.get("style_entity", "")
            entity = self.state_manager.get_entity(entity_id) if self.state_manager and entity_id else None
            if entity and matches_condition(
                entity.state,
                self.config.get("style_operator", "equals"),
                self.config.get("style_value", ""),
            ):
                for key in ("bg_color", "text_color"):
                    value = self.config.get(f"style_{key}", "")
                    if value:
                        overrides[key] = value
        if overrides != self._conditional_overrides:
            self._conditional_overrides = overrides
            self.apply_style()

    # -- shared helpers ---------------------------------------------------- #
    @classmethod
    def full_schema(cls) -> list[PropertyDef]:
        return COMMON_SCHEMA + cls.PROPERTY_SCHEMA

    def get_prop(self, key: str, fallback: Any = None) -> Any:
        if key in self._conditional_overrides:
            return self._conditional_overrides[key]
        for p in self.full_schema():
            if p.key == key:
                return self.config.get(key, p.default)
        return self.config.get(key, fallback)

    def apply_style(self) -> None:
        radius = self.get_prop("radius", 16)
        bg = QColor(self.get_prop("bg_color", "#1E1F29"))
        opacity = self.get_prop("opacity", 100) / 100.0
        accent = QColor(self.get_prop("accent_color", "#4C8DFF"))

        if self._active:
            # blend the accent color into the background so "on"/active state is
            # unmistakable at a glance, not just via a small icon color change
            bg = QColor(
                int(bg.red() * 0.55 + accent.red() * 0.45),
                int(bg.green() * 0.55 + accent.green() * 0.45),
                int(bg.blue() * 0.55 + accent.blue() * 0.45),
            )
        bg.setAlphaF(opacity)

        if self.selected:
            border = "2px solid #4C8DFF"
        elif self._active:
            border = f"2px solid {accent.name()}"
        else:
            border = "1px solid rgba(255,255,255,25)"
            
        gradient_enabled = self.get_prop("bg_gradient_enabled", False)
        if not gradient_enabled:
            self.setStyleSheet(
                f"""
                QWidget#panelWidget {{
                    background-color: rgba({bg.red()},{bg.green()},{bg.blue()},{bg.alphaF()});
                    border-radius: {radius}px;
                    border: {border};
                }}
                """
            )
        else:
            self.setStyleSheet(
                f"""
                QWidget#panelWidget {{
                    border-radius: {radius}px;
                    border: {border};
                }}
                """
            )
        self.setObjectName("panelWidget")

        if self.get_prop("shadow", True) and not self.selected:
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(28 if self._active else 24)
            effect.setOffset(0, 4)
            effect.setColor(QColor(*accent.getRgb()[:3], 120) if self._active else QColor(0, 0, 0, 160))
            self.setGraphicsEffect(effect)
        else:
            self.setGraphicsEffect(None)

    def set_active(self, active: bool) -> None:
        """Mark the widget as representing an "on"/active entity state."""
        if self._active != active:
            self._active = active
            self.apply_style()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self.apply_style()

    def apply_config(self, config: dict) -> None:
        self.config = dict(config or {})
        self.apply_style()
        self.build_ui()
        self._safe_refresh_from_state()

    def call_service(self, domain: str, service: str, **data) -> None:
        entity_id = self.config.get("entity_id")
        if self.state_manager and entity_id:
            self.state_manager.call_service(domain, service, entity_id=entity_id, **data)

    def entity(self):
        entity_id = self.config.get("entity_id")
        if self.state_manager and entity_id:
            return self.state_manager.get_entity(entity_id)
        return None
