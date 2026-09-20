# Plugin: docker

Verwaltung lokaler Docker-Container über die `docker`-CLI (lokaler Socket).

## Funktionen

- Container-Liste mit Status (`docker ps -a --format "{{json .}}"`).
- **Start / Stop / Neustart** je Container (`docker start|stop|restart`).
- Statistik (`docker stats --no-stream`) über `DockerClient.stats()`.
- Stop/Neustart verlangen eine Bestätigung (`QMessageBox`).

## Widgets

| type_name | Anzeigename | Beschreibung |
|---|---|---|
| `docker_containers` | Docker | Container-Liste + Aktions-Buttons |

## API

`plugins/docker/api.py` – `DockerClient`:

- `containers()` → Liste von Dicts (JSON-Zeilen aus `docker ps`).
- `stats(container)` → Dict (aus `docker stats --no-stream`).
- `start(container)`, `stop(container)`, `restart(container)`.

Alle Aufrufe laufen mit Timeout (5–30 s); Fehler werden als Ausnahme an den
QThread-Aufrufer gemeldet, der die Widgets auf keinen Fall blockiert.

## Voraussetzungen

- `docker`-CLI installiert und für den HomePanel-Benutzer ausführbar
  (z. B. Mitglied der Gruppe `docker` oder passende `sudo`-Regel).