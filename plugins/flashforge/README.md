# Plugin: flashforge

Integration für Flashforge-3D-Drucker (z. B. Adventurer 5M Pro) über das
dokumentierte TCP-Protokoll (Port `8899`).

## Funktionen

- **Printer Status** – Maschinenstatus, Fortschritt, Düsen- und Betttemperatur
  (G-Code `M119`, `M27`, `M105`).
- **Print Control** – Pause (`M25`), Fortsetzen (`M24`), Abbrechen (`M26`,
  mit Bestätigung).
- **Print Jog** – Achsensteuerung (relative Bewegung `G91`/`G1`, Home `G28`).
- **Drucker-Kamera** – MJPEG-Livestream (Standard: Port `8080`,
  Pfad `/?action=stream`). Der Stream wird nur gestartet, solange das Widget
  sichtbar ist (`showEvent`/`hideEvent`) und bei Widget-Löschung sauber
  beendet.

## Widgets

| type_name | Anzeigename | Beschreibung |
|---|---|---|
| `printer_status` | Drucker-Status | Live-Status-Temperatur/Fortschritt |
| `printer_control` | Drucker-Steuerung | Pause/Fortsetzen/Abbrechen |
| `printer_jog` | Drucker-Jog | Achsen-Bewegung + Home |
| `flashforge_camera` | Drucker-Kamera | MJPEG-Livestream (Properties: `host`, `stream_port`, `stream_path`) |

## API

`plugins/flashforge/api.py` – dokumentierter Roh-TCP-Client:

- `command(command)` – einzelner G-Code.
- `move(dx, dy, dz, feed_rate)` – relative Achsbewegung.
- `home()` – `G28`.
- `status()` – Dict mit `status`, `progress`, `nozzle`, `bed`.
- `pause()/resume()/cancel()`.

Kontext-Handshake pro Batch: `~M601 S1` (Control übernehmen) … `~M602`
(Control freigeben). Alle Kommandos nutzen `~`-Präfix und werden auf
`\r\n` terminiert; Antworten werden bis `ok` gelesen.

## Einstellungen

Plugins-Tab: `host` (Drucker-IP), `port` (TCP-Steuerport, Standard `8899`).

## Fehlertoleranz

- Kein erreichbarer Drucker → Widgets zeigen einen Fehlerhinweis, die App
  bleibt stabil.
- Kamera: Lese-Thread meldet `offline`, wenn der Stream nicht erreichbar ist,
  und versucht es nach 2 s erneut.