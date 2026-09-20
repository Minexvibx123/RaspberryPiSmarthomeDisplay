# Core-Layer (`app/core/`)

Das Backend. Enthält die gesamte Persistenz- und Integrationslogik, ohne
Qt-Spezifika außerhalb der Threading-Helfer.

## Übersicht

| Modul | Verantwortung |
|---|---|
| `homeassistant.py` | Synchroner REST-Client für Home Assistant |
| `websocket.py` | Hintergrund-WebSocket-Client mit Auto-Reconnect |
| `database.py` | SQLite-Zugriff (Seiten, Widgets, Themes, Vorlagen, Workflows, Settings, Backup/Export) |
| `state_manager.py` | Zentrale Entity-Zustände, Verbindungsstatus, Demo-Modus |
| `settings.py` | Typisierter Wrapper um die Settings-Tabelle |
| `service_registry.py` | Service-Nachschlagestelle für Plugins |
| `http_fetch.py` | Nebenläufiger HTTP-Fetch-Helfer für Internet-Widgets |
| `animations.py` | Einmalige Widget-Animationen (Fade/Slide/Pulse/Bounce/Shake/Glow) |
| `conditions.py` | Sichere Bedingungsauswertung (Sichtbarkeit + Styling) |
| `expressions.py` | Whitelist-Template-System (`{{ state \| round(1) }}`) |
| `workflows.py` | Listenbasierte WENN/DANN/WARTEN-Workflow-Engine |

## `homeassistant.py` – REST-Client

Minimaler, synchroner Client für Einzelabrufe:

- `Entity(entity_id, state, attributes)` – Dataclass mit `domain`,
  `friendly_name` und `area` als Eigenschaften.
- `test_connection()` → `(ok: bool, message: str)`.
- `get_states()`, `get_state(entity_id)`, `get_config()`, `get_logbook()`.
- `call_service(domain, service, entity_id=None, **data)` – wirft
  `HomeAssistantAPIError` bei HTTP ≥ 400.
- Authentifizierung per `Authorization: Bearer <token>`.

Live-Updates laufen nicht hier, sondern über `websocket.py`.

## `websocket.py` – WebSocket-Client

- Läuft in eigenem `QThread`, UI wird nie blockiert.
- Auto-Reconnect mit Backoff (2 s → 30 s), Ping alle 20 s.
- Signale: `connected`, `disconnected(reason)`, `state_changed(entity_id, dict)`,
  `connection_status(bool)`.
- Authentifizierung über `auth_required`/`access_token`-Handshake und abonniert
  das Event `state_changed`.

## `database.py` – SQLite

Tabellen: `pages`, `widgets`, `themes`, `settings`, `templates`, `workflows`.

Wichtige Methoden:

- Seiten: `list_pages()`, `create_page()`, `update_page()`, `delete_page()`,
  `reorder_pages()`.
- Widgets: `list_widgets(page_id)`, `create_widget()`, `update_widget()`,
  `delete_widget()`, `duplicate_widget()`.
- Themes: `list_themes()`, `get_active_theme()`, `save_theme()`,
  `set_active_theme()`, `delete_theme()` (Built-Ins sind geschützt).
- Vorlagen: `save_template()`, `list_templates(kind)`, `get_template()`,
  `delete_template()`.
- Workflows: `save_workflow()`, `list_workflows()`, `get_workflow()`,
  `delete_workflow()`, `set_workflow_enabled()`.
- Settings: `get_setting(key, default)`, `set_setting(key, value)` (JSON-kodiert).
- Backup/Export: `backup_to_file(path)`, `restore_from_file(path)`,
  `export_config(include_secrets=False)`, `import_config(data, replace=True)`.

**Geheimnis-Schutz:** `export_config()` schließt Settings-Schlüssel aus, die
`token`, `sid`, `password`, `secret` oder `api_key` enthalten –
es sei denn, `include_secrets=True` ist explizit gesetzt.

## `state_manager.py` – Zentrale Entity-Zentrale

- `entities: dict[str, Entity]` – lokaler Cache aller Zustände.
- Signale: `entity_updated(entity_id, dict)`, `connection_status_changed(bool)`,
  `entities_loaded()`.
