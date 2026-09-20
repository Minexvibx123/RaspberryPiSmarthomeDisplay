# Architektur

HomePanel ist eine native PySide6/Qt6-Anwendung für den Raspberry Pi 5 mit
7"-Touchdisplay, die als hochgradig visuell konfigurierbares Dashboard für
Home Assistant dient. Das Kernprinzip: **keine manuelle Code- oder
YAML/JSON-Konfiguration** – alles wird direkt auf dem Touchscreen bearbeitet.

## Schichten

```
┌──────────────────────────────────────────────────────────────────┐
│  app/ui/        Oberfläche: MainWindow, Dashboard, Editor,       │
│                 Settings, Themes, Navigation, Wizard, Launcher   │
├──────────────────────────────────────────────────────────────────┤
│  app/widgets/   Eingebaute Widgets (BaseWidget + Registry)      │
│  plugins/*/     Plugin-Widgets (z. B. Flashforge-Kamera)        │
├──────────────────────────────────────────────────────────────────┤
│  app/core/      Backend: Datenbank, HA REST/WebSocket,           │
│                 State-Manager, Engines (Animation, Conditions,   │
│                 Expressions, Workflows), HTTP-Fetch              │
├──────────────────────────────────────────────────────────────────┤
│  data/          SQLite (homepanel.db) – Seiten, Widgets, Themes, │
│                 Vorlagen, Workflows, Settings                    │
└──────────────────────────────────────────────────────────────────┘
```

## Basis-Entscheidungen

- **Eine Datenbank (SQLite) als einzige Wahrheit.** Seiten, Widgets, Themes,
  Vorlagen, Workflows und Settings liegen in `data/homepanel.db`
  (`app/core/database.py`). Widget- und Theme-Konfigurationen sind JSON-Blobs,
  dadurch brauchen neue Eigenschaften **nie** eine DB-Migration.
- **State-Manager als zentrale Entity-Zentrale.** Widgets sprechen nie direkt
  mit Home Assistant, sondern immer über `StateManager` (`app/core/state_manager.py`).
  Dadurch bleibt das Panel auch bei Ausfällen reaktiv (letzter bekannter
  Zustand ist lokal verfügbar).
- **Schema-getriebene Oberfläche.** Der Editor, die Element-Bibliothek und das
  Eigenschaftenpanel kennen **keinen einzigen Widget-Typ**. Sie rendern
  ausschließlich die `PROPERTY_SCHEMA`-Liste, die jedes Widget deklariert.
  Neue Widgets brauchen daher nur: Klasse schreiben + in
  `app/widgets/registry.py` eintragen (oder per Plugin registrieren).
- **Threading über Qt-Signals.** Langsame Arbeit (HTTP, WebSocket, TCP,
  Subprocess, Ping) läuft in `QThread`s und meldet Ergebnisse über Qt-Signals
  zurück – der UI-Thread wird nie blockiert.

## Startablauf

1. `app/main.py` parst die Argumente (`--windowed`, `--demo`), erzeugt die
   `QApplication` und `MainWindow`.
2. `MainWindow.__init__()` erzeugt `Database`, `AppSettings` und den
   `ThemeManager` und wendet das aktive Theme an.
3. Ohne abgeschlossene Einrichtung (`setup_complete == False`) erscheint der
   `SetupWizard` (Sprache, HA-URL + Token oder Demo-Modus).
4. Ansonsten startet `_start_runtime()`:
   - `StateManager` – lädt die Entity-Zustände per REST und verbindet sich per
     WebSocket für Live-Updates.
   - `ServiceRegistry` – zentrale Service-Nachschlagestelle für Plugins
     (`database`, `settings`, `state_manager`, `workflow_engine`, …).
   - `PluginManager` – entdeckt und lädt alle aktivierten Plugins
     (`plugins/*/manifest.json`), mit vollständiger Fehlerisolation.
   - `WorkflowEngine` – lauscht auf `state_manager.entity_updated` und führt
     WENN-Entity-Zustand-DANN-Aktion/Warten-Automationen aus.
   - `DashboardView` (Canvas + Navigation + Verbindungs-Badge + Editor-Geste),
     `EditorScreen` und `SettingsScreen`.
5. Danach rendert das Dashboard die erste Seite.

## Datenfluss (Home Assistant)

```
Home Assistant Server
    ├── REST (Initial-Load + Service-Calls)
    │       └── HomeAssistantClient (app/core/homeassistant.py)
    │               └── Entity-Datensätze
    └── WebSocket (Live-Zustandsänderungen)
            └── HomeAssistantWebSocket (app/core/websocket.py)
                    └── Signal state_changed
StateManager
    ├── entities: dict[str, Entity]        ← zentraler Cache
    ├── Signal entity_updated              → an Dashboard/Widgets
    ├── Signal connection_status_changed   → Verbindungs-Badge
    ├── call_service()                     → REST oder Demo-Simulation
    └── Demo-Modus: 28 simulierte Entities, Tick alle 5 s
Database (app/core/database.py)             ← Persistenz aller Layouts
AppSettings (app/core/settings.py)          ← typisierter Settings-Zugriff
```

## Threading-Modell

| Modul | Thread | Rückkanal |
|---|---|---|
| `core/http_fetch.py` | eigener kurzlebiger `QThread` pro Request | Callback auf Qt-Main-Thread (geguarded) |
| `core/websocket.py` | ein `QThread` mit Auto-Reconnect | Qt-Signale |
| Plugins (`flashforge`, `pihole`, `docker`, `network`, `system_monitor`) | je Widget ein `_Job`-`QThread` | Qt-Signale |
| Flashforge-Kamera | `_MjpegReader` (`QThread`) parst MJPEG-Stream | Signal `frame_ready` (Bytes → QPixmap) |

Grundregel: **Blockierende I/O nie im UI-Thread.** Fehlgeschlagene
Hintergrundaufgaben werden gemeldet, nie geworfen.

## Editor-Modus

- Aktivierung: 3-Sekunden-Langdruck oben links (optional PIN-geschützt,
  Einstellung `edit_pin`).
- `DashboardCanvas` wird mit `edit_mode=True` wiederverwendet – Normal- und
  Editor-Modus sehen pixelidentisch aus.
- Undo/Redo arbeitet auf Ganz-Seiten-Snapshots der Widget-Zeilen.
- `Speichern` schreibt nach SQLite, `Abbrechen` verwirft alle Änderungen seit
  dem Öffnen des Editors.