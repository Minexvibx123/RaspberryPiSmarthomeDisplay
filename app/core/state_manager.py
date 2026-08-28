"""Central runtime hub: entity cache, connection status, demo mode.

Widgets never talk to Home Assistant directly - they go through the
StateManager. This keeps the panel responsive and offline-safe: the last
known state of every entity is always available locally, even mid-outage.
"""
from __future__ import annotations

import logging
import random
import time
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal

from app.core.homeassistant import Entity, HomeAssistantClient
from app.core.websocket import HomeAssistantWebSocket

logger = logging.getLogger(__name__)

DEMO_ENTITIES: list[dict] = [
    {"entity_id": "light.wohnzimmer_deckenlampe", "state": "on", "attributes": {"friendly_name": "Deckenlampe", "area": "Wohnzimmer", "brightness": 200}},
    {"entity_id": "light.wohnzimmer_stehlampe", "state": "off", "attributes": {"friendly_name": "Stehlampe", "area": "Wohnzimmer"}},
    {"entity_id": "light.kueche_arbeitslicht", "state": "on", "attributes": {"friendly_name": "Arbeitslicht", "area": "Küche", "brightness": 255}},
    {"entity_id": "switch.kaffeemaschine", "state": "off", "attributes": {"friendly_name": "Kaffeemaschine", "area": "Küche"}},
    {"entity_id": "sensor.wohnzimmer_temperatur", "state": "21.4", "attributes": {"friendly_name": "Temperatur", "area": "Wohnzimmer", "unit_of_measurement": "°C", "device_class": "temperature"}},
    {"entity_id": "sensor.aussen_temperatur", "state": "14.8", "attributes": {"friendly_name": "Außentemperatur", "area": "Garten", "unit_of_measurement": "°C", "device_class": "temperature"}},
    {"entity_id": "sensor.luftfeuchtigkeit", "state": "48", "attributes": {"friendly_name": "Luftfeuchtigkeit", "area": "Wohnzimmer", "unit_of_measurement": "%", "device_class": "humidity"}},
    {"entity_id": "climate.wohnzimmer", "state": "heat", "attributes": {"friendly_name": "Heizung Wohnzimmer", "area": "Wohnzimmer", "temperature": 21.5, "current_temperature": 21.0, "min_temp": 5, "max_temp": 30}},
    {"entity_id": "cover.wohnzimmer_rollladen", "state": "open", "attributes": {"friendly_name": "Rollladen", "area": "Wohnzimmer", "current_position": 100}},
    {"entity_id": "media_player.wohnzimmer_tv", "state": "playing", "attributes": {"friendly_name": "Wohnzimmer TV", "area": "Wohnzimmer", "media_title": "Demo Video", "media_artist": "Demo Artist", "media_duration": 240, "media_position": 42, "volume_level": 0.7, "is_volume_muted": False}},
    {"entity_id": "media_player.kueche", "state": "paused", "attributes": {"friendly_name": "Küchen-Lautsprecher", "area": "Küche", "media_title": "Podcast Folge 42", "media_artist": "Tech Talk DE", "media_duration": 3600, "media_position": 1200, "volume_level": 0.5, "is_volume_muted": False}},
    {"entity_id": "sensor.energie_verbrauch", "state": "1.8", "attributes": {"friendly_name": "Energieverbrauch", "area": "Haus", "unit_of_measurement": "kW", "device_class": "power"}},
    {"entity_id": "sensor.batterie_sensor", "state": "76", "attributes": {"friendly_name": "Sensor Batterie", "area": "Wohnzimmer", "unit_of_measurement": "%", "device_class": "battery"}},
    {"entity_id": "binary_sensor.haustuer", "state": "off", "attributes": {"friendly_name": "Haustür", "area": "Eingang", "device_class": "door"}},
    {"entity_id": "weather.home", "state": "cloudy", "attributes": {"friendly_name": "Wetter", "temperature": 16, "humidity": 55}},
    {"entity_id": "calendar.familie", "state": "on", "attributes": {"friendly_name": "Familienkalender", "message": "Zahnarzttermin", "start_time": "2026-08-20 09:00:00"}},
    {"entity_id": "todo.einkaufsliste", "state": "3", "attributes": {"friendly_name": "Einkaufsliste", "all_items": [{"summary": "Milch"}, {"summary": "Brot"}, {"summary": "Kaffee"}]}},
    {"entity_id": "alarm_control_panel.haus", "state": "disarmed", "attributes": {"friendly_name": "Alarmanlage", "area": "Haus"}},
    {"entity_id": "vacuum.wohnzimmer", "state": "docked", "attributes": {"friendly_name": "Saugroboter", "area": "Wohnzimmer", "battery_level": 88}},
    {"entity_id": "fan.wohnzimmer", "state": "on", "attributes": {"friendly_name": "Ventilator", "area": "Wohnzimmer", "percentage": 60}},
    {"entity_id": "lock.haustuer", "state": "locked", "attributes": {"friendly_name": "Haustür-Schloss", "area": "Eingang"}},
    {"entity_id": "humidifier.schlafzimmer", "state": "on", "attributes": {"friendly_name": "Luftbefeuchter", "area": "Schlafzimmer", "humidity": 45}},
    {"entity_id": "person.max", "state": "home", "attributes": {"friendly_name": "Max"}},
    {"entity_id": "input_number.zielwert", "state": "42", "attributes": {"friendly_name": "Zielwert", "min": 0, "max": 100}},
    {"entity_id": "input_select.modus", "state": "Automatik", "attributes": {"friendly_name": "Modus", "options": ["Automatik", "Manuell", "Urlaub"]}},
    {"entity_id": "camera.haustuer", "state": "idle", "attributes": {"friendly_name": "Haustür-Kamera", "area": "Eingang", "entity_picture": "/api/camera_proxy/camera.haustuer"}},
    {"entity_id": "camera.garten", "state": "idle", "attributes": {"friendly_name": "Gartenkamera", "area": "Garten", "entity_picture": "/api/camera_proxy/camera.garten"}},
    {"entity_id": "sensor.home_power_w", "state": "347", "attributes": {"friendly_name": "Hausleistung", "area": "Haus", "unit_of_measurement": "W", "device_class": "power"}},
    {"entity_id": "sensor.energy_today_kwh", "state": "4.2", "attributes": {"friendly_name": "Verbrauch heute", "area": "Haus", "unit_of_measurement": "kWh", "device_class": "energy"}},
]


