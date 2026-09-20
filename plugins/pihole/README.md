# Plugin: pihole

Integration der **Pi-hole v6 REST-API** (`/api/…`): Statistiken und zeitlich
begrenztes Deaktivieren der Blockierung.

## Funktionen

- **Statistik** (`pihole_stats`) – Queries, geblockte DNS-Anfragen, Block-Rate
  (`/api/stats/summary`).
- **Steuerung** (`pihole_control`) – Blocking für 5/30/60 Minuten oder
  dauerhaft deaktivieren, Blocking wieder aktivieren (`/api/dns/blocking`).

## Widgets

| type_name | Anzeigename | Beschreibung |
|---|---|---|
| `pihole_stats` | Pi-hole | Online-Status + Statistiken |
| `pihole_control` | Pi-hole Steuerung | Blocking-Buttons + Status |

## API

`plugins/pihole/api.py` – `PiHoleClient(base_url, sid)`:

- `stats()` → `/api/stats/summary`
- `blocking()` → `/api/dns/blocking`
- `set_blocking(enabled, timer=None)` → POST `/api/dns/blocking`

Sitzung via `sid`-Header (optional, leeres `sid` = öffentliche Instanz).

## Einstellungen

Plugins-Tab: `url` (Pi-hole-Adresse, z. B. `http://pi.hole`), `sid`
(API-Sitzung). Die `sid` ist ein Geheimnis und wird beim Konfigurations-Export
automatisch ausgeschlossen.

## Hinweis

Widgets binden URL/SID aus der **Widget-Config**
(`pihole_url`/`pihole_sid`-Properties) – beim Einfügen auf einer Seite werden
die Plugin-Einstellungen übernommen. Für Nutzung ohne sichtbare Widgets genügt
die Konfiguration im Plugins-Tab.