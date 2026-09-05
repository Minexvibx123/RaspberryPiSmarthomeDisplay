# HomePanel – Visual Home Assistant Touchpanel

Ein natives, hochgradig anpassbares Touchpanel für Home Assistant, gebaut für
Raspberry Pi 5 + 7"-Touchdisplay. Der Fokus liegt auf **visueller
Anpassbarkeit ohne YAML/JSON/Code** – Elemente werden per Tippen, Ziehen und
Skalieren direkt auf dem Bildschirm bearbeitet.

## Features

- Verbindung zu Home Assistant über REST + WebSocket (Live-Updates, Auto-Reconnect)
- Demo-Modus mit simulierten Entities (kein Home Assistant nötig zum Testen)
- Visueller Editor: Drag & Drop, Skalieren, Eigenschaftenpanel, Ebenen (z-Index),
  Duplizieren, Löschen, Rückgängig/Wiederholen, Raster/Snap
- Editor: Copy/Paste (Ctrl+C/V), Multi-Select (Shift+Click), bedingte Sichtbarkeit
- Element-Bibliothek (42 Kern-Widget-Typen, Plugins registrieren weitere zur Laufzeit):
  - Steuerung: Button, Licht, Schalter, Slider, Thermostat, Rollladen, Medienplayer, Timer, Lüfter, Schloss, Luftbefeuchter, Alarmanlage, Saugroboter, Szenen-Grid, Zahlenwert, Auswahlliste
  - Anzeige: Sensor, Wetter, Uhr, Text, Icon, Entity-Liste, Kamera, Sensor-Verlauf, Kalender, To-Do-Liste, Person, Container, Benachrichtigungen, Energie
  - Internet: Kryptokurs, Aktienkurs, Wechselkurs, Zitat, Witz, Feiertag, Internet-Status, News-Feed
  - System: System-Monitor, Konsole
  - Apps: Web-Panel (optional, QtWebEngine mit sicherem Fallback ohne Absturz)
  - Custom: Eigenes Widget (siehe „Custom Widget Builder“ unten)
- Animation Engine: kurze, performante Fade/Slide/Pulse/Bounce/Shake/Glow-Effekte bei Eintritt und Zustandswechsel, konfigurierbar pro Widget
- Bedingtes Styling: Hintergrund-/Textfarbe abhängig von Entity-Zustand ändern (equals/not_equals/greater_than/less_than/contains/online/offline/true/false)
- Custom Widget Builder: eigene Widgets aus Text/Icon/Sensor-Wert/Fortschrittsbalken/Button zusammenstellen, ohne Python – sichere Textvorlagen wie `{{ state | round(1) }}`
- Workflow-Engine (Grundgerüst): einfache WENN-Entity-Zustand-DANN-Aktion/Warten-Automationen, gespeichert in SQLite
- Bedingte Sichtbarkeit: Widgets nur bei bestimmtem Entity-Zustand anzeigen (oder invertiert)
- Hintergrundbilder und Farbverläufe (vertikal/horizontal/radial) pro Widget; eigene Hintergrundbilder pro Seite und eigene Bilder als Icons (Datei-Auswahl direkt im Editor)
- COMMON_SCHEMA: Schriftart, Icon-Position, Innenabstand für jedes Widget
- Auto Dark/Light Mode (nach Tageszeit: 7:00–19:00 hell, sonst dunkel)
- Zweistufiger Standby nach Inaktivität: Abdunkeln nach 2 Min., Display aus nach 5 Min. (Zeiten und Abdunkel-Stärke in den Einstellungen; Aufwecken per Berührung)
- Screensaver-Modus wählbar: digitale Uhr oder Systeminformationen (CPU/RAM/Temperatur), optional mit eigenem Hintergrundbild
- Raum-basierte Entity-Auswahl (keine manuelle Entity-ID nötig)
- Themes (4 Presets: Minimal, Dark Glass, Industrial, Modern) + Light/Dark/Auto
- Beliebig viele Seiten mit Bottom-Navigation oder Seitenleiste; Seiten im Editor löschen (mit Bestätigung, Schutz für die letzte Seite)
- Responsive Layout (skaliert auf jede Auflösung/Orientierung)
- SQLite-Speicherung aller Seiten/Widgets/Themes/Vorlagen/Workflows/Einstellungen
- Backup, Export/Import der Konfiguration über die UI (Geheimnisse wie Tokens/Sessions/Passwörter werden beim Export automatisch ausgeschlossen)
- Einrichtungsassistent beim ersten Start
- Editor-Modus per 3-Sekunden-Langdruck auf die obere linke Ecke, optional PIN-geschützt
- Plugin-System mit grafischer Verwaltung (aktivieren/deaktivieren/neu laden, Fehler werden isoliert angezeigt statt die App abstürzen zu lassen); mitgelieferte Plugins:
  - **System-Monitoring**: CPU/RAM/Speicher/Netzwerk sowie systemd-Dienste (Start/Stop/Neustart mit Bestätigung)
  - **Flashforge**: Live-Status/-Steuerung für Flashforge-3D-Drucker über das dokumentierte TCP-Protokoll (Port 8899)
  - **Pi-hole**: Statistiken und zeitlich begrenztes Deaktivieren der Blockierung über die Pi-hole-v6-API
  - **Netzwerk**: Erreichbarkeit einzelner Geräte per Ping
  - **Docker**: Container-Liste, Start/Stop/Neustart (lokaler Docker-Socket)
  - **Browser**: interner Touch-Browser (optional, QtWebEngine) mit Bookmarks, öffnet sich innerhalb von HomePanel über den App-Launcher
