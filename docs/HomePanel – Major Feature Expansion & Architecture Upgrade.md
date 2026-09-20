# HomePanel – Major Feature Expansion & Architecture Upgrade

Du arbeitest an einem bestehenden Projekt namens **HomePanel**. Ziel ist es, das bestehende Projekt nicht neu zu schreiben, sondern professionell und modular weiterzuentwickeln.

HomePanel ist eine native **PySide6 / Qt6 Touchpanel-Anwendung für Raspberry Pi 5**, die als hochgradig anpassbares Dashboard für Home Assistant dient.

Das zentrale Ziel des Projekts ist:

> Eine vollständig visuell konfigurierbare Touch-Oberfläche für Raspberry Pi, Smart Home, lokale Dienste, Hardware und Systemfunktionen zu schaffen – ohne YAML, JSON-Konfiguration oder manuelle Codebearbeitung durch den Benutzer.

Der Benutzer soll möglichst alles direkt auf dem Touchscreen konfigurieren können.

---

# 1. Bestehende Architektur unbedingt erhalten

Das Projekt besitzt bereits eine funktionierende Architektur mit:

- Python
- PySide6 / Qt6
- SQLite
- Home Assistant REST API
- Home Assistant WebSocket API
- visuellem Dashboard Editor
- Widget-System
- Theme-System
- Seitenverwaltung
- Drag & Drop
- Resize
- Undo / Redo
- Conditional Visibility
- Standby-System
- Home Assistant Entity Picker
- automatischem Property Editor

Die bestehende Architektur darf nicht unnötig zerstört oder komplett ersetzt werden.

Neue Funktionen müssen sich möglichst natürlich in das bestehende System integrieren.

Die aktuelle Widget-Architektur basiert auf einer gemeinsamen `BaseWidget` Klasse und `PropertyDef`.

Neue Widgets sollen weiterhin nach diesem Prinzip funktionieren.

Beispiel:

```python
class MyWidget(BaseWidget):

    type_name = "my_widget"
    display_name = "My Widget"
    category = "Kategorie"
    icon = "🎯"
    default_size = (200, 140)

    PROPERTY_SCHEMA = [
        PropertyDef(
            "my_property",
            "Meine Eigenschaft",
            "text",
            "default"
        )
    ]

    def build_ui(self):
        pass

    def refresh_from_state(self):
        pass
```

Der bestehende visuelle Editor und der Property Editor sollen neue Eigenschaften automatisch erkennen.

---

# 2. Langfristige Vision

HomePanel soll langfristig nicht nur ein Home Assistant Dashboard sein.

Die Architektur soll in diese Richtung erweitert werden:

```text
HomePanel
│
├── Home Dashboard
│
├── Smart Home
│   ├── Home Assistant
│   ├── Automationen
│   └── Szenen
│
├── Hardware
│   ├── Flashforge 5M Pro
│   ├── Kameras
│   ├── Sensoren
│   └── zukünftige Geräte
│
├── Network
│   ├── Pi-hole
│   ├── Netzwerkgeräte
│   ├── Internetstatus
│   └── Netzwerkmonitoring
│
├── System
│   ├── Raspberry Pi Monitoring
│   ├── Services
│   ├── Speicher
│   ├── CPU / RAM
│   └── Docker
│
├── Apps
│   ├── Browser
│   ├── Web Apps
│   ├── lokale Anwendungen
│   └── zukünftige Plugins
│
└── Customization
    ├── Themes
    ├── Animationen
    ├── Custom Widgets
    ├── Conditional Styling
    └── Layouts
```

Home Assistant soll weiterhin ein wichtiger Bestandteil bleiben, aber HomePanel soll nicht ausschließlich von Home Assistant abhängig sein.

---

# 3. Plugin-System

Eine der wichtigsten Erweiterungen ist ein richtiges Plugin-System.

Ziel:

Neue Funktionen sollen später möglichst als Plugin hinzugefügt werden können.

Beispiel:

```text
plugins/
│
├── flashforge/
│   ├── __init__.py
│   ├── manifest.json
│   ├── plugin.py
│   ├── api.py
│   └── widgets/
│       ├── status.py
│       ├── temperature.py
│       ├── progress.py
│       └── camera.py
│
├── pihole/
│   ├── __init__.py
│   ├── manifest.json
│   ├── plugin.py
│   ├── api.py
│   └── widgets/
│
├── browser/
│   ├── __init__.py
│   ├── manifest.json
│   └── plugin.py
│
└── animations/
    ├── __init__.py
    ├── manifest.json
    └── plugin.py
```

