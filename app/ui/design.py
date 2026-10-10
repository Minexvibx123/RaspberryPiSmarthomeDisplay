"""Design tokens, contrast helpers and the Qt styling shared by every screen."""
from __future__ import annotations

from PySide6.QtGui import QColor, QLinearGradient, QPalette

_FONT = "Noto Sans, DejaVu Sans, sans-serif"

BUILT_IN_THEMES: list[dict] = [
    {"name": "Aurora", "mode": "dark", "background": "#0D1412", "surface": "#16211E",
     "surface_alt": "#1F2D29", "primary": "#5FD8B4", "secondary": "#7FB4D6", "accent": "#F2BD62",
     "text": "#EEF5F1", "text_secondary": "#9DB3A9", "card_radius": 18, "card_opacity": 100,
     "shadow": True, "border": True, "font_family": _FONT, "font_size_base": 16, "spacing": 14},
    {"name": "Porcelain", "mode": "light", "background": "#E9EEEA", "surface": "#FFFFFF",
     "surface_alt": "#F3F6F4", "primary": "#1F6B55", "secondary": "#A85B45", "accent": "#B77D1E",
     "text": "#18241F", "text_secondary": "#52625A", "card_radius": 18, "card_opacity": 100,
     "shadow": True, "border": True, "font_family": _FONT, "font_size_base": 16, "spacing": 14},
    {"name": "Dark Glass", "mode": "dark", "background": "#0C0F16", "surface": "#171B27",
     "surface_alt": "#212636", "primary": "#6AA2FF", "secondary": "#9C8CFF", "accent": "#3DDDB9",
     "text": "#F4F6FB", "text_secondary": "#9AA3B8", "card_radius": 22, "card_opacity": 100,
     "shadow": True, "border": True, "font_family": _FONT, "font_size_base": 16, "spacing": 14},
    {"name": "Minimal", "mode": "light", "background": "#F0F1F4", "surface": "#FFFFFF",
     "surface_alt": "#F5F6F9", "primary": "#2459C9", "secondary": "#4B7BE0", "accent": "#0E8F86",
     "text": "#161A26", "text_secondary": "#566074", "card_radius": 16, "card_opacity": 100,
     "shadow": True, "border": True, "font_family": _FONT, "font_size_base": 16, "spacing": 12},
    {"name": "Industrial", "mode": "dark", "background": "#171717", "surface": "#242424",
     "surface_alt": "#303030", "primary": "#FFA726", "secondary": "#FFD54F", "accent": "#FF7043",
     "text": "#F4F4F4", "text_secondary": "#B4B4B4", "card_radius": 8, "card_opacity": 100,
     "shadow": True, "border": True, "font_family": _FONT, "font_size_base": 15, "spacing": 10},
    {"name": "Modern", "mode": "dark", "background": "#0B0C17", "surface": "#161830",
     "surface_alt": "#20233F", "primary": "#8B6CFF", "secondary": "#5C9BFF", "accent": "#10E5A8",
     "text": "#F6F6FF", "text_secondary": "#A5AACB", "card_radius": 26, "card_opacity": 100,
     "shadow": True, "border": False, "font_family": _FONT, "font_size_base": 17, "spacing": 16},
    {"name": "Mitternacht", "mode": "dark", "background": "#000000", "surface": "#0F1114",
     "surface_alt": "#181B20", "primary": "#4FC3F7", "secondary": "#81D4FA", "accent": "#FFD740",
     "text": "#FFFFFF", "text_secondary": "#A3AAB3", "card_radius": 20, "card_opacity": 100,
     "shadow": False, "border": True, "font_family": _FONT, "font_size_base": 16, "spacing": 14},
    {"name": "Sand", "mode": "light", "background": "#F2EBDD", "surface": "#FFFBF2",
     "surface_alt": "#F8F0E0", "primary": "#B4531F", "secondary": "#7A5A2B", "accent": "#2E7D6B",
     "text": "#2A2118", "text_secondary": "#6B5C49", "card_radius": 20, "card_opacity": 100,
     "shadow": True, "border": True, "font_family": _FONT, "font_size_base": 16, "spacing": 14},
]

_ACTIVE: dict = dict(BUILT_IN_THEMES[0])


def _color(value, fallback: str = "#000000") -> QColor:
    if isinstance(value, QColor):
        return QColor(value)
    color = QColor(str(value))
    return color if color.isValid() else QColor(fallback)


