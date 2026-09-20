# UI-Layer (`app/ui/`)

Die komplette Oberfläche. Alle Dialoge sind touch-first und bedarfsgerecht
generiert – spezifische Widget-Kenntnis steckt nur dort, wo sie nötig ist.

## Übersicht

| Modul | Verantwortung |
|---|---|
| `main_window.py` | App-Shell, Routing, Standby-Zustandsmaschine, Editor-Gesten |
| `dashboard.py` | Canvas-Rendering (Normal- + Editor-Modus) und Dashboard-Shell |
| `editor.py` | Editor-Werkzeugleiste, Undo/Redo, Vorlagen, Speichern/Abbrechen |
| `properties.py` | Dynamisches Eigenschaftenpanel (schema-getrieben) |
| `element_library.py` | Widget-Bibliothek + Entity-Picker |
| `navigation.py` | Bottom-/Sidebar-Navigation zwischen Seiten |
| `themes.py` | Theme-Presets, Stylesheet-Generator, Theme-Editor |
| `setup_wizard.py` | Ersteinrichtungsassistent |
| `settings_screen.py` | Einstellungen (Verbindung, Design, Standby, Plugins, Backup) |
| `app_launcher.py` | Touch-Launcher für Plugin-Apps (z. B. Browser) |
| `custom_widget_builder.py` | Dialog zum Zusammenstellen eigener Widgets |

## `main_window.py` – Hauptfenster

- QMainWindow mit QStackedWidget-Routing zwischen Dashboard, Editor,
  Einstellungen, Wizard und Plugin-Apps.
- **Standby-Zustandsmaschine** `NORMAL → DIMMED → OFF`, jede Interaktion
  setzt auf `NORMAL` zurück. DIMMED = halbtransparentes Overlay, OFF = schwarz
  + Backlight aus via sysfs. Konfigurierbar über die
  `standby_*`-Settings; Screensaver-Modus `digital_clock` oder `system_info`.
- Editor-Aktivierung per 3-Sekunden-Langdruck oben links.
- Verbindungs-Badge (REST/WebSocket-Status).
- Start der Laufzeit (`_start_runtime`) mit State-Manager, Service-Registry,
  Plugin-Manager, Workflow-Engine, Dashboard, Editor und Einstellungen.
- Plugin-Apps werden in denselben Qt-Stack geöffnet (nie externer Prozess).

## `dashboard.py` – Dashboard-Canvas

- `DashboardCanvas` rendert die Widgets einer Seite frei positioniert
  (x/y/w/h/z), normal und im Editor-Modus (Edit-Mode schaltet `edit_mode`
  und fügt Auswahl/Verschieben/Skalieren hinzu).
- Hört auf `state_manager.entity_updated` und leitet Änderungen an die
  betroffenen Widgets (`on_state_changed`) weiter.
- `clear()`/`delete_widget()` rufen vor dem Löschen `inst.hide()` auf, damit
  Widgets mit laufenden Threads (z. B. Flashforge-Kamera) sauber beendet
  werden (`hideEvent` → Stream stoppen) und kein Signal in ein gelöschtes
  Objekt läuft.

## `editor.py` – Visueller Editor

- Canvas im Edit-Modus + Werkzeugleiste (`+ Element`, Ebenen, Duplizieren,
  Löschen, Rückgängig/Wiederholen, Vorlagen, Speichern/Abbrechen).
- Undo/Redo über Ganz-Seiten-Snapshots der Widget-Zeilen (einfach und robust).
- Kopieren/Einfügen (Ctrl+C/V), Mehrfachauswahl (Shift+Click).
- Seitenverwaltung (hinzufügen/löschen, Schutz der letzten Seite).

## `properties.py` – Eigenschaftenpanel

- Zeigt die Felder aus `widget.full_schema()` = `COMMON_SCHEMA` + widget-eigene
  `PROPERTY_SCHEMA` – **kein** widget-spezifischer Code.
- Feldtypen: `text`, `number`, `color`, `bool`, `select`, `icon`, `entity`
  (mit Entity-Picker-Link), `font_size`, `image` (Dateiauswahl), `action`
  (öffnet Builder-Dialoge wie den Custom-Widget-Builder).

## `element_library.py` – Bibliothek + Entity-Picker

- Modal-Dialog mit allen Widget-Typen, gruppiert nach `category`.
- Entity-Picker gruppiert Home-Assistant-Entities nach Räumen/Arealen
  (`friendly_name`/`area`) mit Suchfeld – keine Entity-ID von Hand tippen.

## `navigation.py` – Navigation

- Datengetrieben: spiegelt die Seiten aus der Datenbank.
- Modi: `bottom` (Leiste unten) oder `sidebar` (vertikale Seitenleiste),
  einstellbar über `navigation_style`.

## `themes.py` – Themes

- Themes sind Dicts aus Design-Tokens; `build_stylesheet(theme)` erzeugt ein
  vollständiges Qt-Stylesheet (QMainWindow, QWidget, QLabel, QPushButton,
  QLineEdit, QComboBox, QSlider, QToolTip, Navigation).
- `BUILT_IN_THEMES`: Minimal, Dark Glass, Industrial, Modern.
- Auto-Modus wechselt nach Tageszeit (7–19 Uhr hell, sonst dunkel), Check
  alle 5 Minuten. Benutzerdefinierte Themes über die Einstellungen speicherbar.

## `setup_wizard.py` – Ersteinrichtung

- Beim ersten Start (`setup_complete == False`): Sprache, Home-Assistant-Adresse
  + Long-Lived-Token oder Demo-Modus.
- Signal `finished(dict)` übergibt die Auswahl an das Hauptfenster.

## `settings_screen.py` – Einstellungen

Tabs für Verbindung (HA-URL/Token, Demo-Modus – als Tab im Hauptfenster),
Design (Themes, Orientierung, Auflösung, Navigation), Standby & Display,
Sicherheit (Editor-PIN), Plugins (Aktivieren/Deaktivieren/Neu laden +
generierter Einstellungsdialog aus `settings_schema`) und
Backup/Export/Import. Alles grafisch – keine Konfigdatei wird von Hand editiert.

## `app_launcher.py` – Plugin-App-Launcher

- Listet alle Plugins, die `create_app_view()` überschreiben.
- Öffnet die Plugin-App im bestehenden Qt-Stack; Zurück-Button führt zum Panel.

## `custom_widget_builder.py` – Custom Widget Builder

- Dialog zum Zusammenstellen eigener Widgets aus einer Palette:
  Text, Icon, Sensor-Wert, Fortschrittsbalken, Button.
- Elemente werden per sicherer Expression-Templates (`app/core/expressions.py`)
  an Entities gebunden.
- Speichern nutzt den normalen `PropertiesPanel`-Pfad (`elements`-Property)
  – keine parallele Speicherung.