class StateManager(QObject):
    entity_updated = Signal(str, dict)
    connection_status_changed = Signal(bool)
    entities_loaded = Signal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.client: Optional[HomeAssistantClient] = None
        self.ws: Optional[HomeAssistantWebSocket] = None
        self.entities: dict[str, Entity] = {}
        self.connected: bool = False
        self.last_connected_at: Optional[float] = None
        self.demo_mode: bool = settings.demo_mode

        self._demo_timer: Optional[QTimer] = None

    # ------------------------------------------------------------------ #
    def start(self) -> None:
        if self.demo_mode or not self.settings.ha_url:
            self._start_demo()
            return
        self.client = HomeAssistantClient(self.settings.ha_url, self.settings.ha_token)
        try:
            for e in self.client.get_states():
                self.entities[e.entity_id] = e
            self.entities_loaded.emit()
        except Exception:
            logger.warning("Initial REST fetch failed, will rely on websocket + retry")

        self.ws = HomeAssistantWebSocket(self.settings.ha_url, self.settings.ha_token)
        self.ws.connection_status.connect(self._on_connection_status)
        self.ws.state_changed.connect(self._on_state_changed)
        self.ws.start()

    def stop(self) -> None:
        if self.ws:
            self.ws.stop()
        if self._demo_timer:
            self._demo_timer.stop()

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self.entities.get(entity_id)

    def call_service(self, domain: str, service: str, entity_id: Optional[str] = None, **data) -> None:
        if self.demo_mode:
            self._simulate_service_call(domain, service, entity_id, **data)
            return
        if not self.client:
            return
        try:
            self.client.call_service(domain, service, entity_id, **data)
        except Exception:
            logger.exception("call_service failed (offline?)")

    def seconds_since_last_connection(self) -> Optional[float]:
        if self.last_connected_at is None:
            return None
        return time.time() - self.last_connected_at

    # ------------------------------------------------------------------ #
    def _on_connection_status(self, is_connected: bool) -> None:
        self.connected = is_connected
        if is_connected:
            self.last_connected_at = time.time()
            # refresh full state on reconnect in case events were missed
            try:
                if self.client:
                    for e in self.client.get_states():
                        self.entities[e.entity_id] = e
                    self.entities_loaded.emit()
            except Exception:
                logger.warning("Refresh after reconnect failed")
        self.connection_status_changed.emit(is_connected)

    def _on_state_changed(self, entity_id: str, new_state: dict) -> None:
        entity = Entity(entity_id, new_state.get("state", "unknown"), new_state.get("attributes", {}))
        self.entities[entity_id] = entity
        self.entity_updated.emit(entity_id, new_state)

    # ------------------------------------------------------------------ #
    # demo mode: no Home Assistant required, entities update themselves
    # ------------------------------------------------------------------ #
    def _start_demo(self) -> None:
        self.demo_mode = True
        for raw in DEMO_ENTITIES:
            self.entities[raw["entity_id"]] = Entity(raw["entity_id"], raw["state"], dict(raw["attributes"]))
        self.entities_loaded.emit()
        self.connected = True
        self.last_connected_at = time.time()
        self.connection_status_changed.emit(True)

        self._demo_timer = QTimer(self)
        self._demo_timer.timeout.connect(self._demo_tick)
        self._demo_timer.start(5000)

    def _demo_tick(self) -> None:
        for entity_id, entity in list(self.entities.items()):
            if entity_id == "sensor.home_power_w":
                val = max(20.0, float(entity.state) + random.uniform(-45, 45))
                entity.state = f"{val:.0f}"
                self.entity_updated.emit(entity_id, {"state": entity.state, "attributes": entity.attributes})
                continue
            if entity_id == "sensor.energy_today_kwh":
                val = float(entity.state) + random.uniform(0.002, 0.02)
                entity.state = f"{val:.2f}"
                self.entity_updated.emit(entity_id, {"state": entity.state, "attributes": entity.attributes})
                continue
            if entity.domain == "sensor" and entity.attributes.get("device_class") in ("temperature", "humidity", "power", "battery"):
                try:
                    val = float(entity.state)
                except ValueError:
                    continue
                val += random.uniform(-0.3, 0.3)
                entity.state = f"{val:.1f}"
                self.entity_updated.emit(entity_id, {"state": entity.state, "attributes": entity.attributes})

    def _simulate_service_call(self, domain: str, service: str, entity_id: Optional[str], **data) -> None:
        if not entity_id or entity_id not in self.entities:
            return
        entity = self.entities[entity_id]
        if domain in ("light", "switch") and service in ("turn_on", "turn_off", "toggle"):
            if service == "toggle":
                entity.state = "off" if entity.state == "on" else "on"
            else:
                entity.state = "on" if service == "turn_on" else "off"
            if "brightness" in data:
                entity.attributes["brightness"] = data["brightness"]
        elif domain == "cover":
            if service == "open_cover":
                entity.state = "open"
                entity.attributes["current_position"] = 100
            elif service == "close_cover":
                entity.state = "closed"
                entity.attributes["current_position"] = 0
            elif service == "set_cover_position":
                pos = data.get("position", 50)
                entity.attributes["current_position"] = pos
                entity.state = "open" if pos > 0 else "closed"
        elif domain == "climate" and service == "set_temperature":
            entity.attributes["temperature"] = data.get("temperature")
        elif domain == "fan":
            if service == "toggle":
                entity.state = "off" if entity.state == "on" else "on"
            elif service in ("turn_on", "turn_off"):
                entity.state = "on" if service == "turn_on" else "off"
            elif service == "set_percentage":
                entity.attributes["percentage"] = data.get("percentage", 50)
                entity.state = "on"
        elif domain == "lock":
            entity.state = "locked" if service == "lock" else "unlocked"
        elif domain == "humidifier" and service == "toggle":
            entity.state = "off" if entity.state == "on" else "on"
        elif domain == "vacuum":
            if service == "start":
                entity.state = "cleaning"
            elif service == "return_to_base":
                entity.state = "docked"
        elif domain == "alarm_control_panel":
            entity.state = "armed_away" if service == "alarm_arm_away" else "disarmed"
        elif domain in ("select", "input_select") and service == "select_option":
            entity.state = data.get("option", entity.state)
        elif domain in ("number", "input_number") and service == "set_value":
            entity.state = str(data.get("value", entity.state))
        self.entity_updated.emit(entity_id, {"state": entity.state, "attributes": entity.attributes})
