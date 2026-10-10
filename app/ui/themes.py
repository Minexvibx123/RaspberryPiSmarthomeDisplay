"""Theme presets and the manager that applies them; tokens and styling live in design.py."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from app.ui.design import BUILT_IN_THEMES, apply_theme, build_stylesheet

if TYPE_CHECKING:
    from app.core.database import Database

__all__ = ["BUILT_IN_THEMES", "ThemeManager", "build_stylesheet"]


@dataclass
class ThemeManager:
    db: "Database"

    def active(self) -> dict:
        theme = self.db.get_active_theme()
        return theme.config if theme else BUILT_IN_THEMES[0]

    def all_themes(self):
        return self.db.list_themes()

    def apply(self, app, theme: dict) -> None:
        apply_theme(app, theme)

    def set_active(self, theme_id: int) -> None:
        self.db.set_active_theme(theme_id)

    def save_custom(self, name: str, config: dict, set_active: bool = True) -> None:
        self.db.save_theme(name, config, set_active=set_active, built_in=False)

    def check_auto_mode(self, app, db) -> None:
        if db.get_setting("theme_mode", "dark") != "auto":
            return
        desired = "light" if 7 <= datetime.now().hour < 19 else "dark"
        current = db.get_active_theme()
        if current and current.config.get("mode", "dark") != desired:
            for theme in self.all_themes():
                if theme.config.get("mode") == desired:
                    self.set_active(theme.id)
                    self.apply(app, theme.config)
                    return
