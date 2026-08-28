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
- Element-Bibliothek (40 Widget-Typen):
  - Steuerung: Button, Licht, Schalter, Slider, Thermostat, Rollladen, Medienplayer, Timer, Lüfter, Schloss, Luftbefeuchter, Alarmanlage, Saugroboter, Szenen-Grid, Zahlenwert, Auswahlliste
  - Anzeige: Sensor, Wetter, Uhr, Text, Icon, Entity-Liste, Kamera, Sensor-Verlauf, Kalender, To-Do-Liste, Person, Container, Benachrichtigungen, Energie
  - Internet: Kryptokurs, Aktienkurs, Wechselkurs, Zitat, Witz, Feiertag, Internet-Status, News-Feed
  - System: System-Monitor, Konsole
- Bedingte Sichtbarkeit: Widgets nur bei bestimmtem Entity-Zustand anzeigen (oder invertiert)
- Hintergrundbilder und Farbverläufe (vertikal/horizontal/radial) pro Widget; eigene Hintergrundbilder pro Seite und eigene Bilder als Icons (Datei-Auswahl direkt im Editor)
- COMMON_SCHEMA: Schriftart, Icon-Position, Innenabstand für jedes Widget
- Auto Dark/Light Mode (nach Tageszeit: 7:00–19:00 hell, sonst dunkel)
- Zweistufiger Standby nach Inaktivität: Abdunkeln nach 2 Min., Display aus nach 5 Min. (Zeiten und Abdunkel-Stärke in den Einstellungen; Aufwecken per Berührung)
- Raum-basierte Entity-Auswahl (keine manuelle Entity-ID nötig)
- Themes (4 Presets: Minimal, Dark Glass, Industrial, Modern) + Light/Dark/Auto
- Beliebig viele Seiten mit Bottom-Navigation oder Seitenleiste; Seiten im Editor löschen (mit Bestätigung, Schutz für die letzte Seite)
- Responsive Layout (skaliert auf jede Auflösung/Orientierung)
- SQLite-Speicherung aller Seiten/Widgets/Themes/Einstellungen
- Backup, Export/Import der Konfiguration über die UI
- Einrichtungsassistent beim ersten Start
- Editor-Modus per 3-Sekunden-Langdruck auf die obere linke Ecke, optional PIN-geschützt
- systemd-Service + Kiosk-Skript für Autostart auf dem Pi

## Projektstruktur

```
app/
├── main.py                  Einstiegspunkt
├── core/
│   ├── homeassistant.py     REST-Client
│   ├── websocket.py         WebSocket-Client mit Auto-Reconnect
│   ├── database.py          SQLite-Zugriff (Seiten/Widgets/Themes/Settings)
│   ├── state_manager.py     Zentrale Entity-Zustände + Demo-Modus
│   └── settings.py          Typisierte Settings-Wrapper
├── ui/
│   ├── main_window.py        App-Shell, Editor-Gesten, Routing
│   ├── dashboard.py           Canvas-Rendering (normal + Editor)
│   ├── editor.py               Editor-Werkzeugleiste, Undo/Redo, Speichern/Abbrechen
│   ├── properties.py            Dynamisches Eigenschaftenpanel
│   ├── element_library.py        Widget-Bibliothek + Entity-Picker
│   ├── navigation.py              Bottom-/Sidebar-Navigation
│   ├── themes.py                   Theme-Presets + Stylesheet-Generator
│   ├── setup_wizard.py              Ersteinrichtung
│   └── settings_screen.py            Einstellungen (Verbindung, Design, Backup)
└── widgets/
    ├── base.py               Basisklasse + Property-Schema-System
    ├── button.py, light.py, switch.py, sensor.py, thermostat.py,
    │   slider.py, cover.py, weather.py, clock.py, text.py,
    │   icon_widget.py, entity_list.py, console.py, energy.py
    └── registry.py           Widget-Typ-Registry (Plugin-Seam)
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
  ausgehend zu Home Assistant.

## Lizenz

MIT, siehe [LICENSE](LICENSE).
