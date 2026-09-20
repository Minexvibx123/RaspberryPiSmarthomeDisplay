# Plugin: system_monitor

Raspberry-Pi-Systemmonitoring ohne externe Abhängigkeiten – liest direkt aus
`/proc`, `/sys` und `os.statvfs`.

## Funktionen

- **CPU** in Prozent (aus `/proc/stat`, Differenzmessung)
- **RAM** in Prozent + belegt/gesamt (aus `/proc/meminfo`)
- **Speicher** in Prozent + belegt/gesamt (aus `os.statvfs("/")`)
- **Netzwerk** Down/Up in Bytes/s (aus `/proc/net/dev`, Differenzmessung)
- **Temperatur** in °C (aus `/sys/class/thermal/thermal_zone*`)
- **Systemdienste** (`system_services`): Status + Start/Stop/Neustart über
  `sudo -n systemctl` (mit Bestätigung)

## Widgets

| type_name | Anzeigename | Beschreibung |
|---|---|---|
| `system_cpu` | CPU | Auslastung + Temperatur |
| `system_ram` | RAM | Auslastung + belegt/gesamt |
| `system_storage` | Speicher | Auslastung + belegt/gesamt |
| `system_network` | Netzwerk | Down/Up-Raten |
| `system_services` | Systemdienste | Liste + Aktionen (Property `service_names`, Komma-getrennt) |

CPU/RAM/Speicher/Netzwerk aktualisieren sich alle 2 s, Dienste alle 5 s.

## API

`plugins/system_monitor/api.py` – `SystemMetrics.snapshot()` liefert ein Dict
`{cpu_percent, memory_percent, memory_used, memory_total, storage_percent,
storage_used, storage_total, temperature, download_rate, upload_rate}` sowie
das Modul-Singleton `metrics`.

## Voraussetzungen

- Linux mit `/proc` + `/sys` (Raspberry Pi OS).
- Für Dienst-Aktionen: `sudo -n` (passwordless sudo) für `systemctl`.