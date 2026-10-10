# Plugin-Katalog

Übersicht aller mitgelieferten Plugins unter `plugins/`. Details zu jedem
Plugin in dessen eigenem `README.md`.

| Plugin | Kategorie | Funktion | Widgets / Apps |
|---|---|---|---|
| [System Monitoring](../../plugins/system_monitor/README.md) | system | CPU/RAM/Speicher/Netzwerk/Temperatur + systemd-Dienste | `system_cpu`, `system_ram`, `system_storage`, `system_network`, `system_services` |
| [Flashforge](../../plugins/flashforge/README.md) | hardware | 3D-Drucker-Steuerung (TCP 8899) + Kamera | `printer_status`, `printer_control`, `printer_jog`, `flashforge_camera` |
| [Pi-hole](../../plugins/pihole/README.md) | network | Statistik + zeitlich begrenztes Blocking (v6-API) | `pihole_stats`, `pihole_control` |
| [Netzwerk](../../plugins/network/README.md) | network | Geräte-Erreichbarkeit + manuelle Erkennung im privaten LAN | `network_device`, `network_inventory` |
| [Docker](../../plugins/docker/README.md) | system | Lokale Container (Start/Stop/Neustart) | `docker_containers` |
| [Browser](../../plugins/browser/README.md) | apps | Interner Touch-Browser (optional QtWebEngine) | App-View im Launcher |
| Energie | apps | HA-Energiedashboard als Vollbild-App | `energy_app` |
| Medien | apps | Touch-Steuerung für HA-Mediaplayer | `media_center` |
| Geräte | apps | Durchsuchbare HA-Entity-Übersicht | `device_center` |
| [App-Store](../ui.md) | apps | Lokaler Katalog, Installieren/Deaktivieren gebündelter App-Plugins | `AppStore` |
| [Beispiel](../../plugins/example_plugin/README.md) | general | Lifecycle-Demonstration (Referenz) | – |

## Gemeinsame Konventionen

- **API-Clients in `api.py`**, thread-frei und defensiv (Fehler werden als
  Dict/Wert zurückgemeldet, nie geworfen).
- **Widgets** starten ihre I/O in `QThread`s und liefern über Qt-Signals – der
  UI-Thread wird nie blockiert.
- **Einstellungen** über `settings_schema` im Plugins-Tab; Speicherung als
  `plugin.<id>.*` in SQLite.
- **Sichere Aktionen** (Stop/Neustart, Cancel) verlangen eine
  Bestätigung (`QMessageBox`).
- **Repo-Apps**: Ein GitHub-Repository mit `manifest.json` + `plugin.py` im
  Wurzelverzeichnis (oder `plugins/<id>/`) lässt sich im App-Store per URL
  installieren. Es wird deaktiviert abgelegt und erst nach Bestätigung aktiviert.

## Erstellen neuer Plugins

Siehe [Plugin-Entwicklung](../plugin-development.md).