## Plugin Manifest

Jedes Plugin soll Metadaten besitzen:

```json
{
    "id": "flashforge",
    "name": "Flashforge Integration",
    "version": "1.0.0",
    "description": "Integration für Flashforge 5M Pro",
    "author": "HomePanel",
    "enabled": true,
    "category": "hardware",
    "requires": []
}
```

## Plugin Manager

Es soll eine grafische Plugin-Verwaltung geben.

Funktionen:

- installierte Plugins anzeigen
- Plugin aktivieren/deaktivieren
- Plugin Einstellungen öffnen
- Plugin Version anzeigen
- Plugin Status anzeigen
- Plugin Fehler anzeigen
- Plugin sauber laden und entladen
- Widgets automatisch registrieren

Plugins dürfen das Hauptprogramm nicht komplett zum Absturz bringen.

Fehler eines Plugins sollen abgefangen und im Plugin Manager angezeigt werden.

---

# 4. Flashforge Adventurer 5M Pro Integration

Es soll ein eigenes Flashforge Plugin entwickelt werden.

Das Plugin soll die Grundlage für die Integration eines Flashforge Adventurer 5M Pro bilden.

Die Architektur muss so gestaltet sein, dass später weitere Drucker oder Schnittstellen ergänzt werden können.

## Drucker Dashboard

Es soll eine eigene Drucker-Seite geben.

Mögliche Anzeige:

```text
┌───────────────────────────────────────┐
│ 🖨 FLASHFORGE ADVENTURER 5M PRO       │
├───────────────────────────────────────┤
│                                       │
│            LIVE CAMERA                │
│                                       │
├───────────────┬───────────────────────┤
│ Progress      │ Status                │
│               │                       │
│ ███████░░░    │ Printing              │
│ 63 %          │                       │
├───────────────┼───────────────────────┤
│ Nozzle        │ Bed                   │
│ 220 °C        │ 60 °C                 │
├───────────────┴───────────────────────┤
│                                       │
│ [ Pause ] [ Continue ] [ Cancel ]     │
│                                       │
└───────────────────────────────────────┘
```

## Flashforge Widgets

Folgende Widgets sollen vorbereitet werden:

### PrinterStatusWidget

Zeigt:

- Offline
- Idle
- Heating
- Printing
- Paused
- Finished
- Error

### PrintProgressWidget

Zeigt:

- Fortschritt in Prozent
- Fortschrittsbalken
- verbleibende Zeit
- vergangene Zeit
- aktueller Layer, falls verfügbar

### PrinterTemperatureWidget

Zeigt:

- Nozzle Temperatur
- Bed Temperatur
- Zieltemperaturen
- optional weitere verfügbare Temperatursensoren

### PrinterCameraWidget

Funktionen:

- Livebild
- Vollbild
- automatische Aktualisierung
- Snapshot
- später optional Timelapse

### PrintControlWidget

Funktionen:

- Pause
- Fortsetzen
- Abbrechen
- Bestätigung bei Abbruch

### PrintQueueWidget

Eine grafische Druckwarteschlange:

```text
DRUCKWARTESCHLANGE

1. Gearbox.gcode
   2h 14min

2. Case.gcode
   4h 32min

3. RobotHand.gcode
   7h 10min
```

Die API-Anbindung muss sauber vom UI getrennt werden.

---

# 5. Pi-hole Integration

Es soll ein eigenes Pi-hole Plugin entwickelt werden.

Das Plugin soll über eine eigene API-Schicht mit Pi-hole kommunizieren.

## Pi-hole Dashboard

Beispiel:

```text
┌──────────────────────────────┐
│ 🛡 PI-HOLE                   │
├──────────────────────────────┤
│                              │
│ Blocked today                │
│ 12.482                       │
│                              │
│ Queries                      │
│ 48.231                       │
│                              │
│ Blocked                      │
│ 25,8 %                       │
│                              │
│ Status                       │
│ ● ONLINE                     │
└──────────────────────────────┘
```

## Pi-hole Widgets

### PiHoleStatsWidget

- Queries heute
- geblockte Queries
- Blockrate
- Status

### DNSQueryGraphWidget

Graph über:

- Queries pro Minute
- Blockrate
- zeitlicher Verlauf

### TopBlockedWidget

Zeigt:

- häufigste geblockte Domains
- optional Top Clients

### PiHoleControlWidget

Funktionen:

