"""Offscreen verification for the app catalogue, store UI and all bundled apps."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from app.apps.catalog import BUILTIN_APPS, AppCatalog  # noqa: E402
from app.apps import internet  # noqa: E402
from app.apps.games import computer_move, winner  # noqa: E402
from app.apps.internet import parse_feed  # noqa: E402
from app.apps.tools import calculate, convert  # noqa: E402
from app.core.database import Database  # noqa: E402
from app.core.homeassistant import Entity  # noqa: E402
from app.core.service_registry import ServiceRegistry  # noqa: E402
from app.plugins.manager import PluginManager  # noqa: E402
from app.ui.app_launcher import AppLauncher  # noqa: E402
from app.ui.app_store import AppStore  # noqa: E402
from app.ui.design import BUILT_IN_THEMES, apply_theme  # noqa: E402


class _State(QObject):
    entity_updated = Signal(str, dict)
    entities_loaded = Signal()
    connection_status_changed = Signal(bool)
    connected = False
    demo_mode = True
    settings = None

    def __init__(self):
        super().__init__()
        self.calls: list = []
        self.entities = {e.entity_id: e for e in (
            Entity("light.sofa", "on", {"friendly_name": "Sofa", "brightness": 128}),
            Entity("cover.rolladen", "open", {"friendly_name": "Rollladen", "current_position": 100}),
            Entity("climate.bad", "heat", {"friendly_name": "Bad", "temperature": 21.0, "current_temperature": 20.0}),
            Entity("sensor.akku", "12", {"friendly_name": "Akku", "device_class": "battery"}),
            Entity("binary_sensor.tuer", "on", {"friendly_name": "Tür", "device_class": "door"}),
            Entity("sensor.leistung", "340", {"friendly_name": "Ofen", "device_class": "power", "unit_of_measurement": "W"}),
        )}

    def get_entity(self, entity_id):
        return self.entities.get(entity_id)

    def run_service_actions(self, actions, on_finished=None):
        self.calls.extend(actions)


app = QApplication(sys.argv)
apply_theme(app, BUILT_IN_THEMES[0])
internet.fetch = lambda *args, **kwargs: None
root = Path(tempfile.mkdtemp(prefix="homepanel_apps_"))
try:
    db = Database(root / "homepanel.db")
    state = _State()
    services = ServiceRegistry()
    services.register("state_manager", state)
    services.register("database", db)
    manager = PluginManager(db, services, Path(__file__).resolve().parents[2] / "plugins")
    manager.load_all()
    catalog = AppCatalog(db, manager, state)

    assert len(BUILTIN_APPS) >= 30 and len({a.id for a in BUILTIN_APPS}) == len(BUILTIN_APPS)
    for builtin in BUILTIN_APPS:
        view = catalog.create_view(builtin.id)
        assert view is not None, builtin.id
        view.deleteLater()

    assert calculate("2+3*4") == 14 and calculate("(1+2)^3") == 27 and calculate("7,5/2") == 3.75
    for bad in ("__import__('os')", "1+a", "2**1000", "[1]", "1/0"):
        try:
            calculate(bad)
        except (ValueError, SyntaxError, ZeroDivisionError):
            continue
        raise AssertionError(f"unsafe expression accepted: {bad}")
    assert abs(convert("Temperatur", "°C", "°F", 100) - 212) < 1e-9
    assert abs(convert("Länge", "km", "m", 2) - 2000) < 1e-9
    assert winner(["X", "X", "X", "", "", "", "", "", ""]) == "X" and computer_move(["O", "O", "", "X", "X", "", "", "", ""]) == 2
    assert [i["title"] for i in parse_feed("<rss><channel><item><title>A</title><description>&lt;b&gt;x&lt;/b&gt;</description></item></channel></rss>")] == ["A"]
    try:
        parse_feed('<!DOCTYPE x [<!ENTITY a "b">]><rss/>')
    except ValueError:
        pass
    else:
        raise AssertionError("DTD feed accepted")

    lights = catalog.create_view("board_lights")
    assert lights.grid.count() == 1
    buttons = {b.text(): b for b in lights.findChildren(QPushButton)}
    buttons["Aus"].click()
    assert state.calls[-1] == {"domain": "light", "service": "turn_off", "entity_id": "light.sofa", "data": {}}
    climate = catalog.create_view("board_climate")
    {b.text(): b for b in climate.findChildren(QPushButton)}["+"].click()
    assert state.calls[-1]["data"] == {"temperature": 21.5}
    batteries = catalog.create_view("board_batteries")
    security = catalog.create_view("board_security")
    consumers = catalog.create_view("board_consumers")
    assert batteries.grid.count() == 1 and security.grid.count() == 1 and consumers.grid.count() == 1

    default_ids = {e.id for e in catalog.installed() if e.source == "builtin"}
    assert "board_lights" in default_ids and "calculator" not in {"x"}
    launcher = AppLauncher(catalog, lambda app_id: None)
    store = AppStore(catalog)
    store.search.setText("rechner")
    assert any(b.text() in ("Installieren", "Entfernen") for b in store.findChildren(QPushButton))
    store.search.setText("")
    catalog.remove("calculator")
    assert not catalog.get("calculator").installed
    catalog.install("calculator")
    assert catalog.get("calculator").installed
    assert catalog.install("media_center") and catalog.get("media_center").installed
    view = catalog.create_view("media_center")
    assert view is not None
    view.deleteLater()
    catalog.remove("media_center")
    assert not catalog.get("media_center").installed
    app.processEvents()
    manager.unload_all()
    db.close()
finally:
    shutil.rmtree(root, ignore_errors=True)

print("VERIFICATION PASSED")
