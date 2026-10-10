"""Theme presets and stylesheet generation.

A theme is a plain dict of design tokens. It gets turned into a Qt
stylesheet that is applied to the whole application, so changing a theme
instantly re-skins every screen without touching widget code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.database import Database

BUILT_IN_THEMES: list[dict] = [
    {
        "name": "Aurora",
        "mode": "dark",
        "background": "#111817",
        "surface": "#1C2724",
        "primary": "#72D6B5",
        "secondary": "#93B8CA",
        "accent": "#F0B85B",
        "text": "#F2F6F3",
        "text_secondary": "#A8BBB2",
        "card_radius": 12,
        "card_opacity": 98,
        "shadow": True,
        "border": True,
        "font_family": "Noto Sans, DejaVu Sans, sans-serif",
        "font_size_base": 16,
        "spacing": 12,
    },
    {
        "name": "Porcelain",
        "mode": "light",
        "background": "#EEF2ED",
        "surface": "#FFFFFF",
        "primary": "#276B57",
        "secondary": "#B86750",
        "accent": "#C38B35",
        "text": "#1D2A25",
        "text_secondary": "#5C6C64",
        "card_radius": 10,
        "card_opacity": 100,
        "shadow": False,
        "border": True,
        "font_family": "Noto Sans, DejaVu Sans, sans-serif",
        "font_size_base": 16,
        "spacing": 12,
    },
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
    secondary = theme.get("secondary", "#8A7CFF")
    accent = theme.get("accent", "#33D9B2")
    text = theme.get("text", "#FFFFFF")
    text_secondary = theme.get("text_secondary", "#9AA1B4")
    font_family = theme.get("font_family", "Inter, sans-serif")
    font_size = theme.get("font_size_base", 16)
    radius = max(4, min(int(theme.get("card_radius", 12)), 20))
    border = "rgba(255,255,255,24)" if theme.get("mode") == "dark" else "rgba(20,40,32,34)"
    muted = "rgba(255,255,255,28)" if theme.get("mode") == "dark" else "rgba(20,40,32,24)"
    return f"""
    QMainWindow, QDialog {{
        background-color: {bg};
        color: {text};
        font-family: {font_family};
        font-size: {font_size}px;
    }}
    QWidget {{
        color: {text};
        font-family: {font_family};
        font-size: {font_size}px;
        selection-background-color: {primary};
    }}
    QLabel {{ color: {text}; background: transparent; }}
    QGroupBox {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: {radius}px;
        margin-top: 14px;
        padding: 18px 12px 10px 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 5px;
        color: {text_secondary};
    }}
    QPushButton {{
        background-color: {surface};
        color: {text};
        border-radius: 10px;
        min-height: 38px;
        padding: 6px 14px;
        border: 1px solid {border};
    }}
    QPushButton:hover {{ border: 1px solid {primary}; background-color: {secondary}; }}
    QPushButton:pressed, QPushButton:checked {{ background-color: {primary}; color: {bg}; }}
    QPushButton:disabled {{ color: {text_secondary}; background-color: {bg}; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTimeEdit {{
        background-color: {surface};
        color: {text};
        border-radius: 8px;
        min-height: 32px;
        padding: 4px 9px;
        border: 1px solid {border};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 2px solid {primary}; }}
    QComboBox QAbstractItemView {{ background-color: {surface}; color: {text}; selection-background-color: {primary}; }}
    QCheckBox {{ spacing: 10px; }}
    QCheckBox::indicator {{ width: 22px; height: 22px; border-radius: 6px; border: 1px solid {text_secondary}; background: {surface}; }}
    QCheckBox::indicator:checked {{ background: {primary}; border-color: {primary}; }}
    QTabWidget::pane {{ border: 1px solid {border}; border-radius: {radius}px; top: -1px; background: {bg}; }}
    QTabBar::tab {{ color: {text_secondary}; background: {surface}; border: 1px solid {border}; border-bottom: none; border-radius: 8px 8px 0 0; padding: 10px 16px; min-height: 30px; }}
    QTabBar::tab:selected {{ color: {text}; background: {bg}; border-top: 3px solid {primary}; }}
    QTabBar::tab:hover:!selected {{ color: {text}; background: {secondary}; }}
    QListWidget, QTreeWidget, QTableWidget {{ background: {surface}; border: 1px solid {border}; border-radius: 8px; outline: none; }}
    QListWidget::item {{ min-height: 34px; padding: 4px 8px; border-radius: 6px; }}
    QListWidget::item:selected {{ background: {primary}; color: {bg}; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ width: 10px; background: transparent; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {muted}; border-radius: 5px; min-height: 28px; }}
    QScrollBar::handle:vertical:hover {{ background: {primary}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QSlider::groove:horizontal {{
        height: 6px; background: {muted}; border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {primary}; width: 22px; height: 22px; margin: -8px 0; border-radius: 11px; border: 2px solid {surface};
    }}
    QToolTip {{ color: {text}; background-color: {surface}; border: 1px solid {primary}; border-radius: 6px; padding: 5px 8px; }}
    #connectionBadgeOk {{ color: {accent}; font-weight: 700; }}
    #connectionBadgeBad {{ color: #F07868; font-weight: 700; }}
    #navBar {{ background-color: {surface}; border-top: 1px solid {border}; }}
    #navButton {{ color: {text_secondary}; border: 1px solid transparent; background: transparent; font-size: 13px; }}
    #navButton:hover {{ color: {text}; background: {bg}; border: 1px solid {border}; }}
    #navButtonActive {{ color: {primary}; border: 1px solid {border}; background: {bg}; font-weight: 700; font-size: 13px; }}
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
