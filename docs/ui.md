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
| `service_actions.py` | Editor für geordnete Home-Assistant-Service-Aktionen |
| `element_library.py` | Widget-Bibliothek + Entity-Picker |
| `navigation.py` | Bottom-/Sidebar-Navigation zwischen Seiten |
| `themes.py` | Theme-Presets, Stylesheet-Generator, Theme-Editor |
| `setup_wizard.py` | Ersteinrichtungsassistent |
| `settings_screen.py` | Einstellungen (Verbindung, Design, Standby, Plugins, Backup) |
| `workflow_editor.py` | Workflow-Verwaltung und -Editor (Trigger, Aktionen, Wartezeiten) |
| `app_launcher.py` | Touch-Launcher für Plugin-Apps (z. B. Browser) |
| `app_store.py` | Lokaler Katalog zum Aktivieren/Deaktivieren gebündelter App-Plugins |
| `custom_widget_builder.py` | Dialog zum Zusammenstellen eigener Widgets |

## `main_window.py` – Hauptfenster

- QMainWindow mit QStackedWidget-Routing zwischen Dashboard, Editor,
  Einstellungen, Wizard und Plugin-Apps.
- **Standby-Zustandsmaschine** `NORMAL → DIMMED → OFF`, jede Interaktion
  setzt auf `NORMAL` zurück. DIMMED = halbtransparentes Overlay, OFF = schwarz
  + Backlight aus via sysfs. Konfigurierbar über die
  `standby_*`-Settings; Screensaver-Modus `digital_clock` oder `system_info`.
- Beim Start wird das Backlight auf maximale Helligkeit zurückgesetzt, damit
  ein Neustart während `OFF` kein dauerhaft schwarzes Panel hinterlässt.
  Touch-Ereignisse innerhalb des HomePanel-Fensters wecken das Display und
  setzen die Inaktivitäts-Timer zurück.
- Nach der ersten Touch-Eingabe wird der Mauszeiger ausgeblendet; erst eine
  nicht synthetisierte Mausbewegung blendet ihn wieder ein.
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
- Im normalen Dashboard-Modus wechselt ein horizontaler Wisch nach links/rechts
  zur nächsten/vorherigen Seite. Während der Fingerbewegung liegt die Zielseite
  bereits unter einem verschiebbaren Abbild der aktuellen Seite. Beim Loslassen
  wird ab 14 % Canvas-Breite (mindestens 80 px) abgeschlossen; kürzere Wischs federn zur
  Ausgangsseite zurück. Kurze oder überwiegend vertikale Bewegungen werden
  ignoriert; an den Rändern gibt es keinen zyklischen Sprung. Im Editor-Modus
  bleiben Ziehen und Skalieren unverändert.
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
- Die `action`-Property des Button-Widgets öffnet `ServiceActionsDialog`:
  Domain, Service, optionale Entity-ID und Parameter als JSON-Objekt; die
  geordnete Aktionsliste wird in der Widget-Konfiguration gespeichert. Häufige
  Ketten können als `service_actions`-Vorlage gespeichert und auf weitere
  Buttons angewendet werden.

## `element_library.py` – Bibliothek + Entity-Picker

- Modal-Dialog mit allen Widget-Typen, gruppiert nach `category`.
- Entity-Picker gruppiert Home-Assistant-Entities nach Räumen/Arealen
  (`friendly_name`/`area`) mit Suchfeld – keine Entity-ID von Hand tippen.

## `navigation.py` – Navigation

- Datengetrieben: spiegelt die Seiten aus der Datenbank.
- Modi: `bottom` (Leiste unten) oder `sidebar` (vertikale Seitenleiste),
  einstellbar über `navigation_style`.

## `design.py` – Design-System

- Zentrale Tokens, `readable()` (WCAG-Kontrast), `apply_theme()` (QPalette +
  Stylesheet) und `widget_default()` für themenabhängige Widget-Standardwerte.
- Text- und Akzentfarben der Widgets werden gegen den Hintergrund geprüft und
  bei zu geringem Kontrast automatisch korrigiert.

## `themes.py` – Themes

- Themes sind Dicts aus Design-Tokens; `build_stylesheet(theme)` erzeugt ein
  vollständiges Qt-Stylesheet (QMainWindow, QWidget, QLabel, QPushButton,
  QLineEdit, QComboBox, QSlider, QToolTip, Navigation).
- `BUILT_IN_THEMES`: Aurora, Porcelain, Minimal, Dark Glass, Industrial, Modern.
- Auto-Modus wechselt nach Tageszeit (7–19 Uhr hell, sonst dunkel), Check
  alle 5 Minuten. Benutzerdefinierte Themes über die Einstellungen speicherbar.
- Icon-Packs: HomePanel Line, Font Awesome 6 Solid, Material Design Icons,
  Phosphor und Remix Icons. Die Auswahl greift sofort für Dashboard und Editor;
  nicht gemappte Symbole nutzen den eingebauten Vektor-Fallback.

## `setup_wizard.py` – Ersteinrichtung

- Beim ersten Start (`setup_complete == False`): Sprache, Home-Assistant-Adresse
  + Long-Lived-Token oder Demo-Modus.
- Signal `finished(dict)` übergibt die Auswahl an das Hauptfenster.

## `settings_screen.py` – Einstellungen

Tabs für Verbindung (HA-URL/Token, Demo-Modus – als Tab im Hauptfenster),
Design (Themes, Orientierung, Auflösung, Navigation), Standby & Display,
Automationen (Entity-Zustand, Aktionskette, Wartezeiten, Aktivieren/Deaktivieren),
Sicherheit (Editor-PIN), Plugins (Aktivieren/Deaktivieren/Neu laden +
generierter Einstellungsdialog aus `settings_schema`) und
Backup/Export/Import. Alles grafisch – keine Konfigdatei wird von Hand editiert.
Das Icon-Pack ist im Design-Tab auswählbar und wird ohne Neustart auf Dashboard
und Editor angewendet.

## `app_launcher.py` – App-Launcher und Store

- Der Launcher zeigt alle installierten Apps aus dem `AppCatalog`
  (`app/apps/`: 30 eingebaute Apps plus Plugin-Apps).
- Der App-Store (`app_store.py`) installiert/entfernt Apps und kann Pakete aus
  GitHub-Repositories laden (`app/plugins/installer.py`).
- Sicherheit der Repo-Installation: nur `https://github.com`, Größen- und
  Dateilimits, Schutz vor Zip-Slip und Symlinks, kein Import beim Installieren,
  Installation deaktiviert (Marker `.homepanel-repo`), Bestätigungsdialoge.
- Entfernen deaktiviert eingebaute/lokale Pakete; Repo-Pakete werden gelöscht.

## `custom_widget_builder.py` – Custom Widget Builder

- Dialog zum Zusammenstellen eigener Widgets aus einer Palette:
  Text, Icon, Sensor-Wert, Fortschrittsbalken, Button.
- Elemente werden per sicherer Expression-Templates (`app/core/expressions.py`)
  an Entities gebunden.
- Speichern nutzt den normalen `PropertiesPanel`-Pfad (`elements`-Property)
  – keine parallele Speicherung.