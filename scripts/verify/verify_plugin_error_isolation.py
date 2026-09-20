"""Error isolation + widget registration verification for the Phase 1 plugin system.

Uses a temp DB and temp plugins root. Creates deliberately broken plugins and
verifies none of them can crash the manager or the app, plus verifies the
register_widget_class seam with a plugin that registers a real widget class.

No Qt needed (manager-level tests only).
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

logging.basicConfig(level=logging.CRITICAL)  # silence expected error logs

from app.core.database import Database  # noqa: E402
from app.core.service_registry import ServiceRegistry  # noqa: E402
from app.plugins.manager import PluginManager  # noqa: E402
from app.widgets import registry as widget_registry  # noqa: E402

# baseline: capture the built-in widget registry BEFORE any plugin loads
before_types = set(widget_registry.WIDGET_REGISTRY.keys())
builtin_count = len(widget_registry.WIDGET_REGISTRY)

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: Any = "") -> None:
    status = "OK  " if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


tmp = Path(tempfile.mkdtemp(prefix="homepanel_plugin_test_"))
plugins_root = tmp / "plugins"
plugins_root.mkdir()
db = Database(tmp / "test.db")
services = ServiceRegistry()
services.register("database", db)
services.register("dummy", object())

GOOD_MANIFEST = {
    "id": "good_plugin", "name": "Gutes Plugin", "version": "1.0.0",
    "enabled": True, "category": "general",
}

DEPENDENT_MANIFEST = {
    "id": "dependent_plugin", "name": "Abhängiges Plugin", "version": "1.0.0",
    "enabled": True, "requires": ["good_plugin"],
}

# --- build the good plugin (valid) -------------------------------------- #
good = plugins_root / "good_plugin"
good.mkdir()
(good / "manifest.json").write_text(json.dumps(GOOD_MANIFEST, indent=2), encoding="utf-8")
(good / "plugin.py").write_text(textwrap.dedent('''
    from app.plugins.api import Plugin


    class Plugin(Plugin):
        def on_load(self):
            # prove services + namespaced settings reach the plugin
            db = self.services.resolve("database")
            assert db is not None
            self.settings.set("marker", "good")
            self.loaded_via = db
'''[1:]), encoding="utf-8")

# --- dependent plugin: sorts before its dependency, must load afterwards -- #
dependent = plugins_root / "dependent_plugin"
dependent.mkdir()
(dependent / "manifest.json").write_text(json.dumps(DEPENDENT_MANIFEST, indent=2), encoding="utf-8")
(dependent / "plugin.py").write_text(textwrap.dedent('''
    from app.plugins.api import Plugin


    class Plugin(Plugin):
        def on_load(self):
            self.settings.set("dependency_loaded", True)
'''[1:]), encoding="utf-8")

# --- package plugin: proves local API/widget modules can use relative imports #
package_plugin = plugins_root / "package_plugin"
package_plugin.mkdir()
(package_plugin / "manifest.json").write_text(json.dumps(
    {"id": "package_plugin", "name": "Paket Plugin", "version": "1.0.0"}, indent=2), encoding="utf-8")
(package_plugin / "api.py").write_text("MARKER = 'relative import works'\n", encoding="utf-8")
(package_plugin / "plugin.py").write_text(textwrap.dedent('''
    from app.plugins.api import Plugin
    from .api import MARKER


    class Plugin(Plugin):
        def on_load(self):
            self.settings.set("import_marker", MARKER)
'''[1:]), encoding="utf-8")

# --- missing dependency: must report an error without affecting others --- #
missing_dependency = plugins_root / "missing_dependency"
missing_dependency.mkdir()
(missing_dependency / "manifest.json").write_text(json.dumps(
    {"id": "missing_dependency", "name": "Fehlende Abhängigkeit", "version": "1.0.0", "requires": ["does_not_exist"]},
    indent=2), encoding="utf-8")
(missing_dependency / "plugin.py").write_text("from app.plugins.api import Plugin\n", encoding="utf-8")

# --- broken plugin 1: invalid manifest JSON ------------------------------ #
broken_manifest = plugins_root / "broken_manifest"
broken_manifest.mkdir()
(broken_manifest / "manifest.json").write_text("{ not json", encoding="utf-8")

# --- broken plugin 2: import raises -------------------------------------- #
broken_import = plugins_root / "broken_import"
broken_import.mkdir()
(broken_import / "manifest.json").write_text(json.dumps(
    {"id": "broken_import", "name": "Kaputt Import", "version": "1.0.0", "enabled": True},
    indent=2), encoding="utf-8")
(broken_import / "plugin.py").write_text("raise RuntimeError('kaputt beim import')\n", encoding="utf-8")

# --- broken plugin 3: no Plugin class ------------------------------------ #
no_class = plugins_root / "no_class"
no_class.mkdir()
(no_class / "manifest.json").write_text(json.dumps(
    {"id": "no_class", "name": "Keine Klasse", "version": "1.0.0", "enabled": True},
    indent=2), encoding="utf-8")
(no_class / "plugin.py").write_text("x = 42\n", encoding="utf-8")

# --- broken plugin 4: on_load raises ------------------------------------- #
load_raises = plugins_root / "load_raises"
load_raises.mkdir()
(load_raises / "manifest.json").write_text(json.dumps(
    {"id": "load_raises", "name": "Load Kaputt", "version": "1.0.0", "enabled": True},
    indent=2), encoding="utf-8")
(load_raises / "plugin.py").write_text(textwrap.dedent('''
    from app.plugins.api import Plugin


    class Plugin(Plugin):
        def on_load(self):
            raise ValueError("on_load explodiert")
'''[1:]), encoding="utf-8")

# --- broken plugin 5: register_widgets raises ----------------------------- #
reg_raises = plugins_root / "reg_raises"
reg_raises.mkdir()
(reg_raises / "manifest.json").write_text(json.dumps(
    {"id": "reg_raises", "name": "Reg Kaputt", "version": "1.0.0", "enabled": True},
    indent=2), encoding="utf-8")
(reg_raises / "plugin.py").write_text(textwrap.dedent('''
    from app.plugins.api import Plugin


    class Plugin(Plugin):
        def register_widgets(self):
            raise RuntimeError("widget registrierung explodiert")
'''[1:]), encoding="utf-8")

# --- widget plugin: registers a real widget class ------------------------- #
widget_plugin = plugins_root / "widget_plugin"
widget_plugin.mkdir()
(widget_plugin / "manifest.json").write_text(json.dumps(
    {"id": "widget_plugin", "name": "Widget Plugin", "version": "2.0.0", "enabled": True},
    indent=2), encoding="utf-8")
(widget_plugin / "plugin.py").write_text(textwrap.dedent('''
    from app.plugins.api import Plugin
    from app.widgets.base import BaseWidget
    from app.widgets.registry import register_widget_class


    class MyTestWidget(BaseWidget):
        type_name = "test_widget_plugin"
        display_name = "Test Widget Plugin"
        category = "Plugins"
        icon = "\\U0001F4E6"
        default_size = (200, 140)


    class Plugin(Plugin):
        def register_widgets(self):
            register_widget_class(MyTestWidget)
'''[1:]), encoding="utf-8")

# --- manager-level tests -------------------------------------------------- #
pm = PluginManager(db, services, plugins_root)
pm.load_all()  # MUST NOT raise despite 5 broken plugins

infos = {i.id: i for i in pm.list_plugins()}

# good plugin loads
check("good_plugin enabled", infos["good_plugin"].state == "enabled", infos["good_plugin"].state)
check("good_plugin instance loaded", pm.get_instance("good_plugin") is not None)
check("good_plugin services+settings worked",
      db.get_setting("plugin.good_plugin.marker") == "good",
      f"marker={db.get_setting('plugin.good_plugin.marker')}")
check("dependent plugin loaded after requirement", infos["dependent_plugin"].state == "enabled",
    infos["dependent_plugin"].state)
check("dependent plugin lifecycle ran", db.get_setting("plugin.dependent_plugin.dependency_loaded") is True)
check("local relative import plugin loaded", infos["package_plugin"].state == "enabled",
    infos["package_plugin"].state)
check("local relative import lifecycle ran",
    db.get_setting("plugin.package_plugin.import_marker") == "relative import works")
check("missing dependency isolated", infos["missing_dependency"].state == "error",
    infos["missing_dependency"].error)

# isolation: all broken plugins produce error state, never raise
check("broken_manifest isolated", infos["broken_manifest"].state == "error",
      f"{infos['broken_manifest'].state}: {infos['broken_manifest'].error}")
check("broken_import isolated", infos["broken_import"].state == "error",
      f"{infos['broken_import'].state}: {infos['broken_import'].error}")
check("no_class isolated", infos["no_class"].state == "error",
      f"{infos['no_class'].state}: {infos['no_class'].error}")
check("load_raises isolated", infos["load_raises"].state == "error",
      f"{infos['load_raises'].state}: {infos['load_raises'].error}")
check("load_raises NOT in instances", pm.get_instance("load_raises") is None)
check("reg_raises isolated", infos["reg_raises"].state == "error",
      f"{infos['reg_raises'].state}: {infos['reg_raises'].error}")

# error strings are meaningful (German, per project style)
check("error message is human-readable",
      "Import fehlgeschlagen" in (infos["broken_import"].error or ""),
      infos["broken_import"].error)
check("on_load error message",
      "on_load fehlgeschlagen" in (infos["load_raises"].error or ""),
      infos["load_raises"].error)
check("manifest error message",
      "Ungültiges Manifest" in (infos["broken_manifest"].error or ""),
      infos["broken_manifest"].error)

# disable a broken plugin must not raise either
ok = pm.disable("load_raises")
check("disable broken plugin ok", ok and infos["load_raises"].state == "error")

# --- widget registration ------------------------------------------------- #
check("widget_plugin enabled", infos["widget_plugin"].state == "enabled", infos["widget_plugin"].state)
check("widget type registered", "test_widget_plugin" in widget_registry.WIDGET_REGISTRY,
      list(widget_registry.WIDGET_REGISTRY.keys())[-3:])
check("widget type maps to plugin classes",
      widget_registry.WIDGET_REGISTRY["test_widget_plugin"].__module__.startswith("_homepanel_plugin_widget_plugin"),
      widget_registry.WIDGET_REGISTRY["test_widget_plugin"].__module__)
check("widget type count grew by exactly one after load",
      len(widget_registry.WIDGET_REGISTRY) == builtin_count + 1,
      f"before={builtin_count} now={len(widget_registry.WIDGET_REGISTRY)}")

# idempotency: reload must not duplicate the registration
pm.reload("widget_plugin")
check("reload keeps plugin enabled", pm.get_instance("widget_plugin") is not None)
check("reload keeps widget registered",
      widget_registry.WIDGET_REGISTRY["test_widget_plugin"] is not None)
check("widget type count unchanged after reload",
      len(widget_registry.WIDGET_REGISTRY) == builtin_count + 1,
      f"before={builtin_count} now={len(widget_registry.WIDGET_REGISTRY)}")

# unload plugin -> its dynamic widget type is no longer available
pm.disable("widget_plugin")
check("widget plugin disabled ok", all(
    i.state == "disabled" for i in pm.list_plugins() if i.id == "widget_plugin"))
check("unload removes plugin widget", "test_widget_plugin" not in widget_registry.WIDGET_REGISTRY)

# --- cleanup ------------------------------------------------------------- #
shutil.rmtree(tmp, ignore_errors=True)

print()
if FAILURES:
    print(f"VERIFICATION FAILED: {FAILURES}")
    sys.exit(1)
print("VERIFICATION PASSED")
sys.exit(0)