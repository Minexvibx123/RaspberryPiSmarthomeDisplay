# Plugin: network

Erreichbarkeits-Monitoring für lokale Geräte per `ping`.

## Funktionen

- Ein Widget pro zu prüfendem Gerät (`network_device`).
- Zeigt **Online/Offline**-Status und Antwortzeit (ms).
- Eigenschaft `host` (IP oder Hostname) pro Widget einstellbar.
- `network_inventory` sucht auf Knopfdruck aktive Hosts in einem privaten
	IPv4-Netz und zeigt Router-Namen, sofern Reverse-DNS sie liefert.
- Der Scan ist auf höchstens 256 Adressen (maximal `/24`) beschränkt, sendet
	je Host einen Ping und prüft keine Ports. Ohne CIDR nutzt er das private
	IPv4-Netz der Standardroute; alternativ kann ein CIDR in den
	Widget-Eigenschaften eingetragen werden.

## Widgets

| type_name | Anzeigename | Beschreibung |
|---|---|---|
| `network_device` | Netzwerkgerät | Ping-Status + Antwortzeit |
| `network_inventory` | Netzwerk-Inventar | Manuelle Host-Erkennung im privaten IPv4-LAN |

## API

`plugins/network/api.py` – `NetworkMonitor.probe(host)` und
`NetworkMonitor.discover(cidr=None)`:

```python
{"host": host, "online": bool, "response_ms": float | None}
```

- `ping -c 1 -W 2 <host>` mit hartem Timeout (3 s).
- Fehlende Antwort → `online=False`, `response_ms=None`.
- Die Inventarsuche gibt nur antwortende Hosts mit IP, optionalem Reverse-DNS-
	Namen und Antwortzeit zurück. Schlafende oder nicht antwortende Geräte
	erscheinen nicht; der Scan ersetzt keine Router-/HA-Geräteverwaltung.

## Threading

Einzel-Pings und Inventarscans laufen in `QThread`s; der UI-Thread wird nie
blockiert. Einzelgeräte werden beim Refresh geprüft, ein Inventarscan startet
nur nach einer Touch-Betätigung.