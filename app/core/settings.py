"""Typed convenience wrapper around the settings key/value table."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.database import Database


@dataclass
class AppSettings:
    db: Database

    @property
    def language(self) -> str:
        return self.db.get_setting("language", "de")

    @language.setter
    def language(self, value: str) -> None:
        self.db.set_setting("language", value)

    @property
    def ha_url(self) -> str:
        return self.db.get_setting("ha_url", "")

    @ha_url.setter
    def ha_url(self, value: str) -> None:
        self.db.set_setting("ha_url", value.rstrip("/"))

    @property
    def ha_token(self) -> str:
        return self.db.get_setting("ha_token", "")

    @ha_token.setter
    def ha_token(self, value: str) -> None:
        # never logged, only persisted to the local sqlite file
        self.db.set_setting("ha_token", value)

    @property
    def demo_mode(self) -> bool:
        return bool(self.db.get_setting("demo_mode", False))

    @demo_mode.setter
    def demo_mode(self, value: bool) -> None:
        self.db.set_setting("demo_mode", bool(value))

    @property
    def setup_complete(self) -> bool:
        return bool(self.db.get_setting("setup_complete", False))

    @setup_complete.setter
    def setup_complete(self, value: bool) -> None:
        self.db.set_setting("setup_complete", bool(value))

    @property
    def edit_pin(self) -> Optional[str]:
        return self.db.get_setting("edit_pin", None)

    @edit_pin.setter
    def edit_pin(self, value: Optional[str]) -> None:
        self.db.set_setting("edit_pin", value)

    @property
    def orientation(self) -> str:
        return self.db.get_setting("orientation", "landscape")

    @orientation.setter
    def orientation(self, value: str) -> None:
        self.db.set_setting("orientation", value)

    @property
    def design_resolution(self) -> tuple[int, int]:
        val = self.db.get_setting("design_resolution", [1024, 600])
        return int(val[0]), int(val[1])

    @design_resolution.setter
    def design_resolution(self, value: tuple[int, int]) -> None:
        self.db.set_setting("design_resolution", list(value))

    @property
    def effective_design_resolution(self) -> tuple[int, int]:
        """design_resolution, swapped to match the current orientation setting.

        design_resolution is always stored in its native (landscape) form;
        this derives the actual w/h the canvas should use so switching
        "Ausrichtung" in the settings doesn't require re-entering numbers.
        """
        w, h = self.design_resolution
        is_landscape_stored = w >= h
        if self.orientation == "portrait" and is_landscape_stored:
            return h, w
        if self.orientation == "landscape" and not is_landscape_stored:
            return h, w
        return w, h

    @property
    def navigation_style(self) -> str:
        return self.db.get_setting("navigation_style", "bottom")

    @navigation_style.setter
    def navigation_style(self, value: str) -> None:
        self.db.set_setting("navigation_style", value)

    @property
    def theme_mode(self) -> str:
        """light | dark | auto"""
        return self.db.get_setting("theme_mode", "dark")

    @theme_mode.setter
    def theme_mode(self, value: str) -> None:
        self.db.set_setting("theme_mode", value)

    @property
    def standby_enabled(self) -> bool:
        return bool(self.db.get_setting("standby_enabled", True))

    @standby_enabled.setter
    def standby_enabled(self, value: bool) -> None:
        self.db.set_setting("standby_enabled", bool(value))

    @property
    def standby_dim_minutes(self) -> int:
        return int(self.db.get_setting("standby_dim_minutes", 2))

    @standby_dim_minutes.setter
    def standby_dim_minutes(self, value: int) -> None:
        self.db.set_setting("standby_dim_minutes", int(value))

    @property
    def standby_off_minutes(self) -> int:
        return int(self.db.get_setting("standby_off_minutes", 5))

    @standby_off_minutes.setter
    def standby_off_minutes(self, value: int) -> None:
        self.db.set_setting("standby_off_minutes", int(value))

    @property
    def standby_dim_opacity(self) -> int:
        return int(self.db.get_setting("standby_dim_opacity", 60))

    @standby_dim_opacity.setter
    def standby_dim_opacity(self, value: int) -> None:
        self.db.set_setting("standby_dim_opacity", int(value))

    @property
    def screensaver_mode(self) -> str:
        return self.db.get_setting("screensaver_mode", "digital_clock")

    @screensaver_mode.setter
    def screensaver_mode(self, value: str) -> None:
        self.db.set_setting("screensaver_mode", value)

    @property
    def screensaver_background_path(self) -> str:
        return self.db.get_setting("screensaver_background_path", "")

    @screensaver_background_path.setter
    def screensaver_background_path(self, value: str) -> None:
        self.db.set_setting("screensaver_background_path", value)