def _channel(value: int) -> float:
    v = value / 255
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def _luminance(color: QColor) -> float:
    return 0.2126 * _channel(color.red()) + 0.7152 * _channel(color.green()) + 0.0722 * _channel(color.blue())


def contrast_ratio(first, second) -> float:
    a, b = _luminance(_color(first)), _luminance(_color(second))
    high, low = max(a, b), min(a, b)
    return (high + 0.05) / (low + 0.05)


def readable(foreground, background, minimum: float = 4.5) -> str:
    """Return the foreground, or black/white if it would be hard to read on the background."""
    fg = _color(foreground)
    if contrast_ratio(fg, background) >= minimum:
        return fg.name()
    light, dark = QColor("#FFFFFF"), QColor("#0B1210")
    best = light if contrast_ratio(light, background) >= contrast_ratio(dark, background) else dark
    return best.name()


def mix(first, second, amount: float) -> str:
    a, b = _color(first), _color(second)
    amount = max(0.0, min(1.0, amount))
    return QColor(
        round(a.red() * (1 - amount) + b.red() * amount),
        round(a.green() * (1 - amount) + b.green() * amount),
        round(a.blue() * (1 - amount) + b.blue() * amount),
    ).name()


def rgba(color, alpha: float) -> str:
    c = _color(color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{round(max(0.0, min(1.0, alpha)) * 100)}%)"


def _tokens(theme: dict) -> dict:
    base = dict(BUILT_IN_THEMES[0])
    base.update({k: v for k, v in (theme or {}).items() if v not in (None, "")})
    base.setdefault("surface_alt", mix(base["surface"], base["text"], 0.06))
    return base


def set_active_theme(theme: dict) -> None:
    _ACTIVE.clear()
    _ACTIVE.update(_tokens(theme))


def widget_default(key: str):
    """Theme-aware default for the shared widget colours; None for unrelated keys."""
    t = _ACTIVE
    surface = t["surface"]
    if key == "bg_color":
        return surface
    if key == "text_color":
        return readable(t["text"], surface)
    if key == "accent_color":
        return readable(t["primary"], surface, 3.0)
    if key == "gradient_color":
        return t["primary"]
    if key == "radius":
        return min(int(t.get("card_radius", 16)), 28)
    return None


def canvas_gradient(width: int, height: int) -> QLinearGradient:
    t = _ACTIVE
    gradient = QLinearGradient(0, 0, width * 0.4, height)
    gradient.setColorAt(0.0, _color(mix(t["background"], t["primary"], 0.07)))
    gradient.setColorAt(1.0, _color(mix(t["background"], t["secondary"], 0.03)))
    return gradient


def build_palette(theme: dict) -> QPalette:
    t = _tokens(theme)
    bg, surface, alt, text = t["background"], t["surface"], t["surface_alt"], t["text"]
    on_surface = readable(text, surface)
    on_primary = readable("#FFFFFF", t["primary"])
    palette = QPalette()
    for role, value in (
        (QPalette.ColorRole.Window, bg), (QPalette.ColorRole.WindowText, readable(text, bg)),
        (QPalette.ColorRole.Base, surface), (QPalette.ColorRole.AlternateBase, alt),
        (QPalette.ColorRole.Text, on_surface), (QPalette.ColorRole.Button, alt),
        (QPalette.ColorRole.ButtonText, readable(text, alt)),
        (QPalette.ColorRole.ToolTipBase, surface), (QPalette.ColorRole.ToolTipText, on_surface),
        (QPalette.ColorRole.Highlight, t["primary"]), (QPalette.ColorRole.HighlightedText, on_primary),
        (QPalette.ColorRole.PlaceholderText, t["text_secondary"]), (QPalette.ColorRole.Link, t["primary"]),
    ):
        palette.setColor(role, _color(value))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, _color(t["text_secondary"]))
    return palette


