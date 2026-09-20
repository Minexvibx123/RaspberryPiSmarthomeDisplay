# Plugin: network

Erreichbarkeits-Monitoring für lokale Geräte per `ping`.

## Funktionen

- Ein Widget pro zu prüfendem Gerät (`network_device`).
- Zeigt **Online/Offline**-Status und Antwortzeit (ms).
- Eigenschaft `host` (IP oder Hostname) pro Widget einstellbar.

## Widgets

| type_name | Anzeigename | Beschreibung |
|---|---|---|
| `network_device` | Netzwerkgerät | Ping-Status + Antwortzeit |

## API

`plugins/network/api.py` – `NetworkMonitor.probe(host)`:

```python
{"host": host, "online": bool, "response_ms": float | None}
```

- `ping -c 1 -W 2 <host>` mit hartem Timeout (3 s).
- Fehlende Antwort → `online=False`, `response_ms=None`.

## Threading

Der Ping läuft in einem `QThread` (`_Probe`); der UI-Thread wird nie
blockiert. Jede `refresh_from_state()`-Aktualisierung stößt einen neuen
Probe an.