- systemd-Service + Kiosk-Skript für Autostart auf dem Pi

## Projektstruktur

```
app/
├── main.py                  Einstiegspunkt
├── core/
│   ├── homeassistant.py     REST-Client
│   ├── websocket.py         WebSocket-Client mit Auto-Reconnect
│   ├── database.py          SQLite-Zugriff (Seiten/Widgets/Themes/Vorlagen/Workflows/Settings)
│   ├── state_manager.py     Zentrale Entity-Zustände + Demo-Modus
│   ├── settings.py          Typisierte Settings-Wrapper
│   ├── service_registry.py  Zentrale Service-Registry für Plugins
│   ├── animations.py        Zentrale Animation Engine (Fade/Slide/Pulse/Bounce/Shake/Glow)
│   ├── conditions.py        Sichere Bedingungsauswertung (Sichtbarkeit + Styling)
│   ├── expressions.py       Sicheres Whitelist-Template-System (kein eval/exec)
│   └── workflows.py         Listenbasierte WENN/DANN/WARTEN-Workflow-Engine
├── plugins/
│   ├── api.py, discovery.py, manager.py, plugin_settings.py   Plugin-Kern
│   └── ...                  siehe plugins/ im Projektwurzelverzeichnis
├── ui/
│   ├── main_window.py        App-Shell, Editor-Gesten, Routing, Standby/Screensaver
│   ├── dashboard.py           Canvas-Rendering (normal + Editor)
│   ├── editor.py               Editor-Werkzeugleiste, Undo/Redo, Vorlagen, Speichern/Abbrechen
│   ├── properties.py            Dynamisches Eigenschaftenpanel (inkl. Builder-Aktionen)
│   ├── custom_widget_builder.py  Dialog zum Zusammenstellen eigener Widgets
│   ├── app_launcher.py           Touch-Launcher für Plugin-Apps (z. B. Browser)
│   ├── element_library.py        Widget-Bibliothek + Entity-Picker
│   ├── navigation.py              Bottom-/Sidebar-Navigation
│   ├── themes.py                   Theme-Presets + Stylesheet-Generator + Theme-Editor
│   ├── setup_wizard.py              Ersteinrichtung
│   └── settings_screen.py            Einstellungen (Verbindung, Design, Standby, Plugins, Backup)
└── widgets/
    ├── base.py               Basisklasse + Property-Schema-System (inkl. Animation/Styling-Felder)
    ├── button.py, light.py, switch.py, sensor.py, thermostat.py,
    │   slider.py, cover.py, weather.py, clock.py, text.py,
    │   icon_widget.py, entity_list.py, console.py, energy.py, web.py
    ├── custom_widget.py      Eigenes Widget (Custom Widget Builder Rendering)
    └── registry.py           Widget-Typ-Registry (Plugin-Seam)

plugins/                      Echte Integrationen, siehe Feature-Liste oben
├── example_plugin/
├── system_monitor/
├── flashforge/
├── pihole/
├── network/
├── docker/
└── browser/
```