- Blocking aktivieren/deaktivieren
- Blocking temporär deaktivieren
- Dauer auswählen

Beispiel:

```text
Blocking deaktivieren

[ 5 Minuten ]
[ 30 Minuten ]
[ 1 Stunde ]
[ Dauerhaft ]
```

---

# 6. Netzwerk-Monitoring

HomePanel soll später ein einfaches Netzwerk-Dashboard besitzen.

Widgets:

### NetworkDeviceWidget

Zeigt bekannte Geräte:

```text
NETWORK DEVICES

● Desktop PC
  Online

● Raspberry Pi
  Online

● Smartphone
  Online

○ Laptop
  Offline
```

Mögliche Informationen:

- Name
- IP
- MAC optional
- Online Status
- Last Seen
- Ping
- Response Time

Die Geräteverwaltung soll später visuell erfolgen können.

---

# 7. Web Widget

Es soll ein universelles Web Widget geben.

Dieses Widget soll beliebige lokale oder externe Webseiten darstellen können.

Beispiel:

```text
┌──────────────────────────┐
│ 🌐 WEB PANEL             │
├──────────────────────────┤
│                          │
│                          │
│       WEBSITE            │
│                          │
│                          │
└──────────────────────────┘
```

Eigenschaften:

```text
URL

Refresh Interval

Zoom

Touch Input

Show Scrollbars

Allow Interaction

Reload on Page Open
```

Beispiele für die Nutzung:

- Pi-hole Webinterface
- Grafana
- Router
- Proxmox
- Portainer
- Node-RED
- andere lokale Webinterfaces

Das Web Widget muss optional sein, damit HomePanel nicht zwingend eine schwere Browser-Abhängigkeit benötigt.

---

# 8. Browser App

Neben dem Web Widget soll es langfristig eine richtige Browser-App geben.

Der Browser soll innerhalb von HomePanel laufen.

Navigation:

```text
[ ← ] [ → ] [ ⟳ ]

https://example.com

[ ⭐ ]
```

Funktionen:

- URL Eingabe
- Zurück
- Vor
- Reload
- Home
- Bookmarks
- Fullscreen
- Touch-optimierte Bedienung

Bookmarks:

```text
🏠 Home Assistant

🖨 Flashforge

🛡 Pi-hole

📊 Grafana

📡 Router
```

Der Browser muss als optionales Modul umgesetzt werden.

Wenn die Browser-Abhängigkeit nicht installiert ist, darf HomePanel nicht abstürzen.

---

# 9. Animation Engine

HomePanel soll ein einheitliches Animationssystem bekommen.

Die Animationen sollen nicht für jedes Widget einzeln neu implementiert werden.

Es soll eine zentrale Animation Engine geben.

Mögliche Animationen:

- Fade
- Slide
- Scale
- Pulse
- Bounce
- Shake
- Rotate
- Glow
- Breathing

Jedes Widget soll optional Animationen besitzen.

Beispiel:

```text
Animation

Entrance:
[ Fade In ▼ ]

State Change:
[ Pulse ▼ ]

Error:
[ Shake ▼ ]

Speed:
──────●──────
```

Die Animationen sollen performant sein und auf einem Raspberry Pi 5 flüssig laufen.

Keine unnötigen Daueranimationen erzeugen.

---

# 10. Conditional Styling

Das bestehende System für Conditional Visibility soll erweitert werden.

Aktuell kann ein Widget abhängig von einer Entity angezeigt oder versteckt werden.

Das neue System soll auch das Styling verändern können.

Beispiel:

```text
IF

sensor.printer_status

equals

printing


THEN

Change Background Color

Change Text Color

Change Icon

Start Animation

Show Notification
```

Weitere mögliche Bedingungen:

- equals
- not equals
- greater than
- less than
- contains
- online
- offline
- true
- false

Mehrere Regeln sollen später möglich sein.

Beispiel:

```text
IF temperature > 30
→ Hintergrund rot

IF temperature > 25
→ Hintergrund orange

ELSE
→ Hintergrund normal
```

Regeln sollen visuell bearbeitet werden können.

---

# 11. Custom Widget Builder

Es soll langfristig ein System geben, mit dem Benutzer eigene Widgets erstellen können.

Ohne Python.

Der Benutzer soll grafische Elemente kombinieren können:

- Text
- Icon
- Image
- Shape
- Sensor Value
- Progress Bar
- Graph
- Button
- Animation
- Container

Beispiel:

```text
┌─────────────────────┐
│ ☀                   │
│                     │
│ 23.4 °C             │
│ Wohnzimmer          │
└─────────────────────┘
```

Der Benutzer soll Elemente mit Daten verbinden können.

Beispiel:

```text
Text:

{{ state }}

Entity:

sensor.temperature_living_room
```

Später sollen einfache Expressions möglich sein:

```text
{{ state | round(1) }}

{{ state + " °C" }}
```

Das System muss sicher umgesetzt werden.

Keine unsichere direkte Ausführung von beliebigem Python-Code.

---

# 12. Screensaver System

Das bestehende Standby-System soll zu einem vollständigen Screensaver-System erweitert werden.

Es soll verschiedene Screensaver geben:

- Digitale Uhr
- Analoge Uhr
- Wetter
- Fotos
- Videos
- GIFs
- Animationen
- Systeminformationen
- Smart Home Informationen

Beispiel:

```text
SCREENSAVER

Mode:
[ Animated Clock ▼ ]

Background:
[ Space Animation ]

Widgets:

☑ Clock

☑ Weather

☑ CPU Temperature

☐ Calendar

Brightness:
────●──────
```

---

# 13. Medien und Animationen

HomePanel soll Medien als Hintergrund oder Widget verwenden können.

Unterstützung vorbereiten für:

- Bilder
- GIFs
- Videos
- Lottie Animationen
- lokale Medien

Mögliche Verwendung:

### Page Background

Ein Dashboard kann beispielsweise einen animierten Hintergrund haben.

### Widget Background

Ein Widget kann ein Bild oder eine Animation besitzen.

### Standby Animation

Beim Übergang in Standby kann eine Animation abgespielt werden.

Beispiel:

```text
NORMAL

↓ inactivity

FADE OUT

↓

SCREENSAVER

↓

DISPLAY OFF
```

Alle Übergänge sollen weich animiert werden.

---

# 14. System Dashboard

Das Raspberry Pi System soll vollständig überwacht werden können.

Eine eigene Systemseite:

```text
RASPBERRY PI 5

CPU
████████░░ 78 %

RAM
██████░░░░ 61 %

TEMPERATURE
███████░░░ 64 °C

STORAGE
█████░░░░░ 42 %

NETWORK

↓ 24 Mbit/s

↑ 8 Mbit/s
```

Widgets:

### CPUWidget

- CPU Auslastung
- CPU Frequenz
- Temperatur

### RAMWidget

- Used
- Available
- Percentage

### StorageWidget

- Used
- Free
- Percentage

### NetworkWidget

- Download
- Upload
- History

### SystemServiceWidget

Zeigt Systemdienste:

```text
● homepanel.service

● pihole.service

● docker.service

○ example.service
```

Optional:

- Service neu starten
- Service starten
- Service stoppen

Kritische Aktionen müssen bestätigt werden.

---

# 15. Docker Integration

Falls Docker auf dem Raspberry Pi verwendet wird, soll optional ein Docker Plugin existieren.

Anzeige:

```text
DOCKER

● homeassistant
  Running

● pihole
  Running

● grafana
  Running

○ test-container
  Stopped
```

Funktionen:

- Container Status
- Start
- Stop
- Restart
- CPU Usage
- RAM Usage

Diese Funktionen müssen optional bleiben.

---

# 16. App Launcher

HomePanel soll ein internes App-System bekommen.

Beispiel:

```text
APPS

🌐 Browser

🖨 Flashforge

🛡 Pi-hole

📊 System

📡 Network

🎵 Media
```

Apps sollen innerhalb der HomePanel-Oberfläche geöffnet werden.

Nicht:

```text
HomePanel beenden
→ externe App starten
```

Sondern:

```text
HomePanel

├── DashboardView
├── BrowserView
├── FlashforgeView
├── PiHoleView
├── SystemView
└── SettingsView
```

Die Navigation muss konsistent bleiben.

---

# 17. Workflow Builder

Langfristig soll ein einfacher grafischer Workflow Builder vorbereitet werden.

Beispiel:

```text
WHEN

[ Button Pressed ]

↓

THEN

[ Turn On Light ]

↓

WAIT

[ 5 Seconds ]

↓

THEN

[ Start Animation ]
```

Später visuell:

```text
[ BUTTON ]
     │
     ▼
[ LIGHT ON ]
     │
     ▼
[ WAIT ]
     │
     ▼
[ ANIMATION ]
```

Der erste Schritt kann zunächst eine einfache Listen-basierte Umsetzung sein.