- `get_entity(entity_id)`, `call_service(domain, service, entity_id, **data)`.
- **Demo-Modus:** 28 vordefinierte Entities; Service-Aufrufe werden lokal
  simuliert und Sensorwerte alle 5 s zufällig aktualisiert. Kein Home Assistant
  nötig (`--demo`).

## `settings.py` – Typisierte Settings

Property-Wrapper um die Settings-Tabelle: `language`, `ha_url`, `ha_token`
(nie geloggt), `demo_mode`, `setup_complete`, `edit_pin`, `orientation`,
`design_resolution`, `effective_design_resolution`, `navigation_style`,
`theme_mode` (light/dark/auto), Standby (`standby_enabled`,
`standby_dim_minutes`, `standby_off_minutes`, `standby_dim_opacity`) und
Screensaver (`screensaver_mode`, `screensaver_background_path`).

## `service_registry.py` – Service-Registry

Plugins lösen ihre Abhängigkeiten über Namen auf statt über harte Imports:

- `register(name, service, replace=False)` – Duplikate werfen `KeyError`.
- `resolve(name)`, `get(name)`, `names()`, `registered(name)`.

Beim Start registriert `MainWindow._start_runtime()` u. a. `database`,
`settings`, `state_manager`, `workflow_engine`.

## `http_fetch.py` – Hintergrund-HTTP

`fetch(url, on_success, on_error=None, params=None, headers=None, as_json=True, parent=None)`

- Jeder Request läuft in einem eigenen, kurzlebigen `QThread`.
- Callbacks werden über Qt-Signals auf dem Main-Thread aufgerufen und gegen
  bereits gelöschte Widgets geschützt (`RuntimeError` wird geschluckt).
- Der Thread ist bewusst **kein** Qt-Kind des aufrufenden Widgets (sonst
  Prozessabort bei Widget-Löschung während des Requests); er verwaltet sich
  selbst (`_ACTIVE_THREADS` hält die Referenz).
- Timeout 6 s, Ergebnis als JSON oder Text.

## `animations.py` – Animation Engine

Singleton `animation_engine` mit `play(widget, name, speed)`:

- Namen: `none`, `fade`, `slide`, `pulse`, `bounce`, `shake`, `glow`.
- Einmalig, kurze Dauer (≤ 1500 ms), maximal eine Animation pro Widget.
- Wird von `BaseWidget` bei Eintritt und bei gebundenen
  Entity-Zustandsänderungen ausgelöst; konfigurierbar über die
  `COMMON_SCHEMA`-Felder `entrance_animation`, `state_animation`,
  `animation_speed`.

## `conditions.py` – Bedingungsauswertung

`matches_condition(value, operator, expected)` – sicher, kein User-Code:

`equals`, `not_equals`, `greater_than`, `less_than`, `contains`, `online`,
`offline`, `true`, `false`.

Gemeinsam genutzt von **bedingter Sichtbarkeit** (`visible_*`-Properties) und
**bedingtem Styling** (`style_*`-Properties, overridet `bg_color`/`text_color`
ohne die gespeicherte Basis-Konfiguration zu verändern).

## `expressions.py` – Expression-Engine

Sicheres Whitelist-Template-System, ausschließlich für den Custom Widget Builder:

- Erlaubt nur `Name`, `Constant`, `BinOp` (`+ - * /`) und `UnaryOp`.
- Filter: `round`, `upper`, `lower`, `int`, `float`, `abs`.
- Beispiel: `render_template("{{ state | round(1) }}", {"state": 23.44})` → `"23.4"`.
- Alles andere (Calls, Attributzugriff, Comprehensions, Imports) wirft
  `ExpressionError` — **kein** `eval`/`exec`.

## `workflows.py` – Workflow-Engine

Listenbasierte Automationen (Phase-5-Fundament):

- Format: `WHEN <entity> == <state> THEN <steps…>`.
- Schritt `{"kind": "action", "domain", "service", "entity_id", "data"}`
  → `state_manager.call_service(...)`.
- Schritt `{"kind": "wait", "seconds"}` → Verzögerung per `QTimer.singleShot`.
- Hängt an `state_manager.entity_updated`; ein fehlerhafter Schritt wird
  geloggt und nie geworfen. Gespeichert in der `workflows`-Tabelle; eine
  node-basierte UI kann später ohne Formatänderung aufgesetzt werden.