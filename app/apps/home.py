"""Smart-home apps built on the entity board."""
from __future__ import annotations

from app.apps.kit import AppContext, BoardSpec, EntityBoard, number, tr

_LIGHT_WORDS = ("licht", "lampe", "leuchte", "light")
_SWITCH_NOISE = (
    "crossfade", "loudness", "autoplay", "alarm", "gruppierung", "surround", "night_sound", "speech",
    "buzzer", "soft_wind", "evaporator", "health", "anti_frost", "eco_mode", "self_cleaning", "led",
)
_SECURITY_CLASSES = ("door", "window", "opening", "motion", "smoke", "moisture", "problem", "garage_door", "lock")


def _text(entity) -> str:
    return f"{entity.friendly_name} {entity.entity_id}".lower()


def _lights() -> BoardSpec:
    def select(e):
        return e.domain == "light" or (
            e.domain == "switch" and any(w in _text(e) for w in _LIGHT_WORDS) and not any(n in _text(e) for n in _SWITCH_NOISE))

    def describe(e):
        level = e.attributes.get("brightness")
        return tr(e.state) + (f" · {round(level / 2.55)} %" if level and e.state == "on" else "")

    def actions(e):
        base = [("An", e.domain, "turn_on", {}), ("Aus", e.domain, "turn_off", {})]
        return base + ([("50 %", "light", "turn_on", {"brightness_pct": 50})] if e.domain == "light" else [])

    return BoardSpec("Lichter", select, describe, lambda e: e.friendly_name.casefold(), actions,
                     tone=lambda e: "ok" if e.state == "on" else "", empty="Keine Lichter in Home Assistant gefunden.")


def _switches() -> BoardSpec:
    def select(e):
        return (e.domain in ("switch", "input_boolean")) and not any(n in _text(e) for n in _SWITCH_NOISE) \
            and e.state != "unavailable"

    return BoardSpec("Schalter", select, lambda e: tr(e.state), lambda e: e.friendly_name.casefold(),
                     lambda e: [("An", e.domain, "turn_on", {}), ("Aus", e.domain, "turn_off", {})],
                     tone=lambda e: "ok" if e.state == "on" else "")


def _scenes() -> BoardSpec:
    return BoardSpec(
        "Szenen & Skripte", lambda e: e.domain in ("scene", "script"),
        lambda e: "Szene" if e.domain == "scene" else "Skript", lambda e: (e.domain, e.friendly_name.casefold()),
        lambda e: [("Starten", e.domain, "turn_on", {})], empty="Keine Szenen oder Skripte vorhanden.")


def _climate() -> BoardSpec:
    def describe(e):
        a = e.attributes
        parts = [tr(e.state)]
        if a.get("current_temperature") is not None:
            parts.append(f"Ist {a['current_temperature']} °C")
        if a.get("temperature") is not None:
            parts.append(f"Soll {a['temperature']} °C")
        return " · ".join(parts)

    def actions(e):
        target = e.attributes.get("temperature")
        result = []
        if target is not None:
            step = float(e.attributes.get("target_temp_step") or 0.5)
            result += [("−", "climate", "set_temperature", {"temperature": round(float(target) - step, 1)}),
                       ("+", "climate", "set_temperature", {"temperature": round(float(target) + step, 1)})]
        result.append(("Aus" if e.state != "off" else "An", "climate", "turn_off" if e.state != "off" else "turn_on", {}))
        return result

    return BoardSpec("Heizung & Klima", lambda e: e.domain == "climate", describe,
                     lambda e: e.friendly_name.casefold(), actions,
                     tone=lambda e: "ok" if e.state not in ("off", "unavailable") else "")


def _covers() -> BoardSpec:
    def describe(e):
        position = e.attributes.get("current_position")
        return tr(e.state) + (f" · {position} %" if position is not None else "")

    return BoardSpec(
        "Rollläden", lambda e: e.domain == "cover", describe, lambda e: e.friendly_name.casefold(),
        lambda e: [("Auf", "cover", "open_cover", {}), ("Stopp", "cover", "stop_cover", {}),
                   ("Zu", "cover", "close_cover", {})])


