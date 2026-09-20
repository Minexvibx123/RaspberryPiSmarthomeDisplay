"""Central registry mapping widget-type strings to their implementing class.

Adding a brand-new widget type later only means: write the class, import it
here, append it to WIDGET_CLASSES. Nothing else in the editor/dashboard
needs to change - this is the plugin seam mentioned in the architecture.
"""
from __future__ import annotations

from app.widgets.base import BaseWidget
from app.widgets.button import ButtonWidget
from app.widgets.camera import CameraWidget
from app.widgets.clock import ClockWidget
from app.widgets.console import ConsoleWidget
from app.widgets.container import ContainerWidget
from app.widgets.cover import CoverWidget
from app.widgets.custom_widget import CustomWidget
from app.widgets.energy import EnergyWidget
from app.widgets.entity_list import EntityListWidget
from app.widgets.ha_extra import (
    AlarmPanelWidget, CalendarWidget, FanWidget, HumidifierWidget, LockWidget,
    NumberInputWidget, PersonWidget, SceneGridWidget, SelectWidget,
    TodoListWidget, VacuumWidget,
)
from app.widgets.icon_widget import IconWidget
from app.widgets.internet import (
    CryptoPriceWidget, CurrencyWidget, HolidayWidget, InternetStatusWidget,
    JokeWidget, NewsWidget, QuoteWidget, StockPriceWidget, SystemMonitorWidget,
)
from app.widgets.light import LightWidget
from app.widgets.media_player import MediaPlayerWidget
from app.widgets.notification import NotificationWidget
from app.widgets.sensor import SensorWidget
from app.widgets.sensor_graph import SensorGraphWidget
from app.widgets.slider import SliderWidget
from app.widgets.switch import SwitchWidget
from app.widgets.text import TextWidget
from app.widgets.thermostat import ThermostatWidget
from app.widgets.timer import TimerWidget
from app.widgets.weather import WeatherWidget
from app.widgets.weather_api import WeatherApiWidget
from app.widgets.web import WebWidget

WIDGET_CLASSES: list[type[BaseWidget]] = [
    ButtonWidget, LightWidget, SwitchWidget, SliderWidget, ThermostatWidget,
    SensorWidget, CoverWidget, WeatherWidget, WeatherApiWidget, ClockWidget, TextWidget,
    IconWidget, EntityListWidget,
    # Home Assistant domain coverage
    CalendarWidget, TodoListWidget, AlarmPanelWidget, VacuumWidget, FanWidget,
    LockWidget, HumidifierWidget, PersonWidget, SceneGridWidget,
    NumberInputWidget, SelectWidget,
    # internet-sourced / system information
    CryptoPriceWidget, StockPriceWidget, CurrencyWidget, QuoteWidget,
    JokeWidget, HolidayWidget, InternetStatusWidget, SystemMonitorWidget,
    NewsWidget,
    CameraWidget, ContainerWidget, MediaPlayerWidget, NotificationWidget,
    SensorGraphWidget, TimerWidget,
    ConsoleWidget, EnergyWidget,
    WebWidget,
    CustomWidget,
]

WIDGET_REGISTRY: dict[str, type[BaseWidget]] = {cls.type_name: cls for cls in WIDGET_CLASSES}


def widget_class(type_name: str) -> type[BaseWidget]:
    return WIDGET_REGISTRY.get(type_name, BaseWidget)


def widgets_by_category() -> dict[str, list[type[BaseWidget]]]:
    grouped: dict[str, list[type[BaseWidget]]] = {}
    for cls in WIDGET_CLASSES:
        grouped.setdefault(cls.category, []).append(cls)
    return grouped


def register_widget_class(cls: type[BaseWidget]) -> None:
    """Register a widget class at runtime (used by plugins). Idempotent."""
    if cls.type_name in WIDGET_REGISTRY:
        return
    WIDGET_CLASSES.append(cls)
    WIDGET_REGISTRY[cls.type_name] = cls


def unregister_widget_class(type_name: str) -> None:
    """Remove a dynamically registered widget type when its plugin unloads."""
    cls = WIDGET_REGISTRY.pop(type_name, None)
    if cls is not None:
        WIDGET_CLASSES.remove(cls)
