# AI-CONTEXT – HomePanel Technical Reference

> **Purpose**: This file provides a comprehensive technical summary of the HomePanel project for AI assistants that need to understand, modify, or extend this codebase. Read this file FIRST before touching any code.

---

## 1. What This Project Is

**HomePanel** is a native PySide6 (Qt6) touch-panel application that serves as a highly customizable Home Assistant dashboard. It runs on a Raspberry Pi 5 with the official 7" touchscreen display.

**Core Value Proposition**: Users can visually design their home dashboard by dragging, dropping, resizing, and configuring widgets directly on the touchscreen — no YAML, no JSON, no code editing required.

**Current State**: The project is functional and running on physical hardware. It has a complete widget system, visual editor, theme system, deployment pipeline, a full Phase 1-5 plugin architecture (animations, conditional styling, safe expressions, custom widget builder, a list-based workflow engine, and extended backup), plus real integrations for Flashforge, Pi-hole, Docker, local network devices, system monitoring, and an optional internal browser. Headless verification scripts in `scripts/verify_*.py` (16 as of this writing) cover plugin lifecycle/error isolation, widgets, conditions, animations, templates, backup, workflows, expressions, and the custom widget builder - run them after any change to the touched area.

---

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.14 |
| GUI Framework | PySide6 (Qt6 for Python) |
| Database | SQLite (via Python's built-in `sqlite3` module) |
| HTTP Client | `requests` library |
| WebSocket | `websocket-client` library |
| Display Server | `cage` (minimal Wayland compositor) |
| Display Rotation | `wlr-randr` (part of wlroots) |
| Init System | systemd |
| Target OS | Debian 13 (trixie) aarch64 on Raspberry Pi 5 |

**Dependencies** (`requirements.txt` — only 3 packages):
```
PySide6>=6.6
requests>=2.31
websocket-client>=1.7
```

---

## 3. Target Hardware

- **Board**: Raspberry Pi 5
- **Display**: Official Raspberry Pi 7" Touch Display 2
- **Display Interface**: DSI-2 (portrait-native: 720x1280)
- **User**: `supervisor` (groups: video, render, input)
- **SSH Access**: `ssh supervisor@192.168.178.138` (passwordless, SSH key)
- **Sudo**: `echo 0908 | sudo -S <command>`

**Critical Hardware Quirk**: The Pi 5 attaches the DSI panel to a SEPARATE DRM device (`/dev/dri/card1` = drm-rp1-dsi), while the GPU is on card0 (v3d) and HDMI on card2 (vc4). This means:
- Qt's `eglfs` backend **cannot work** — it needs Render+Display on the same DRM device → SIGABRT crashloop
- `linuxfb` works but cannot rotate
- **Solution**: `cage` (Wayland compositor) provides GPU acceleration + rotation + touch coordinate rotation via wlroots/libinput
- The systemd service uses `cage -d -- python -m app.main` with `QT_QPA_PLATFORM=wayland`
- Rotation is applied post-start: `wlr-randr --output DSI-2 --transform 90`

---

## 4. Project Structure

```
homepanel/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # Entry point: argparse, QApplication setup
│   ├── core/                     # Backend layer
│   │   ├── __init__.py
│   │   ├── homeassistant.py      # REST client (get_states, call_service, Entity dataclass)
│   │   ├── websocket.py          # WebSocket client with auto-reconnect
│   │   ├── database.py           # SQLite: pages, widgets, themes, settings tables
│   │   ├── state_manager.py      # Central entity cache, demo mode, service call routing
│   │   ├── settings.py           # Typed property wrapper around DB settings table
│   │   └── http_fetch.py         # HTTP fetching utilities
│   ├── ui/                       # Frontend/UI layer
│   │   ├── __init__.py
│   │   ├── main_window.py        # QMainWindow: standby state machine, view routing, wizard
│   │   ├── dashboard.py          # DashboardCanvas: widget rendering in normal+editor mode
│   │   ├── editor.py             # EditorScreen: toolbar, undo/redo, save/cancel
│   │   ├── properties.py         # Dynamic property panel (auto-generated from widget schemas)
│   │   ├── element_library.py    # Widget library sidebar + entity picker
│   │   ├── navigation.py         # Bottom bar / sidebar page navigation
│   │   ├── themes.py             # Theme presets, build_stylesheet(), ThemeManager
│   │   ├── setup_wizard.py       # First-run wizard (language, HA connection, demo mode)
│   │   └── settings_screen.py    # Settings: connection, design, backup/restore
│   └── widgets/                  # Widget implementations
│       ├── __init__.py
│       ├── base.py               # BaseWidget + PropertyDef + COMMON_SCHEMA
│       ├── registry.py           # WIDGET_CLASSES list, WIDGET_REGISTRY dict, widget_class()
│       ├── button.py             # ButtonWidget
│       ├── light.py              # LightWidget (brightness, color temp)
│       ├── switch.py             # SwitchWidget (toggle on/off)
│       ├── slider.py             # SliderWidget (range input)
│       ├── sensor.py             # SensorWidget (read-only value display)
│       ├── thermostat.py         # ThermostatWidget (temperature control)
│       ├── cover.py              # CoverWidget (blind/shutter position)
│       ├── weather.py            # WeatherWidget (from HA weather entity)
│       ├── clock.py              # ClockWidget (live clock display)
│       ├── text.py               # TextWidget (static/custom text)
│       ├── icon_widget.py        # IconWidget (custom icon display)
│       ├── entity_list.py        # EntityListWidget (list of entities)
│       ├── media_player.py       #MediaPlayerWidget (play/pause/volume)
│       ├── camera.py             # CameraWidget (camera proxy image)
│       ├── console.py            # ConsoleWidget (terminal output)
│       ├── energy.py             # EnergyWidget (power/energy display)
│       ├── container.py          # ContainerWidget (grouping)
│       ├── notification.py       # NotificationWidget (alerts)
│       ├── sensor_graph.py       # SensorGraphWidget (history graph)
│       ├── timer.py              # TimerWidget (countdown/stopwatch)
│       ├── ha_extra.py           # HA-specific widgets: Calendar, TodoList, AlarmPanel,
│       │                         #   Vacuum, Fan, Lock, Humidifier, Person, SceneGrid,
│       │                         #   NumberInput, Select
│       └── internet.py           # Internet widgets: CryptoPrice, StockPrice, Currency,
│                                 #   Quote, Joke, Holiday, InternetStatus, SystemMonitor,
│                                 #   News
├── data/                         # Runtime data
│   └── homepanel.db              # SQLite database (auto-created)
├── plugins/                      # Real Phase 3+ integrations (see AI-CONTEXT 5.6)
│   ├── example_plugin/           # Minimal reference plugin (lifecycle proof)
│   ├── system_monitor/           # CPU/RAM/Storage/Network/Service widgets, /proc + /sys only
│   ├── flashforge/               # Flashforge TCP client (port 8899) + status/control widgets
│   ├── pihole/                   # Pi-hole v6 REST client + stats/control widgets
│   ├── network/                  # ping-based NetworkDeviceWidget
│   ├── docker/                   # docker CLI wrapper + DockerWidget (start/stop/restart)
│   └── browser/                  # Optional QtWebEngine internal browser app
├── scripts/
│   ├── install.sh                # One-time Pi installer (venv, service, udev rules)
│   ├── kiosk-start.sh            # Kiosk mode launcher
│   ├── sync-pi.sh                # Deploy code to Pi via SCP
│   ├── diagnose-pi.sh            # Diagnostic commands for Pi
│   ├── configure_ha.py           # Interactive HA configuration script
│   ├── install-github.sh         # First-time install directly from GitHub
│   ├── update-github.sh          # Safe fast-forward update from GitHub
│   └── verify_*.py               # Headless regression suite (16 scripts) - plugin boot,
│                                 #   error isolation, conditions, animations, templates,
│                                 #   docker, system monitor, expressions, workflows,
│                                 #   backup, custom widget, screensaver, web widget
├── systemd/
│   └── homepanel.service         # systemd unit file (template with /home/pi placeholders)
├── thoughts/                     # Development notes
├── .venv/                        # Python virtual environment
├── requirements.txt              # Python dependencies
├── README.md                     # User-facing documentation (German)
├── AI-CONTEXT.md                 # THIS FILE — technical reference for AI assistants
├── SETUP-STATUS.md               # Hardware bring-up notes (Pi 5 DSI/cage rendering fix)
├── LICENSE                       # MIT license
└── .gitignore
```

---

## 5. Architecture Deep Dive

### 5.1 Application Startup Flow

1. `main.py` parses args (`--windowed`, `--demo`), creates `QApplication`, creates `MainWindow`
2. `MainWindow.__init__()` creates: `Database` → `AppSettings` → `ThemeManager` → applies active theme
3. If `setup_complete == False`: shows `SetupWizard` (language, HA URL/token, or demo mode)
4. If `setup_complete == True`: calls `_start_runtime()`:
   - Creates `StateManager` → starts REST fetch + WebSocket connection
    - Creates `ServiceRegistry` → registers database, settings, state manager
    - Creates `PluginManager` → discovers, resolves and loads enabled plugins
    - Creates `WorkflowEngine` (`app/core/workflows.py`) → registered in `ServiceRegistry`,
      listens to `StateManager.entity_updated` for WHEN/THEN/WAIT automations
   - Creates `DashboardView` (canvas + nav bar + settings button + corner gesture zone)
   - Creates `EditorScreen`
   - Creates `SettingsScreen`
   - Loads first page into dashboard

### 5.2 Data Flow Architecture

```
Home Assistant Server
    │
    ├── REST API (initial load + service calls)
    │       └── HomeAssistantClient (app/core/homeassistant.py)
    │               └── Entity dataclass (entity_id, state, attributes, domain)
    │
    └── WebSocket (live state updates)
            └── HomeAssistantWebSocket (app/core/websocket.py)
                    └── state_changed Signal → StateManager._on_state_changed()

StateManager (app/core/state_manager.py)
    │
    ├── entities: dict[str, Entity]     ← central cache
    ├── entity_updated Signal           → connected to dashboard canvas
    ├── connection_status_changed Signal → connected to ConnectionBadge
    ├── call_service()                  → routes to REST client or demo simulation
    └── Demo Mode:                      → simulates entity updates every 5 seconds
            ├── 28 predefined demo entities
            └── _simulate_service_call() → simulates light, cover, climate, fan, etc.

Database (app/core/database.py)
    │
    ├── pages table: id, name, icon, order_index, bg_image_path, bg_fit
    ├── widgets table: id, page_id, type, x, y, w, h, z, config (JSON)
    ├── themes table: id, name, config (JSON), is_active, built_in
    ├── templates table: id, name, kind (widget|page), type, config (JSON), created_at
    ├── workflows table: id, name, trigger_entity, trigger_state, steps (JSON), enabled
    ├── settings table: key, value (JSON)
    ├── export_config() → JSON export incl. templates/workflows; secrets excluded by default
    └── import_config() → restore from JSON export

AppSettings (app/core/settings.py)
    └── Typed property accessors that read/write from Database settings table
        ├── language, ha_url, ha_token, demo_mode, setup_complete
        ├── edit_pin, orientation, design_resolution, navigation_style
        ├── theme_mode, standby_enabled, standby_dim_minutes, standby_off_minutes
        ├── standby_dim_opacity
        └── screensaver_mode, screensaver_background_path
```

### 5.3 Widget System

The widget system is the core extensibility mechanism. Every widget follows this pattern:

```python
class MyWidget(BaseWidget):
    type_name = "my_widget"           # Unique string identifier
    display_name = "My Widget"        # Human-readable name
    category = "Steuerung"            # Category for library grouping
    icon = "🎯"                       # Emoji icon for library
    default_size = (200, 140)         # Default width x height
    requires_entity = False           # Whether it needs an HA entity
    entity_domains = []               # Allowed HA domains (e.g., ["light"])

    PROPERTY_SCHEMA = [
        PropertyDef("my_prop", "My Property", "text", "default_value"),
        PropertyDef("my_color", "Farbe", "color", "#4C8DFF"),
        PropertyDef("my_number", "Zahl", "number", 50, min=0, max=100),
        PropertyDef("my_bool", "An/Aus", "bool", True),
        PropertyDef("my_select", "Auswahl", "select", "opt1", options=["opt1", "opt2"]),
        PropertyDef("my_entity", "Entity", "entity", "", entity_domains=["light"]),
    ]

    def build_ui(self) -> None:
        """Create child widgets/layouts."""

    def refresh_from_state(self) -> None:
        """Update visuals from current entity state."""
```

**PropertyDef types**: `text`, `number`, `color`, `bool`, `select`, `icon`, `entity`, `font_size`, `image`, `action` (renders a button that opens a builder dialog, e.g. the Custom Widget element editor)

**COMMON_SCHEMA** (18 properties applied to ALL widgets):
- Appearance: `bg_color`, `text_color`, `accent_color`, `radius`, `opacity`
- Gradient: `bg_gradient_enabled`, `gradient_color`, `gradient_direction`
- Background image: `bg_image_path`, `bg_image_opacity`
- Shadow: `shadow`
- Typography: `font_size`, `font_family`
- Layout: `icon_position`, `padding`
- Conditional visibility: `visible_entity`, `visible_state`, `visible_invert`

**Adding a new widget** (the plugin seam):
1. Create `app/widgets/my_widget.py` with a class subclassing `BaseWidget`
2. Set `type_name`, `display_name`, `category`, `icon`, `default_size`
3. Define `PROPERTY_SCHEMA` list
4. Implement `build_ui()` and `refresh_from_state()`
5. Add import + append to `WIDGET_CLASSES` in `app/widgets/registry.py`
6. **Nothing else needs to change** — the editor, library, and properties panel auto-discover it

### 5.4 Widget Registry

```python
# app/widgets/registry.py
WIDGET_CLASSES: list[type[BaseWidget]] = [
    ButtonWidget, LightWidget, SwitchWidget, SliderWidget, ThermostatWidget,
    SensorWidget, CoverWidget, WeatherWidget, ClockWidget, TextWidget,
    IconWidget, EntityListWidget,
    CalendarWidget, TodoListWidget, AlarmPanelWidget, VacuumWidget, FanWidget,
    LockWidget, HumidifierWidget, PersonWidget, SceneGridWidget,
    NumberInputWidget, SelectWidget,
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
```

**42 core registered widget types** across 7 categories (plugins add more at runtime -
see 5.6):
- **Steuerung** (Control, 16): Button, Light, Switch, Slider, Thermostat, Cover, MediaPlayer, Timer, Fan, Lock, Humidifier, AlarmPanel, Vacuum, SceneGrid, NumberInput, Select
- **Anzeige** (Display, 13): Sensor, Weather, Clock, Text, Icon, EntityList, Camera, SensorGraph, Calendar, TodoList, Person, Notification, Energy
- **Internet** (8): CryptoPrice, StockPrice, Currency, Quote, Joke, Holiday, InternetStatus, News
- **System** (2): SystemMonitor (built-in demo widget), Console
- **Allgemein** (1): Container
- **Apps** (1): `WebWidget` - optional QtWebEngine-backed panel, degrades to a
  text message if `PySide6.QtWebEngineWidgets` is not installed (never crashes)
- **Custom** (1): `CustomWidget` - see 5.13 Custom Widget Builder

### 5.5 Phase 1 Plugin Architecture

Plugins live in `plugins/<plugin-id>/` and contain `manifest.json` plus a
`plugin.py` with a `Plugin` subclass. The supported lifecycle is:

1. `PluginManager.load_all()` discovers and validates manifests.
2. `requires` is resolved as a list of plugin IDs; dependencies load before
    their dependants. Missing, disabled, failed, or cyclic requirements place
    only the affected plugin in the `error` state.
3. The manager injects namespaced `PluginSettings` and the shared
    `ServiceRegistry`, calls `register_widgets()`, then calls `on_load()`.
4. On disable, reload, or application shutdown it calls `on_unload()` and
    removes only widget types that the plugin registered.

All plugin failures are contained by the manager and exposed in the Plugins
settings tab. That tab offers activate, deactivate, reload, and a generated
settings dialog. A plugin can declare `settings_schema` using
`PluginSettingDef` entries with `text`, `number`, `bool`, or `select` fields;
values are stored under `plugin.<plugin-id>.*` in SQLite.

A plugin may also override `create_app_view(parent=None)` to return a
full-screen widget; `app/ui/app_launcher.py` lists every plugin that overrides
it and `MainWindow._open_plugin_app` opens the view inside the existing Qt
stack (never as an external process).

### 5.6 Plugin Catalog (Phase 3+, real integrations)

| Plugin (`plugins/<id>/`) | Real integration | Widgets | Notes |
|---|---|---|---|
| `system_monitor` | `/proc`, `/sys`, `os.statvfs` (no deps) | CPU, RAM, Storage, Network, SystemService (systemd) | Service start/stop/restart require confirmation + `sudo -n systemctl` |
| `flashforge` | Raw TCP client, port 8899, `~M601 S1` control handshake ([protocol ref](https://github.com/Parallel-7/flashforge-api-docs/wiki/TCP-Protocol)) | PrinterStatusWidget, PrintControlWidget | Background `QThread`; pause/resume/cancel confirmed for cancel |
| `pihole` | Pi-hole v6 REST API (`/api/...`, `sid` session header) | PiHoleStatsWidget, PiHoleControlWidget | Timed blocking disable (5/30/60 min or permanent) |
| `network` | `ping` subprocess, bounded timeout | NetworkDeviceWidget | Per-device host/IP configured via PROPERTY_SCHEMA |
| `docker` | `docker` CLI via `subprocess` (local socket) | DockerWidget | Container list + Start/Stop/Restart, confirmation for Stop/Restart |
| `browser` | Optional `QtWebEngineWidgets` | none (provides `create_app_view`) | Back/Forward/Reload/Home/Bookmarks/Fullscreen; safe no-WebEngine fallback |

All plugin API clients run their network/subprocess calls in a `QThread` and
emit a Qt signal back to the widget - never a blocking call on the UI thread.

### 5.7 Animation Engine (`app/core/animations.py`)

`AnimationEngine` (singleton `animation_engine`) plays short, one-shot Qt
property animations - `fade`, `slide`, `pulse`, `bounce`, `shake`, `glow` (no
`rotate`/`breathing`/scale-as-separate-type yet) - triggered by `BaseWidget` on
widget entry and on bound-entity state changes, never as an infinite loop.
Every widget gets three new COMMON_SCHEMA properties: `entrance_animation`,
`state_animation`, `animation_speed`.

### 5.8 Conditional Styling (`app/core/conditions.py`)

`matches_condition(value, operator, expected)` implements the safe operator
set (`equals`, `not_equals`, `greater_than`, `less_than`, `contains`, `online`,
`offline`, `true`, `false`) shared by:
- **Visibility** (`visible_entity`/`visible_operator`/`visible_state`/`visible_invert`,
  extends the original equals-only Conditional Visibility with all operators)
- **Styling** (`style_enabled`/`style_entity`/`style_operator`/`style_value`/
  `style_bg_color`/`style_text_color` COMMON_SCHEMA properties) - overrides
  `bg_color`/`text_color` via `BaseWidget.apply_conditional_style()` without
  mutating the stored base config.

### 5.9 Safe Expression System (`app/core/expressions.py`)

Whitelist-only template evaluator for the Custom Widget Builder -
`render_template("{{ state | round(1) }}", {"state": 23.44})`. Only `Name`,
`Constant`, `BinOp` (`+ - * /`), `UnaryOp` AST nodes are evaluated; everything
else (calls, attribute access, comprehensions, imports) raises
`ExpressionError` instead of running - there is no `eval`/`exec` of
user-supplied Python. Filters: `round`, `upper`, `lower`, `int`, `float`, `abs`.

### 5.10 Custom Widget Builder (`app/widgets/custom_widget.py` + `app/ui/custom_widget_builder.py`)

`CustomWidget` (`type_name="custom_widget"`) renders `config["elements"]` -
a list of `{type, x, y, w, h, color, template, entity_id}` dicts - as
absolutely-positioned child widgets (`text`, `icon`, `sensor_value`,
`progress_bar`, `button`, all bound via the safe expression templates above).
Its only `PROPERTY_SCHEMA` entry is an `"action"`-type property that opens
`open_custom_widget_builder()`, a dialog to add/edit/remove elements; saving
calls the existing `PropertiesPanel._update("elements", ...)` path, so
persistence reuses the standard widget-config flow (no parallel storage).

### 5.11 Workflow Engine (`app/core/workflows.py`, list-based Phase 5 foundation)

Workflows are stored in the `workflows` SQLite table (`Database.save_workflow`
/ `list_workflows` / `set_workflow_enabled`). `WorkflowEngine` (registered in
`ServiceRegistry` as `"workflow_engine"`) listens to `StateManager.entity_updated`
and, when `trigger_entity`/`trigger_state` matches, runs `steps` sequentially:
`{"kind": "action", "domain", "service", "entity_id", "data"}` calls
`state_manager.call_service(...)`; `{"kind": "wait", "seconds"}` delays via
`QTimer.singleShot`. A broken step is caught and logged, never raised. No
visual editor yet - a node-based UI can be layered on this storage/engine
without changes.

### 5.6 Theme System

Themes are dictionaries of design tokens that get converted to Qt stylesheets:

```python
BUILT_IN_THEMES = [
    {"name": "Dark Glass", "mode": "dark", "background": "#101218", "surface": "#1B1E29", ...},
    {"name": "Minimal", "mode": "light", "background": "#F2F3F5", "surface": "#FFFFFF", ...},
    {"name": "Industrial", "mode": "dark", "background": "#1C1C1C", ...},
    {"name": "Modern", "mode": "dark", "background": "#0E0F1A", ...},
]
```

**Theme tokens**: `name`, `mode` (light/dark), `background`, `surface`, `primary`, `secondary`, `accent`, `text`, `text_secondary`, `card_radius`, `card_opacity`, `shadow`, `border`, `font_family`, `font_size_base`, `spacing`

**Auto mode**: Switches between light/dark themes based on time of day (7:00–19:00 = light, rest = dark). Checked every 5 minutes by a QTimer.

**build_stylesheet(theme)** generates a complete Qt stylesheet from the token dict, applying to QMainWindow, QWidget, QLabel, QPushButton, QLineEdit, QComboBox, QSlider, QToolTip, and nav-specific selectors.

### 5.7 Editor System

The editor is a full visual layout tool:

- **Activation**: 3-second long-press on top-left corner (configurable PIN protection)
- **Features**: Drag & drop, resize (blue handle), z-index/layer ordering, duplicate, delete, undo/redo, grid snap
- **Keyboard shortcuts**: Ctrl+C (copy), Ctrl+V (paste), Shift+Click (multi-select)
- **Property panel**: Auto-generated from widget's `PROPERTY_SCHEMA` + `COMMON_SCHEMA`
- **Entity picker**: Browse HA entities by room/area, no manual entity_id typing needed
- **Save/Cancel**: Save commits changes to SQLite, Cancel reverts to pre-edit snapshot
- **Page management**: Add/delete pages (with confirmation, last page protected)

### 5.12 Standby State Machine

```
NORMAL → (inactivity timeout) → DIMMED → (more inactivity) → OFF
   ↑                                                        │
   └────────────── any user interaction ─────────────────────┘
```

- **DIMMED**: Semi-transparent overlay (configurable opacity, default 60%)
- **OFF**: Full black overlay + backlight off via sysfs (`/sys/class/backlight/*/brightness`)
- **Wake**: Any touch/click/mouse move/keyboard event
- **Configurable**: dim_minutes, off_minutes, dim_opacity, enable/disable
- **Screensaver mode** (`screensaver_mode` setting, Settings → Standby & Display):
  `"digital_clock"` (default, unchanged) or `"system_info"` (live CPU/RAM % +
  temperature read directly, refreshed every 5s while shown)
- **Background image** (`screensaver_background_path` setting): optional static
  image shown behind the clock/info text; cleared = plain dim/black as before

### 5.13 Navigation

Two modes:
- **Bottom bar** (default): Horizontal button bar at screen bottom
- **Sidebar**: Vertical navigation panel

Pages can be reordered in the editor. Each page has: `name`, `icon`, `order_index`, `bg_image_path`, `bg_fit`.

### 5.14 Conditional Visibility

Every widget can be conditionally shown/hidden based on an HA entity's state,
now using the same operator set as Conditional Styling (5.8):
- `visible_entity`: entity_id to check
- `visible_operator`: `equals` (default) | `not_equals` | `greater_than` | ...
- `visible_state`: expected value
- `visible_invert`: if true, show when the condition does NOT match

### 5.15 Extended Backup (`Database.export_config`/`import_config`)

Export now includes `templates` and `workflows` alongside `pages`/`widgets`/
`themes`/`settings`. Any settings key matching `token`, `sid`, `password`,
`secret`, `api_key`/`apikey` (case-insensitive) is excluded unless
`include_secrets=True` is explicitly requested - this covers `ha_token` as
well as plugin secrets like `plugin.pihole.sid` automatically, with no
per-plugin allowlist to maintain.

---

## 6. Database Schema

```sql
CREATE TABLE pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    icon TEXT DEFAULT '',
    order_index INTEGER NOT NULL DEFAULT 0,
    bg_image_path TEXT NOT NULL DEFAULT '',
    bg_fit TEXT NOT NULL DEFAULT 'cover'
);

CREATE TABLE widgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    x REAL NOT NULL DEFAULT 0,
    y REAL NOT NULL DEFAULT 0,
    w REAL NOT NULL DEFAULT 200,
    h REAL NOT NULL DEFAULT 120,
    z INTEGER NOT NULL DEFAULT 0,
    config TEXT NOT NULL DEFAULT '{}'  -- JSON blob
);

CREATE TABLE themes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    config TEXT NOT NULL DEFAULT '{}',  -- JSON blob
    is_active INTEGER NOT NULL DEFAULT 0,
    built_in INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT  -- JSON-encoded value
);

CREATE TABLE templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL DEFAULT 'widget',  -- 'widget' | 'page'
    type TEXT NOT NULL DEFAULT '',
    config TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL DEFAULT 0
);

CREATE TABLE workflows (  -- Phase 5, see 5.11 Workflow Engine
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    trigger_entity TEXT NOT NULL DEFAULT '',
    trigger_state TEXT NOT NULL DEFAULT '',
    steps TEXT NOT NULL DEFAULT '[]',  -- JSON list of {kind: action|wait, ...}
    enabled INTEGER NOT NULL DEFAULT 1
);
```

**Key design choice**: Widget and theme configs are stored as JSON blobs, not normalized tables. This means new widget properties or theme tokens never require database migrations.

**Database location**: `data/homepanel.db` (relative to project root)

---

## 7. Settings Keys

| Key | Type | Default | Description |
|---|---|---|---|
| `language` | string | `"de"` | UI language |
| `ha_url` | string | `""` | Home Assistant base URL |
| `ha_token` | string | `""` | Long-lived access token (NEVER logged) |
| `demo_mode` | bool | `false` | Run without Home Assistant |
| `setup_complete` | bool | `false` | Whether wizard has been completed |
| `edit_pin` | string/null | `null` | PIN for editor access |
| `orientation` | string | `"landscape"` | `"landscape"` or `"portrait"` |
| `design_resolution` | [int, int] | `[1024, 600]` | Canvas resolution |
| `navigation_style` | string | `"bottom"` | `"bottom"` or `"sidebar"` |
| `theme_mode` | string | `"dark"` | `"light"`, `"dark"`, or `"auto"` |
| `standby_enabled` | bool | `true` | Enable standby feature |
| `standby_dim_minutes` | int | `2` | Minutes before dimming |
| `standby_off_minutes` | int | `5` | Minutes before display off |
| `standby_dim_opacity` | int | `60` | Dim overlay opacity (0-100) |
| `screensaver_timeout` | int | `10` | Legacy screensaver timeout (min) |
| `screensaver_mode` | string | `"digital_clock"` | `"digital_clock"` or `"system_info"` |
| `screensaver_background_path` | string | `""` | Optional static background image path |
| `plugin.<id>.<key>` | any | - | Namespaced per-plugin settings (see `PluginSettings`) |

---

## 8. Deployment

### 8.1 Installation (on the Pi)

```bash
./scripts/install.sh
```

This script:
1. Installs system packages (`python3-venv`, `python3-pip`, `libgl1`, `libegl1`)
2. Ensures user is in `video` group (for backlight/DRM access)
3. Creates `.venv` and installs Python dependencies
4. Copies and patches `systemd/homepanel.service` (replaces `/home/pi/homepanel` with actual path, `User=pi` with current user)
5. Installs udev rule for backlight write access
6. Enables the systemd service

### 8.2 Service File

```ini
[Service]
Type=simple
User=pi  # patched by install.sh
PAMName=login
Environment=QT_QPA_PLATFORM=wayland
Environment=PYTHONUNBUFFERED=1
ExecStartPost=/bin/sh -c 'i=0; until wlr-randr --output DSI-2 --transform 90 || [ $i -ge 20 ]; do i=$((i+1)); sleep 0.5; done'
WorkingDirectory=/home/pi/homepanel
ExecStart=/usr/bin/cage -d -- /home/pi/homepanel/.venv/bin/python -m app.main
Restart=always
RestartSec=3
```

Key points:
- `cage -d` runs a single-app Wayland compositor (detached mode)
- `QT_QPA_PLATFORM=wayland` tells Qt to use Wayland backend
- `wlr-randr --transform 90` applies landscape rotation after startup (retries 20 times with 0.5s delay)
- `WAYLAND_DISPLAY` must NOT be pre-set (cage sets it for child processes)
- `Restart=always` with 3s delay ensures crash recovery

### 8.3 Deploying Code Changes

```bash
./scripts/sync-pi.sh  # SCP code to Pi
```

Or manually:
```bash
scp systemd/homepanel.service supervisor@192.168.178.138:/tmp/
ssh supervisor@192.168.178.138 'echo 0908 | sudo -S sh -c \
  "sed \"s#/home/pi/homepanel#/home/supervisor/homepanel#g; s#User=pi#User=supervisor#g\" /tmp/homepanel.service > /etc/systemd/system/homepanel.service && systemctl daemon-reload && systemctl restart homepanel.service"'
```

### 8.4 Verifying Deployment

```bash
ssh supervisor@192.168.178.138 'echo 0908 | sudo -S systemctl is-active homepanel.service'
ssh supervisor@192.168.178.138 'echo 0908 | sudo -S journalctl -u homepanel.service --since "5 min ago" --no-pager'
ssh supervisor@192.168.178.138 'ps aux | grep -E "cage|app.main" | grep -v grep'
```

**Framebuffer dump trick** (for remote screen verification):
```bash
ssh supervisor@192.168.178.138 'dd if=/dev/fb0 of=/tmp/fb.raw bs=4096 count=900'
scp supervisor@192.168.178.138:/tmp/fb.raw /tmp/fb.raw
magick -size 720x1280 -depth 8 rgba:/tmp/fb.raw /tmp/fb.png
tesseract /tmp/fb.png - --psm 11  # Orientation 90° = rotation active
```

---

## 9. Running Locally (Development)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Windowed mode (for desktop development)
python -m app.main --windowed

# Windowed + demo mode (no HA needed)
python -m app.main --windowed --demo

# Fullscreen (default, for Pi/kiosk)
python -m app.main
```

---

## 10. Demo Mode

When `demo_mode=True` (via `--demo` flag or wizard selection), the app:
- Loads 28 simulated entities (lights, switches, sensors, climate, cover, media player, cameras, etc.)
- Simulates service calls locally (toggle lights, set thermostat, open/close covers, etc.)
- Ticks sensor values randomly every 5 seconds (temperature ±0.3, power ±45W, etc.)
- Emits `entity_updated` signals to keep widgets reactive

No Home Assistant connection is needed. Useful for testing the UI and editor.

---

## 11. Key Patterns to Follow

### When Adding a Widget
1. Subclass `BaseWidget` in a new file under `app/widgets/`
2. Set class attributes: `type_name`, `display_name`, `category`, `icon`, `default_size`
3. Define `PROPERTY_SCHEMA` list of `PropertyDef` objects
4. Implement `build_ui()` — create Qt child widgets/layouts
5. Implement `refresh_from_state()` — read entity state via `self.entity()` and update UI
6. Register in `app/widgets/registry.py` — import + append to `WIDGET_CLASSES`
7. Use `self.call_service(domain, service, **data)` to send commands to HA
8. Use `self.get_prop(key)` to read config values (respects schema defaults)

### When Modifying UI
- `app/ui/main_window.py`: App shell, routing between views, standby state machine
- `app/ui/dashboard.py`: Canvas where widgets are rendered
- `app/ui/editor.py`: Editor toolbar and mode management
- `app/ui/properties.py`: Dynamic property panel (reads widget schemas)
- `app/ui/themes.py`: Theme presets and stylesheet generation

### When Modifying Backend
- `app/core/homeassistant.py`: REST API calls — `get_states()`, `call_service()`, `test_connection()`
- `app/core/websocket.py`: Live state updates via WebSocket
- `app/core/state_manager.py`: Central entity cache — `get_entity()`, `call_service()`, demo simulation
- `app/core/database.py`: All SQLite operations — pages, widgets, themes, settings CRUD
- `app/core/settings.py`: Typed property accessors wrapping Database settings

---

## 12. Known Issues / Technical Debt

1. **No tests**: The project has zero unit or integration tests
2. **Frame rendering**: Widgets use Qt's `QVBoxLayout` rather than custom paint, which may have performance implications with many widgets
3. **Widget config migration**: Since configs are JSON blobs, changing a widget's PROPERTY_SCHEMA default values won't affect existing widgets (they keep their old config until manually changed)
4. **cage rendering not verified**: The SETUP-STATUS.md indicates that under cage, it was not yet confirmed whether the app renders correctly and rotation works
5. **PAMName=login**: The service uses PAM login session, which may cause issues on some systems
6. **Single-user design**: No multi-user/multi-profile support

---

## 13. File Editing Rules

- **ALWAYS** use the `edit` tool for modifications, not `write` (preserves git history)
- **Read before edit**: You must read a file before editing it
- **Match existing style**: Follow the existing code patterns (German comments, type hints, docstrings)
- **No type suppression**: Never use `as any`, `@ts-ignore`, or equivalent
- **Preserve imports**: Don't remove unused imports unless they're clearly dead code
- **Widget schema changes**: Adding properties to COMMON_SCHEMA affects ALL widgets globally — be careful
- **Database changes**: Avoid schema migrations unless absolutely necessary — prefer JSON config flexibility