def build_stylesheet(theme: dict) -> str:
    t = _tokens(theme)
    bg, surface, alt = t["background"], t["surface"], t["surface_alt"]
    primary, secondary, accent = t["primary"], t["secondary"], t["accent"]
    text, muted_text = t["text"], t["text_secondary"]
    radius = max(6, min(int(t.get("card_radius", 16)), 28))
    control = max(8, radius - 4)
    font, size = t["font_family"], int(t.get("font_size_base", 16))
    dark = t.get("mode") == "dark"
    border = rgba("#FFFFFF" if dark else "#14281F", 0.12 if dark else 0.16)
    track = rgba("#FFFFFF" if dark else "#14281F", 0.14 if dark else 0.12)
    on_surface, on_alt = readable(text, surface), readable(text, alt)
    on_bg = readable(text, bg)
    on_primary = readable("#FFFFFF", primary)
    hover_bg = mix(alt, primary, 0.2)
    on_hover = readable(text, hover_bg)
    active_bg = mix(surface, primary, 0.18)
    on_active = readable(primary, active_bg)
    danger = "#E5645A" if dark else "#B3261E"
    on_danger = readable("#FFFFFF", danger)
    badge_ok = readable(accent, bg, 3.0)
    badge_bad = readable(danger, bg, 3.0)
    return f"""
    QMainWindow, QDialog {{ background-color: {bg}; color: {on_bg}; font-family: {font}; font-size: {size}px; }}
    QWidget {{ color: {on_bg}; font-family: {font}; font-size: {size}px; selection-background-color: {primary}; selection-color: {on_primary}; }}
    QLabel {{ background: transparent; }}
    QMessageBox, QInputDialog {{ background-color: {surface}; }}
    QMessageBox QLabel, QInputDialog QLabel {{ color: {on_surface}; }}
    QToolTip {{ color: {on_surface}; background-color: {surface}; border: 1px solid {primary}; border-radius: 8px; padding: 6px 10px; }}
    QGroupBox {{ background-color: {surface}; color: {on_surface}; border: 1px solid {border}; border-radius: {radius}px; margin-top: 16px; padding: 20px 14px 12px 14px; font-weight: 700; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; color: {readable(muted_text, surface, 3.5)}; }}
    QFrame#appCard {{ background-color: {surface}; border: 1px solid {border}; border-radius: {radius}px; }}
    QFrame#appCard QLabel {{ color: {on_surface}; }}
    QPushButton {{ background-color: {alt}; color: {on_alt}; border: 1px solid {border}; border-radius: {control}px; min-height: 40px; padding: 6px 16px; font-weight: 600; }}
    QPushButton:hover {{ background-color: {hover_bg}; color: {on_hover}; border-color: {primary}; }}
    QPushButton:pressed, QPushButton:checked {{ background-color: {primary}; color: {on_primary}; border-color: {primary}; }}
    QPushButton:disabled {{ color: {muted_text}; background-color: {mix(alt, bg, 0.5)}; border-color: transparent; }}
    QPushButton[variant="primary"] {{ background-color: {primary}; color: {on_primary}; border-color: {primary}; }}
    QPushButton[variant="primary"]:hover {{ background-color: {mix(primary, '#FFFFFF', 0.14)}; color: {readable('#FFFFFF', mix(primary, '#FFFFFF', 0.14))}; }}
    QPushButton[variant="danger"] {{ background-color: {danger}; color: {on_danger}; border-color: {danger}; }}
    QPushButton#iconButton {{ min-height: 0; padding: 0; border-radius: 20px; font-size: 18px; }}
    QPushButton#appTile {{ background-color: {surface}; color: {on_surface}; border: 1px solid {border}; border-radius: {radius}px; min-height: 104px; padding: 12px; text-align: left; font-weight: 600; }}
    QPushButton#appTile:hover {{ border: 2px solid {primary}; background-color: {mix(surface, primary, 0.1)}; color: {readable(text, mix(surface, primary, 0.1))}; }}
    QPushButton#appTile QLabel {{ color: {on_surface}; background: transparent; }}
    QPushButton#appTile:hover QLabel {{ color: {readable(text, mix(surface, primary, 0.1))}; }}
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QTimeEdit, QDateEdit, QComboBox {{ background-color: {surface}; color: {on_surface}; border: 1px solid {border}; border-radius: {control}px; min-height: 36px; padding: 4px 10px; }}
    QTextEdit, QPlainTextEdit {{ padding: 8px; }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border: 2px solid {primary}; }}
    QLineEdit:disabled, QComboBox:disabled {{ color: {muted_text}; }}
    QComboBox::drop-down {{ border: none; width: 28px; }}
    QComboBox QAbstractItemView {{ background-color: {surface}; color: {on_surface}; border: 1px solid {border}; selection-background-color: {primary}; selection-color: {on_primary}; outline: none; }}
    QCheckBox, QRadioButton {{ spacing: 10px; }}
    QCheckBox::indicator, QRadioButton::indicator {{ width: 24px; height: 24px; border: 2px solid {muted_text}; background: {surface}; }}
    QCheckBox::indicator {{ border-radius: 7px; }}
    QRadioButton::indicator {{ border-radius: 12px; }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background: {primary}; border-color: {primary}; }}
    QTabWidget::pane {{ border: 1px solid {border}; border-radius: {radius}px; top: -1px; background: {surface}; }}
    QTabBar::tab {{ color: {readable(muted_text, bg, 3.5)}; background: transparent; border: none; border-bottom: 3px solid transparent; padding: 12px 18px; min-height: 28px; font-weight: 600; }}
    QTabBar::tab:selected {{ color: {readable(primary, bg, 3.5)}; border-bottom: 3px solid {primary}; }}
    QTabBar::tab:hover:!selected {{ color: {on_bg}; }}
    QListView, QListWidget, QTreeView, QTreeWidget, QTableView, QTableWidget {{ background-color: {surface}; alternate-background-color: {alt}; color: {on_surface}; border: 1px solid {border}; border-radius: {control}px; outline: none; gridline-color: {border}; }}
    QListWidget::item {{ min-height: 40px; padding: 4px 10px; border-radius: 8px; }}
    QListView::item:selected, QListWidget::item:selected, QTreeView::item:selected, QTableView::item:selected {{ background-color: {primary}; color: {on_primary}; }}
    QHeaderView::section {{ background-color: {alt}; color: {on_alt}; border: none; border-bottom: 1px solid {border}; padding: 8px 10px; font-weight: 700; }}
    QTableCornerButton::section {{ background-color: {alt}; border: none; }}
    QMenu {{ background-color: {surface}; color: {on_surface}; border: 1px solid {border}; border-radius: {control}px; padding: 6px; }}
    QMenu::item {{ padding: 10px 22px; border-radius: 8px; }}
    QMenu::item:selected {{ background-color: {primary}; color: {on_primary}; }}
    QCalendarWidget QWidget {{ background-color: {surface}; color: {on_surface}; }}
    QCalendarWidget QAbstractItemView:enabled {{ background-color: {surface}; color: {on_surface}; selection-background-color: {primary}; selection-color: {on_primary}; }}
    QCalendarWidget QAbstractItemView:disabled {{ color: {muted_text}; }}
    QCalendarWidget QToolButton {{ background-color: {alt}; color: {on_alt}; border-radius: 8px; min-height: 36px; padding: 0 12px; }}
    QProgressBar {{ background-color: {track}; border: none; border-radius: 8px; min-height: 16px; text-align: center; color: {on_bg}; }}
    QProgressBar::chunk {{ background-color: {primary}; border-radius: 8px; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ width: 12px; background: transparent; margin: 2px; }}
    QScrollBar:horizontal {{ height: 12px; background: transparent; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {track}; border-radius: 5px; min-height: 36px; }}
    QScrollBar::handle:horizontal {{ background: {track}; border-radius: 5px; min-width: 36px; }}
    QScrollBar::handle:hover {{ background: {primary}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    QSlider::groove:horizontal {{ height: 8px; background: {track}; border-radius: 4px; }}
    QSlider::sub-page:horizontal {{ background: {primary}; border-radius: 4px; }}
    QSlider::handle:horizontal {{ background: {primary}; width: 26px; height: 26px; margin: -9px 0; border-radius: 13px; border: 3px solid {surface}; }}
    #connectionBadgeOk {{ color: {badge_ok}; font-weight: 700; }}
    #connectionBadgeBad {{ color: {badge_bad}; font-weight: 700; }}
    #navBar {{ background-color: {surface}; border-top: 1px solid {border}; }}
    #navButton {{ min-height: 0; color: {readable(muted_text, surface, 3.5)}; border: 1px solid transparent; border-radius: {control}px; background: transparent; font-size: 13px; font-weight: 600; padding: 4px 10px; }}
    #navButton:hover {{ color: {on_surface}; background: {alt}; }}
    #navButtonActive {{ min-height: 0; color: {on_active}; border: 1px solid {rgba(primary, 0.5)}; border-radius: {control}px; background: {active_bg}; font-size: 13px; font-weight: 800; padding: 4px 10px; }}
    """


def apply_theme(app, theme: dict) -> None:
    set_active_theme(theme)
    app.setPalette(build_palette(theme))
    app.setStyleSheet(build_stylesheet(theme))