## Entwicklung / Ausführen

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main --windowed   # Fenster statt Fullscreen
python -m app.main --windowed --demo   # erzwingt Demo-Modus
```

Beim ersten Start öffnet sich der Einrichtungsassistent (Sprache, Home-Assistant-
Adresse + Token oder Demo-Modus). Danach startet das Panel direkt in den
Normalbetrieb.

## Editor-Modus aktivieren

Oben links 3 Sekunden gedrückt halten (optional durch PIN in den Einstellungen
geschützt). Im Editor: `+ Element` fügt ein Widget aus der Bibliothek hinzu,
Tippen wählt ein Widget aus (Eigenschaftenpanel rechts), der blaue Punkt an der
Ecke skaliert, Ziehen verschiebt. `Speichern` behält die Änderungen,
`Abbrechen` verwirft alles seit dem Öffnen des Editors.

## Autostart auf dem Raspberry Pi

Für eine neue Installation direkt aus GitHub auf dem Pi:

```bash
curl -fsSL https://raw.githubusercontent.com/Minexvibx123/RaspberryPiSmarthomeDisplay/main/scripts/install-github.sh | bash
```

Standardmäßig wird nach `~/homepanel` installiert. Ein bestehendes Panel wird
ohne Dateisynchronisation direkt aus GitHub aktualisiert:

```bash
~/homepanel/scripts/update-github.sh
```

Das Update prüft vor dem Start auf lokale Änderungen, verwendet ausschließlich
einen Git-Fast-Forward, aktualisiert die Python-Abhängigkeiten und startet den
laufenden HomePanel-Service anschließend wieder. Die lokale SQLite-Datenbank in
`data/` bleibt dabei unverändert.

Für eine lokale Entwicklungskopie bleibt das bisherige Setup verfügbar:

```bash
./scripts/install.sh
sudo systemctl start homepanel.service
```

Das Skript legt ein virtualenv an, installiert Abhängigkeiten und richtet einen
systemd-Service ein, der HomePanel im Kiosk-/Fullscreen-Modus startet.
Für den Standby-Modus (Display abschalten) installiert es zusätzlich eine
udev-Regel, die der Gruppe `video` Schreibrechte auf die Backlight-Sysfs-
Dateien gibt – der Benutzer muss dafür Mitglied der Gruppe `video` sein
(nach dem ersten Setup einmal neu anmelden).

## Architektur-Hinweise für Erweiterungen

- Neue Widgets: Klasse in `app/widgets/` mit `PROPERTY_SCHEMA` anlegen und in
  `app/widgets/registry.py` eintragen – Editor, Bibliothek und
  Eigenschaftenpanel benötigen keine Änderungen.
- Neue Themes: Presets in `app/ui/themes.py` (`BUILT_IN_THEMES`) ergänzen oder
  über die Einstellungen als benutzerdefiniertes Theme speichern.
- Mehrere Panels/zentrale Konfiguration: `Database.export_config()` /
  `import_config()` bilden bereits die Grundlage für Sync zwischen Geräten.

## Sicherheit

- Das Home-Assistant-Token wird ausschließlich lokal in SQLite gespeichert und
  nie geloggt.
- Editor und Einstellungen können optional per PIN geschützt werden.
- Es werden keine zusätzlichen Netzwerk-Ports geöffnet; die App verbindet sich
  ausgehend zu Home Assistant und optional zu Plugin-Endpunkten (Flashforge,
  Pi-hole, Docker-Socket, Netzwerkgeräte).
- Beim Konfigurations-Export werden Einstellungsschlüssel, die wie `token`,
  `sid`, `password`, `secret` oder `api_key` aussehen, automatisch ausgeschlossen
  (auch für Plugin-Einstellungen), sofern der Export nicht ausdrücklich
  Geheimnisse einschließen soll.

## Lizenz

MIT, siehe [LICENSE](LICENSE).
