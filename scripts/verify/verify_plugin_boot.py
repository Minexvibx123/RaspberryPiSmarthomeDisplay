"""Headless boot verification for the Phase 1 plugin system.

Boots the real MainWindow offscreen (QT_QPA_PLATFORM=offscreen) and verifies:
  1. the app starts without crashing,
  2. the example plugin is discovered and enabled ("geladen" via manager),
  3. the SettingsScreen Plugins tab lists "Beispiel Plugin v1.0.0 [enabled]".

Usage: QT_QPA_PLATFORM=offscreen python scripts/verify/verify_plugin_boot.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QListWidget

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "OK  " if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


app = QApplication(sys.argv)
from app.ui.main_window import MainWindow  # noqa: E402  (needs QApplication first)

window = MainWindow(app)

# --- 1. App booted and plugin manager wired --------------------------- #
check("Booting MainWindow", "plugin_manager" in vars(window) or hasattr(window, "plugin_manager"))
pm = window.plugin_manager
check("PluginManager created", pm is not None)

# --- 2. Example plugin discovered + enabled --------------------------- #
infos = pm.list_plugins()
ids = [i.id for i in infos]
check("Example plugin discovered", "example_plugin" in ids, f"ids={ids}")
example = next((i for i in infos if i.id == "example_plugin"), None)
check("Example plugin state enabled", example is not None and example.state == "enabled",
      f"state={example.state if example else None}")
check("Example plugin version 1.0.0", example is not None and example.version == "1.0.0",
      f"version={example.version if example else None}")
system_monitor = next((info for info in infos if info.id == "system_monitor"), None)
check("System monitor plugin discovered", system_monitor is not None)
check("System monitor plugin enabled", system_monitor is not None and system_monitor.state == "enabled",
    f"state={system_monitor.state if system_monitor else None}")
from app.widgets.registry import WIDGET_REGISTRY  # noqa: E402
check("System monitor widgets registered", all(widget_type in WIDGET_REGISTRY for widget_type in (
    "system_cpu", "system_ram", "system_storage", "system_network",
)))
check("No plugin errors", all(i.error is None for i in infos), f"errors={[(i.id, i.error) for i in infos if i.error]}")
check("Instance loaded", pm.get_instance("example_plugin") is not None)

# settings marker written by on_load -> lifecycle really ran
saved = window.db.get_setting("plugin.example_plugin.loaded", None)
check("on_load ran (settings marker written)", saved is True, f"marker={saved}")

# --- 3. Plugins tab in SettingsScreen shows the plugin ----------------- #
check("SettingsScreen exists", hasattr(window, "settings_screen"))
tab = window.settings_screen._plugin_list  # the QListWidget with plugin entries
check("Plugin list widget present", isinstance(tab, QListWidget), type(tab).__name__)
rows = [tab.item(i).text() for i in range(tab.count())]
check("Plugins tab has installed plugins", len(rows) >= 2, f"rows={rows}")
check("Row shows name+version+state", any("Beispiel Plugin v1.0.0 [enabled]" in r for r in rows), f"rows={rows}")
example_instance = pm.get_instance("example_plugin")
schema = getattr(example_instance, "settings_schema", [])
check("Plugin declares settings schema", len(schema) == 4, f"schema={schema}")
check("Plugin settings schema is valid", all(definition.validate() is None for definition in schema))
check("Plugin settings control exists", window.settings_screen._plugin_settings_btn is not None)

# --- 4. UI callbacks: disable -> enable -> reload ---------------------- #
def select_row(text_fragment: str) -> None:
    for i in range(tab.count()):
        if text_fragment in tab.item(i).text():
            tab.setCurrentRow(i)
            return
    raise AssertionError(f"row '{text_fragment}' not found in {rows}")

select_row("Beispiel Plugin")
window.settings_screen._disable_selected_plugin()
rows = [tab.item(i).text() for i in range(tab.count())]
check("Disable via UI -> state disabled", any("Beispiel Plugin v1.0.0 [disabled]" in row for row in rows), f"rows={rows}")
check("Disable persists override", window.db.get_setting("plugin.enabled.example_plugin", None) is False)

select_row("Beispiel Plugin")
window.settings_screen._enable_selected_plugin()
rows = [tab.item(i).text() for i in range(tab.count())]
check("Enable via UI -> state enabled", any("Beispiel Plugin v1.0.0 [enabled]" in row for row in rows), f"rows={rows}")
check("Enable clears override", window.db.get_setting("plugin.enabled.example_plugin", None) is True)

select_row("Beispiel Plugin")
window.settings_screen._reload_selected_plugin()
rows = [tab.item(i).text() for i in range(tab.count())]
check("Reload via UI -> still enabled", any("Beispiel Plugin v1.0.0 [enabled]" in row for row in rows), f"rows={rows}")
check("Reload kept instance", pm.get_instance("example_plugin") is not None)
count = window.db.get_setting("plugin.example_plugin.load_count", 0)
check("Reload ran on_load again (load_count incremented)", int(count or 0) >= 2, f"load_count={count}")

# --- 5. Persistence: fresh manager on same DB honours override -------- #
window.plugin_manager.disable("example_plugin")
from app.plugins.manager import PluginManager  # noqa: E402
pm2 = PluginManager(window.db, window.services, pm.plugins_root)
pm2.load_all()
state2 = {i.id: i.state for i in pm2.list_plugins()}
check("Fresh manager: disabled override survives restart", state2.get("example_plugin") == "disabled",
      f"states={state2}")
pm2.enable("example_plugin")
from app.plugins.plugin_settings import PluginSettings  # noqa: E402
_ = PluginSettings  # silence unused
check("Re-enable after restart", pm2.get_instance("example_plugin") is not None)

# restore clean override state so the dev DB keeps the manifest default
window.db.set_setting("plugin.enabled.example_plugin", None)

print()
if FAILURES:
    print(f"VERIFICATION FAILED: {FAILURES}")
    sys.exit(1)
print("VERIFICATION PASSED")
sys.exit(0)