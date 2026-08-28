"""Theme presets and stylesheet generation.

A theme is a plain dict of design tokens. It gets turned into a Qt
stylesheet that is applied to the whole application, so changing a theme
instantly re-skins every screen without touching widget code.
"""
from __future__ import annotations

from dataclasses import dataclass, field

BUILT_IN_THEMES: list[dict] = [
    {
        "name": "Dark Glass",
        "mode": "dark",
        "background": "#101218",
        "surface": "#1B1E29",
        "primary": "#4C8DFF",
        "secondary": "#8A7CFF",
        "accent": "#33D9B2",
        "text": "#FFFFFF",
        "text_secondary": "#9AA1B4",
        "card_radius": 20,
        "card_opacity": 92,
        "shadow": True,
        "border": True,
        "font_family": "Inter, Segoe UI, sans-serif",
        "font_size_base": 16,
        "spacing": 14,
    },
    {
        "name": "Minimal",
        "mode": "light",
        "background": "#F2F3F5",
        "surface": "#FFFFFF",
        "primary": "#2D6CDF",
        "secondary": "#5B8DEF",
        "accent": "#20B2AA",
        "text": "#1A1D29",
        "text_secondary": "#6B7280",
        "card_radius": 14,
        "card_opacity": 100,
        "shadow": False,
        "border": True,
        "font_family": "Inter, Segoe UI, sans-serif",
        "font_size_base": 16,
        "spacing": 12,
    },
    {
        "name": "Industrial",
        "mode": "dark",
        "background": "#1C1C1C",
        "surface": "#2A2A2A",
        "primary": "#FF9800",
        "secondary": "#FFC107",
        "accent": "#FF5722",
        "text": "#F5F5F5",
        "text_secondary": "#B0B0B0",
        "card_radius": 6,
        "card_opacity": 96,
        "shadow": True,
        "border": True,
        "font_family": "Roboto Condensed, sans-serif",
        "font_size_base": 15,
        "spacing": 10,
    },
    {
        "name": "Modern",
        "mode": "dark",
        "background": "#0E0F1A",
        "surface": "#181A28",
        "primary": "#7C4DFF",
        "secondary": "#4C8DFF",
        "accent": "#00E5A0",
        "text": "#FFFFFF",
        "text_secondary": "#A0A6BD",
        "card_radius": 24,
        "card_opacity": 90,
        "shadow": True,
        "border": False,
        "font_family": "Inter, Segoe UI, sans-serif",
        "font_size_base": 17,
        "spacing": 16,
    },
]


def build_stylesheet(theme: dict) -> str:
    bg = theme.get("background", "#101218")
    surface = theme.get("surface", "#1B1E29")
    primary = theme.get("primary", "#4C8DFF")
    text = theme.get("text", "#FFFFFF")
    text_secondary = theme.get("text_secondary", "#9AA1B4")
    font_family = theme.get("font_family", "Inter, sans-serif")
    font_size = theme.get("font_size_base", 16)
    return f"""
    QMainWindow, QWidget#appRoot {{
        background-color: {bg};
        color: {text};
        font-family: {font_family};
        font-size: {font_size}px;
    }}
    QLabel {{ color: {text}; background: transparent; }}
    QPushButton {{
        background-color: {surface};
        color: {text};
        border-radius: 12px;
        padding: 10px 16px;
        border: 1px solid rgba(255,255,255,20);
    }}
    QPushButton:hover {{ background-color: {primary}; }}
    QPushButton:pressed {{ background-color: {primary}; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: {surface};
        color: {text};
        border-radius: 8px;
        padding: 8px;
        border: 1px solid rgba(255,255,255,30);
    }}
    QScrollArea {{ border: none; background: transparent; }}
    QSlider::groove:horizontal {{
        height: 6px; background: rgba(255,255,255,30); border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {primary}; width: 22px; height: 22px; margin: -8px 0; border-radius: 11px;
    }}
    QToolTip {{ color: {text}; background-color: {surface}; border: 1px solid {primary}; }}
    #connectionBadgeOk {{ color: #33D9B2; font-weight: 600; }}
    #connectionBadgeBad {{ color: #FF5C5C; font-weight: 600; }}
    #navBar {{ background-color: {surface}; border-top: 1px solid rgba(255,255,255,15); }}
    #navButton {{ color: {text_secondary}; border: none; background: transparent; font-size: 13px; }}
    #navButtonActive {{ color: {primary}; border: none; background: transparent; font-weight: 700; font-size: 13px; }}
    """


@dataclass
class ThemeManager:
    db: "Database"  # noqa: F821 - avoid circular import at type-check time

    def active(self) -> dict:
        t = self.db.get_active_theme()
        return t.config if t else BUILT_IN_THEMES[0]

    def all_themes(self):
        return self.db.list_themes()

    def apply(self, app, theme: dict) -> None:
        app.setStyleSheet(build_stylesheet(theme))

    def set_active(self, theme_id: int) -> None:
        self.db.set_active_theme(theme_id)

    def save_custom(self, name: str, config: dict, set_active: bool = True) -> None:
        self.db.save_theme(name, config, set_active=set_active, built_in=False)

    def check_auto_mode(self, app, db) -> None:
        mode = db.get_setting("theme_mode", "dark")
        if mode != "auto":
            return
        from datetime import datetime
        hour = datetime.now().hour
        # Light mode: 7:00 - 19:00, Dark: 19:00 - 7:00
        desired = "light" if 7 <= hour < 19 else "dark"
        current_active = db.get_active_theme()
        if current_active:
            current_mode = current_active.config.get("mode", "dark")
            if current_mode != desired:
                # Find theme matching desired mode
                for theme in self.all_themes():
                    if theme.config.get("mode") == desired:
                        self.set_active(theme.id)
                        self.apply(app, theme.config)
                        return
