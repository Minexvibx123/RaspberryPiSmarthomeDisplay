# AI-CONTEXT – HomePanel Technical Reference

> **Purpose**: This file provides a comprehensive technical summary of the HomePanel project for AI assistants that need to understand, modify, or extend this codebase. Read this file FIRST before touching any code.

---

## 1. What This Project Is

**HomePanel** is a native PySide6 (Qt6) touch-panel application that serves as a highly customizable Home Assistant dashboard. It runs on a Raspberry Pi 5 with the official 7" touchscreen display.

**Core Value Proposition**: Users can visually design their home dashboard by dragging, dropping, resizing, and configuring widgets directly on the touchscreen — no YAML, no JSON, no code editing required.

**Current State**: The project is functional and running on physical hardware. It has a complete widget system, visual editor, theme system, and deployment pipeline. There are no unit tests.

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
├── scripts/
│   ├── install.sh                # One-time Pi installer (venv, service, udev rules)
│   ├── kiosk-start.sh            # Kiosk mode launcher
│   ├── sync-pi.sh                # Deploy code to Pi via SCP
│   ├── diagnose-pi.sh            # Diagnostic commands for Pi
│   └── configure_ha.py           # Interactive HA configuration script
├── systemd/
│   └── homepanel.service         # systemd unit file (template with /home/pi placeholders)
├── thoughts/                     # Development notes
├── .venv/                        # Python virtual environment
├── requirements.txt              # Python dependencies
├── README.md                     # User-facing documentation (German)
├── AI-CONTEXT.md                 # THIS FILE — technical reference for AI assistants
├── SETUP-STATUS.md               # Deployment status / debugging notes
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
    ├── settings table: key, value (JSON)
    ├── export_config() → full JSON export (optionally including secrets)
    └── import_config() → restore from JSON export

AppSettings (app/core/settings.py)
    └── Typed property accessors that read/write from Database settings table
        ├── language, ha_url, ha_token, demo_mode, setup_complete
        ├── edit_pin, orientation, design_resolution, navigation_style
        ├── theme_mode, standby_enabled, standby_dim_minutes, standby_off_minutes
        └── standby_dim_opacity
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

**PropertyDef types**: `text`, `number`, `color`, `bool`, `select`, `icon`, `entity`, `font_size`, `image`

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
]

WIDGET_REGISTRY: dict[str, type[BaseWidget]] = {cls.type_name: cls for cls in WIDGET_CLASSES}
```

**38 registered widget types** across 4 categories:
- **Steuerung** (Control): Button, Light, Switch, Slider, Thermostat, Cover, MediaPlayer, Timer, Fan, Lock, Humidifier, AlarmPanel, Vacuum, SceneGrid, NumberInput, Select
- **Anzeige** (Display): Sensor, Weather, Clock, Text, Icon, EntityList, Camera, SensorGraph, Calendar, TodoList, Person, Container, Notification, Energy
- **Internet**: CryptoPrice, StockPrice, Currency, Quote, Joke, Holiday, InternetStatus, News
- **System**: SystemMonitor, Console

### 5.5 Theme System

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

### 5.6 Editor System

The editor is a full visual layout tool:

- **Activation**: 3-second long-press on top-left corner (configurable PIN protection)
- **Features**: Drag & drop, resize (blue handle), z-index/layer ordering, duplicate, delete, undo/redo, grid snap
- **Keyboard shortcuts**: Ctrl+C (copy), Ctrl+V (paste), Shift+Click (multi-select)
- **Property panel**: Auto-generated from widget's `PROPERTY_SCHEMA` + `COMMON_SCHEMA`
- **Entity picker**: Browse HA entities by room/area, no manual entity_id typing needed
- **Save/Cancel**: Save commits changes to SQLite, Cancel reverts to pre-edit snapshot
- **Page management**: Add/delete pages (with confirmation, last page protected)

### 5.7 Standby State Machine

```
NORMAL → (inactivity timeout) → DIMMED → (more inactivity) → OFF
   ↑                                                        │
   └────────────── any user interaction ─────────────────────┘
```

- **DIMMED**: Semi-transparent clock overlay (configurable opacity, default 60%)
- **OFF**: Full black overlay + backlight off via sysfs (`/sys/class/backlight/*/brightness`)
- **Wake**: Any touch/click/mouse move/keyboard event
- **Configurable**: dim_minutes, off_minutes, dim_opacity, enable/disable

### 5.8 Navigation

Two modes:
- **Bottom bar** (default): Horizontal button bar at screen bottom
- **Sidebar**: Vertical navigation panel

Pages can be reordered in the editor. Each page has: `name`, `icon`, `order_index`, `bg_image_path`, `bg_fit`.

### 5.9 Conditional Visibility

Every widget can be conditionally shown/hidden based on an HA entity's state:
- `visible_entity`: entity_id to check
- `visible_state`: expected state string (e.g., "on", "home", "motion")
- `visible_invert`: if true, show when state does NOT match

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