Eine Node-basierte Oberfläche kann später folgen.

---

# 18. Theme und Customization massiv erweitern

HomePanel soll extrem stark anpassbar sein.

Der Benutzer soll visuell ändern können:

- Hintergrund
- Farben
- Gradients
- Transparenz
- Blur, falls performant möglich
- Border Radius
- Schatten
- Fonts
- Font Size
- Spacing
- Navigation Style
- Icons
- Hintergrundbilder
- Widget Styles
- Animationen

Zusätzlich sollen eigene Themes erstellt werden können.

Beispiel:

```text
THEME EDITOR

Name:
[ My Cyber Theme ]

Background:
[ #0A0A0A ]

Surface:
[ #141414 ]

Primary:
[ #00FF88 ]

Accent:
[ #00CFFF ]

Border Radius:
──────●──────

Export Theme

Import Theme
```

Themes sollen exportiert und importiert werden können.

---

# 19. Widget Templates

Es soll ein System für Widget Templates geben.

Beispiel:

Ein Nutzer erstellt ein perfektes Temperatur Widget.

Dann:

```text
Save as Template
```

Später:

```text
MY TEMPLATES

🌡 Temperature Modern

💡 Smart Light Card

🖨 Printer Status

📊 System Card
```

Beim Hinzufügen eines Templates können Entities neu zugewiesen werden.

---

# 20. Layout Presets

Der Benutzer soll komplette Seiten als Templates speichern können.

Beispiele:

```text
Dashboard Templates

🏠 Smart Home Overview

🖨 3D Printer Dashboard

📊 System Monitor

🛡 Network Security

🌦 Weather Dashboard
```

Templates sollen exportierbar und importierbar sein.

---

# 21. Backup und Restore erweitern

Das bestehende Backup-System soll erweitert werden.

Export:

```text
☑ Pages

☑ Widgets

☑ Themes

☑ Templates

☑ Plugin Settings

☐ Secrets
```

Import:

```text
[ Restore Full Backup ]

or

[ Import Theme ]

[ Import Widget Template ]

[ Import Dashboard ]
```

Secrets dürfen standardmäßig nicht exportiert werden.

---

# 22. Performance

Das Projekt läuft auf einem Raspberry Pi 5.

Deshalb ist Performance extrem wichtig.

Anforderungen:

- keine unnötigen Polling-Schleifen
- Caching verwenden
- Updates nur bei Änderungen durchführen
- WebSocket bevorzugen, wenn möglich
- langsame API Calls nicht im UI Thread ausführen
- Bilder skalieren und cachen
- Animationen begrenzen
- Browser und Medien optional halten
- Plugins lazy laden, wenn möglich

Widgets sollen nicht permanent neu aufgebaut werden.

`refresh_from_state()` soll nur das Nötigste aktualisieren.

---

# 23. Fehlerbehandlung

Keine neue Funktion darf das gesamte HomePanel zum Absturz bringen.

Besonders:

- Plugins
- Netzwerk APIs
- Flashforge
- Pi-hole
- Browser
- Docker

müssen Fehler sauber behandeln.

Beispiel:

```text
⚠ Flashforge Printer

Connection failed

[ Retry ]
```

Statt:

```text
Traceback...
Application crashed
```

Es soll ein zentrales Logging-System geben.

Optional:

```text
Settings

Developer

[ View Logs ]

[ Export Logs ]

[ Enable Debug Mode ]
```

---

# 24. Sicherheit

API Tokens und Passwörter dürfen:

- nicht geloggt werden
- nicht im Klartext exportiert werden
- nicht versehentlich in Debug-Ausgaben erscheinen

Wenn sensible Daten gespeichert werden, soll eine saubere Architektur vorbereitet werden.

---

# 25. Entwicklungsstrategie

Die Umsetzung soll schrittweise erfolgen.

Nicht versuchen, alle Features gleichzeitig zu implementieren.

## Phase 1 – Core Infrastructure

Zuerst implementieren:

1. Plugin Manager
2. Plugin API
3. Plugin Discovery
4. Plugin Settings
5. Error Isolation
6. zentrale Service/API Architektur

## Phase 2 – Customization

Danach:

1. Animation Engine
2. Conditional Styling
3. erweiterter Theme Editor
4. Widget Templates
5. Page Templates

## Phase 3 – Integrationen

Danach:

1. Flashforge Plugin
2. Pi-hole Plugin
3. System Monitoring
4. Network Monitoring

## Phase 4 – Web

Danach:

1. Web Widget
2. Browser App
3. Bookmarks
4. lokale Web Apps

## Phase 5 – Advanced Features

Zum Schluss:

1. Custom Widget Builder
2. Expression System
3. Workflow Builder
4. Docker Integration
5. App Launcher
6. Medien und erweiterte Screensaver

---

# 26. Wichtigste Designprinzipien

Bei jeder neuen Funktion gelten folgende Regeln:

## Keine komplizierten Config-Dateien

Der Benutzer soll nicht gezwungen werden:

```yaml
widget:
  color: red
  animation:
    enabled: true
```

zu schreiben.

Stattdessen:

```text
Widget auswählen

↓

Properties öffnen

↓

Farbe auswählen

↓

Animation auswählen
```

## Touch First

Alle neuen Funktionen müssen für einen kleinen Touchscreen geeignet sein.

Keine kleinen Desktop-Buttons.

Keine komplizierten Dialoge.

Keine überfüllten Menüs.

## Visuell konfigurierbar

Wenn etwas konfigurierbar ist, soll möglichst eine grafische Oberfläche existieren.

## Modular

Neue Hardware oder Dienste sollen später möglichst über Plugins integriert werden.

## Optional Dependencies

Große oder schwere Funktionen wie:

- Browser
- Video
- Docker
- Lottie

dürfen nicht die Grundinstallation unnötig belasten.

## Backwards Compatibility

Bestehende:

- Dashboards
- Widgets
- Themes
- Datenbanken
- Einstellungen

dürfen durch die Erweiterung nicht zerstört werden.

---

# 27. Gewünschtes Endergebnis

Das finale System soll ungefähr so funktionieren:

```text
                 HOMEPANEL

                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼

    SMART HOME     HARDWARE       SYSTEM
        │             │             │
        ▼             ▼             ▼

 Home Assistant   Flashforge      Raspberry Pi
 Automationen     Cameras         CPU / RAM
 Szenen           3D Printer      Storage

        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼

                 PLUGINS

                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼

     PI-HOLE        BROWSER       NETWORK
     SECURITY       WEB APPS      DEVICES

                      │
                      ▼

                CUSTOMIZATION

                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼

     THEMES       ANIMATIONS    CUSTOM WIDGETS
     LAYOUTS      RULES         TEMPLATES
```

HomePanel soll am Ende eine **modulare, visuelle und extrem anpassbare Touch-Oberfläche für Raspberry Pi** sein.

Es soll möglich sein, Home Assistant, lokale Dienste, Hardware, Webinterfaces, Systeminformationen und eigene Widgets auf einer gemeinsamen Oberfläche zu kombinieren.

Der Fokus liegt nicht darauf, möglichst viele Features unkontrolliert hinzuzufügen.

Der Fokus liegt auf:

- sauberer Architektur
- Modularität
- Erweiterbarkeit
- Performance auf Raspberry Pi 5
- visueller Anpassbarkeit
- Touch-Bedienung
- einfacher Bedienung ohne Code
- stabiler Fehlerbehandlung

## Wichtige Implementierungsregel

Bevor größere Änderungen durchgeführt werden:

1. Bestehende Architektur analysieren.
2. Wiederverwendbare Strukturen identifizieren.
3. Neue Komponenten möglichst modular hinzufügen.
4. Keine funktionierenden bestehenden Systeme unnötig ersetzen.
5. Nach jeder größeren Phase sicherstellen, dass das bestehende HomePanel weiterhin funktioniert.
6. Neue Features so implementieren, dass sie später über die GUI konfigurierbar sind.
7. Keine Platzhalter- oder Fake-Implementierungen erstellen, wenn eine reale Integration möglich ist.
8. APIs, Hintergrunddienste und UI sauber voneinander trennen.
9. Keine blockierenden Netzwerkoperationen im Qt UI Thread ausführen.
10. Bestehende Code-Struktur und Coding-Stil beibehalten.

Das Ziel ist keine einfache Sammlung von Widgets.

Das Ziel ist ein langfristig erweiterbares System:

> **HomePanel wird zu einer modularen Touch-Plattform für Smart Home, Hardware, lokale Dienste, System-Monitoring und individuelle Benutzeroberflächen.**

Beginne mit einer Analyse der bestehenden Projektstruktur und erstelle anschließend einen konkreten Implementierungsplan für Phase 1. Danach implementiere die Änderungen schrittweise und prüfe nach jedem größeren Schritt, ob bestehende Funktionen weiterhin funktionieren.