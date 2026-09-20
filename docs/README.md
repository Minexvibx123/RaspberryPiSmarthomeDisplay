# HomePanel – Dokumentation

Übersicht über die gesamte Projektdokumentation. Zielgruppe sind Entwickler,
die HomePanel erweitern oder verstehen wollen, sowie Betreiber, die das Panel
installieren und pflegen.

- **[Architektur](architecture.md)** – Systemübersicht, Startablauf, Datenfluss,
  Schichten (Core / UI / Widgets / Plugins).
- **[Core-Layer](core.md)** – Referenz des Backends: Home-Assistant-REST- und
  WebSocket-Client, SQLite-Datenbank, State-Manager, Settings, Animationen,
  Bedingungen, Expression-Engine, Workflows, HTTP-Fetch.
- **[UI-Layer](ui.md)** – Referenz der Oberfläche: Hauptfenster, Dashboard-Canvas,
  Editor, Eigenschaftenpanel, Element-Bibliothek, Navigation, Themes,
  Einrichtungsassistent, Einstellungen, App-Launcher, Custom-Widget-Builder.
- **[Widget-System & Widget-Referenz](widgets.md)** – `BaseWidget`,
  `PropertyDef`/`COMMON_SCHEMA`, Registry und Beschreibung aller
  eingebauten Widget-Typen.
- **[Plugin-Entwicklung](plugin-development.md)** – Schritt-für-Schritt-Anleitung
  zum Bau eigener Plugins (manifest.json, Lifecycle, Widgets, Einstellungen,
  Apps).
- **[Plugin-Katalog](plugins/README.md)** – Die mitgelieferten Plugins im
  Überblick (System-Monitor, Flashforge, Pi-hole, Netzwerk, Docker, Browser).
- **[Deployment](deployment.md)** – Installation auf dem Raspberry Pi, systemd,
  Kiosk (cage), Rotation, Update-Strategie.
- **[Skripte](scripts.md)** – Alle Skripte unter `scripts/` (Installation,
  GitHub-Deployment, Diagnose, Verifikation) inkl. Verwendung.
- **[Feature-Ausbau & Architektur-Plan](HomePanel%20%E2%80%93%20Major%20Feature%20Expansion%20%26%20Architecture%20Upgrade.md)**
  – Historische Planungs-/Ausbauvorlage (Phasen 1–5), Grundlage der Umsetzung.

## Weitere Wissensbasis

- [`AI-CONTEXT.md`](../AI-CONTEXT.md) – Technische Referenz für KI-Assistenten
  (sehr detailliert, enthält auch Datenbankschema und Settings-Liste).
- [`SETUP-STATUS.md`](../SETUP-STATUS.md) – Hardware-Troubleshooting-Playbook
  für das Raspberry-Pi-5/DSI2-cage-Setup.
- [`README.md`](../README.md) – Benutzerorientierte Projektübersicht (Deutsch).

## Kurzübersicht der Verzeichnisse

| Pfad | Inhalt |
|---|---|
| `app/main.py` | Einstiegspunkt (`python -m app.main [--windowed] [--demo]`) |
| `app/core/` | Backend: Datenbank, HA-Clients, State-Manager, Engines |
| `app/ui/` | Oberfläche: Fenster, Editor, Einstellungen, Themes |
| `app/widgets/` | Eingebaute Widget-Klassen + Registry |
| `app/plugins/` | Plugin-Kern (API, Discovery, Manager) |
| `plugins/` | Echte Plugin-Integrationen (7 Stück) |
| `scripts/` | Installs-, Update-, Diagnose- und Verifikationsskripte |
| `systemd/` | systemd-Unit für den Kiosk-Autostart |
| `data/` | Laufzeitdaten (SQLite: `homepanel.db`), wird nicht versioniert |