def _automations() -> BoardSpec:
    return BoardSpec(
        "Automationen", lambda e: e.domain == "automation",
        lambda e: "Aktiv" if e.state == "on" else "Ausgeschaltet", lambda e: e.friendly_name.casefold(),
        lambda e: [("Umschalten", "automation", "toggle", {}), ("Auslösen", "automation", "trigger", {})],
        tone=lambda e: "ok" if e.state == "on" else "warn")


def _batteries() -> BoardSpec:
    def select(e):
        return e.domain == "sensor" and e.attributes.get("device_class") == "battery" and number(e) is not None

    def tone(e):
        level = number(e) or 0
        return "bad" if level < 15 else "warn" if level < 30 else "ok"

    return BoardSpec("Batterien", select, lambda e: f"{number(e):.0f} %", lambda e: number(e) or 0, lambda e: [],
                     tone=tone, empty="Keine Batteriesensoren gefunden.", columns=3)


def _presence() -> BoardSpec:
    return BoardSpec(
        "Anwesenheit", lambda e: e.domain in ("person", "device_tracker"), lambda e: tr(e.state),
        lambda e: (e.domain, e.friendly_name.casefold()), lambda e: [],
        tone=lambda e: "ok" if e.state == "home" else "", empty="Keine Personen oder Geräte gefunden.", columns=3)


def _security() -> BoardSpec:
    def select(e):
        if e.domain in ("lock", "alarm_control_panel"):
            return True
        return e.domain == "binary_sensor" and e.attributes.get("device_class") in _SECURITY_CLASSES \
            and e.state != "unavailable"

    def describe(e):
        if e.domain == "binary_sensor":
            on = e.state == "on"
            words = {"door": ("Offen", "Zu"), "window": ("Offen", "Zu"), "opening": ("Offen", "Zu"),
                     "garage_door": ("Offen", "Zu"), "motion": ("Bewegung", "Ruhig"),
                     "smoke": ("RAUCH!", "OK"), "moisture": ("NASS!", "Trocken"), "problem": ("Problem", "OK")}
            return words.get(e.attributes.get("device_class"), ("An", "Aus"))[0 if on else 1]
        return tr(e.state)

    def tone(e):
        if e.domain == "binary_sensor" and e.state == "on":
            return "bad" if e.attributes.get("device_class") in ("smoke", "moisture", "problem") else "warn"
        return "bad" if e.state == "triggered" else "ok"

    def actions(e):
        return [("Verriegeln", "lock", "lock", {})] if e.domain == "lock" else []

    return BoardSpec("Sicherheit", select, describe, lambda e: (e.domain, e.friendly_name.casefold()),
                     actions, tone=tone, empty="Keine Sicherheits-Sensoren gefunden.", columns=3)


def _consumers() -> BoardSpec:
    def select(e):
        value = number(e)
        return e.domain == "sensor" and e.attributes.get("device_class") == "power" and value is not None and value >= 1

    return BoardSpec("Verbraucher", select,
                     lambda e: f"{number(e):.0f} {e.attributes.get('unit_of_measurement', 'W')}",
                     lambda e: -(number(e) or 0), lambda e: [], tone=lambda e: "ok", limit=24, columns=3,
                     empty="Aktuell verbraucht kein Gerät messbar Strom.")


def _temperatures() -> BoardSpec:
    def select(e):
        return e.domain == "sensor" and e.attributes.get("device_class") == "temperature" and number(e) is not None

    return BoardSpec("Temperaturen", select,
                     lambda e: f"{number(e):.1f} {e.attributes.get('unit_of_measurement', '°C')}",
                     lambda e: e.friendly_name.casefold(), lambda e: [], columns=3,
                     empty="Keine Temperatursensoren gefunden.")


BOARDS = {
    "lights": _lights, "switches": _switches, "scenes": _scenes, "climate": _climate, "covers": _covers,
    "automations": _automations, "batteries": _batteries, "presence": _presence, "security": _security,
    "consumers": _consumers, "temperatures": _temperatures,
}


def board_factory(key: str):
    def factory(ctx: AppContext):
        return EntityBoard(ctx, BOARDS[key]())
    return factory
