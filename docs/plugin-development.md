# Plugin-Entwicklung

HomePanel lädt Plugins aus `plugins/<plugin-id>/`. Ein Plugin ist ein
Verzeichnis mit mindestens `manifest.json` und einer `plugin.py`, die eine
`Plugin`-Klasse definiert. Der Kern (`app/plugins/`) kümmert sich um
Discovery, Lifecycle und **Fehlerisolation**: Ein kaputtes Plugin kann die App
niemals zum Absturz bringen – Fehler werden erfasst und im Plugins-Tab der
Einstellungen angezeigt.

## On-Disk-Vertrag

```text
plugins/<id>/
├── manifest.json      # Metadaten (Pflichtfelder: id, name, version)
├── plugin.py          # muss eine `Plugin`-Klasse definieren
└── ...                # optionale Module (api.py, widgets.py, view.py, …)
```

### manifest.json

```json
{
  "id": "example_plugin",
  "name": "Beispiel Plugin",
  "version": "1.0.0",
  "description": "Kurzbeschreibung",
  "author": "HomePanel",
  "enabled": true,
  "category": "general",
  "requires": []
}
```

- `id` muss dem Verzeichnisnamen entsprechen.
- `requires` ist eine Liste von Plugin-IDs, die vor diesem Plugin geladen sein
  müssen (Abhängigkeiten). Fehlende/fehlgeschlagene Abhängigkeiten setzen nur
  das betroffene Plugin auf `error`.

## Die `Plugin`-Klasse (`app/plugins/api.py`)

```python
from app.plugins.api import Plugin as PluginBase, PluginSettingDef
from app.widgets.registry import register_widget_class


class Plugin(PluginBase):
    settings_schema = [
        PluginSettingDef("host", "Drucker-IP", "text", "192.168.178.112"),
        PluginSettingDef("poll_interval", "Aktualisierung (Sekunden)", "number", 30),
        PluginSettingDef("notifications", "Benachrichtigungen", "bool", True),
        PluginSettingDef("display_mode", "Anzeige", "select", "compact",
                         ["compact", "detailed"]),
    ]

    def on_load(self) -> None:
        # self.settings  -> namespaced PluginSettings (plugin.<id>.*)
        # self.services  -> ServiceRegistry
        # self.manifest  -> PluginManifest
        pass

    def on_unload(self) -> None:
        pass

    def register_widgets(self) -> None:
        register_widget_class(MyWidget)

    def create_app_view(self, parent=None):
        return MyAppView(parent)   # oder None
```

### Hook-Übersicht

| Hook | Zweck |
|---|---|
| `register_widgets()` | Widget-Klassen global registrieren (`register_widget_class`) |
| `on_load()` | Verbindungen/Timer/Einstellungen einrichten |
| `on_unload()` | Aufräumen (Manager entfernt registrierte Widget-Typen automatisch) |
| `create_app_view(parent)` | Vollbild-Ansicht für den App-Launcher zurückgeben oder `None` |

Der Manager ruft `register_widgets()` vor `on_load()` auf und ruft
`on_unload()` bei Deaktivierung, Neuladen und Shutdown.

## Einstellungen

- `settings_schema` – Liste von `PluginSettingDef(key, label, field_type,
  default, options)`. Feldtypen: `text`, `number`, `bool`, `select`.
- Die Einstellungen werden automatisch als Formular im Plugins-Tab gerendert.
- Werte liegen unter `plugin.<id>.<key>` in der SQLite-`settings`-Tabelle – so
  kollidieren Plugins weder untereinander noch mit Kern-Einstellungen.
- Zugriff von der Plugin-Seite über `self.settings.get(key, default)` /
  `self.settings.set(key, value)`.

### Achtung: Geheimnisse

Settings-Schlüssel, die `token`, `sid`, `password`, `secret` oder `api_key`
enthalten (case-insensitive), werden bei `export_config()` **automatisch
ausgeschlossen** – sofern der Export nicht ausdrücklich
`include_secrets=True` verlangt. Das gilt ohne separate Pflege für jeden
Plugin-Schlüssel.

## Widgets registrieren

Ein Plugin-Widget ist eine normale `BaseWidget`-Unterklasse:

```python
from app.widgets.base import BaseWidget, PropertyDef


class MyWidget(BaseWidget):
    type_name = "my_widget"
    display_name = "Mein Widget"
    category = "Hardware"
    default_size = (240, 160)

    PROPERTY_SCHEMA = [
        PropertyDef("host", "IP", "text", "192.168.178.50", group="Verbindung"),
    ]

    def build_ui(self):
        self.label = QLabel("...")
        self.content_layout.addWidget(self.label)

    def refresh_from_state(self):
        ...
```

In `register_widgets()` mit `register_widget_class(MyWidget)` registrieren.
Beim Entladen entfernt der Manager den Typ automatisch wieder.

## Threading (Pflicht)

Blockierende I/O (HTTP, TCP, Ping, `subprocess`) muss in `QThread`s laufen und
über Qt-Signals zurückmelden. Beispiel-Muster (auch in jedem mitgelieferten
Plugin zu sehen):

```python
class _Job(QThread):
    done = Signal(object)

    def __init__(self, parent):
        super().__init__(parent)

    def run(self):
        try:
            self.done.emit(MyApi().fetch())
        except Exception as exc:
            self.done.emit({"error": str(exc)})
```

Im Widget:

```python
def refresh_from_state(self):
    job = _Job(self)
    job.done.connect(self._show_result)
    job.finished.connect(job.deleteLater)
    job.start()
    self.job = job
```

Damit bleibt der UI-Thread frei und ein langsames/fehlendes Ziel friert das
Panel nicht ein.

## App-Ansichten (App-Launcher)

Überschreibt ein Plugin `create_app_view()`, erscheint es im App-Launcher
(`app/ui/app_launcher.py`) und wird über `MainWindow._open_plugin_app` in den
bestehenden Qt-Stack geladen (nie als externer Prozess). Der Browser greift
dort optional auf QtWebEngine zu – mit sicherem Fallback, wenn das Modul fehlt.

## Fehlerisolation – Verhalten

- Kaputtes Manifest → Plugin landet mit Fehlermeldung im `error`-Zustand.
- Kaputtes `plugin.py`/Importfehler → Fehler isoliert, App startet weiter.
- Fehler in `register_widgets()` → bereits registrierte Widgets des Plugins
  werden wieder entfernt.
- Fehler in `on_load()` → Plugin wird nicht aktiviert, Widgets entfernt.
- Fehler in `on_unload()` → geloggt, Rest des Unloads läuft weiter.

Der Plugins-Tab (Einstellungen) zeigt pro Plugin: Status (installiert/aktiv/
deaktiviert/fehler), Aktivieren, Deaktivieren, Neu laden und das generierte
Einstellungsformular.

## Minimalbeispiel

Siehe [Beispiel-Plugin](../plugins/example_plugin/) – es demonstriert den
kompletten Lifecycle (lädt sauber, setzt Marker-Einstellungen, registriert
nichts Eigenes) ohne Fake-Widgets.

## Weitere Referenz

- [Plugin-Katalog](plugins/README.md) – alle mitgelieferten Plugins mit
  Detailinfos zu ihren APIs.
- `app/plugins/manager.py` – PluginManager (Discovery, Load-Order,
  Dependency-Resolution, Widget-Unregistering).
- `app/plugins/discovery.py` – On-Disk-Format und fehlertolerantes Importieren.
- `app/plugins/plugin_settings.py` – namespaced Settings.
- `app/plugins/api.py` – öffentliche API/Contracts.