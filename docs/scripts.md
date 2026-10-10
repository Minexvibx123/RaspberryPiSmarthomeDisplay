# Skripte (`scripts/`)

Alle Hilfsskripte für Installation, Deployment, Diagnose und Verifikation.

## Installation & Update

| Skript | Zweck |
|---|---|
| `install.sh` | Einmalige Installation auf dem Raspberry Pi: Systempakete, `video`-Gruppe, `.venv`, systemd-Dienst, Backlight-udev-Regel, Start. |
| `install-github.sh` | Frische Installation direkt aus GitHub: klont das Repository und ruft `install.sh` auf. Optionale Env: `HOMEPANEL_DIR`, `HOMEPANEL_BRANCH`, `HOMEPANEL_REPOSITORY`. |
| `update-github.sh` | Safe Update eines bestehenden Checkouts: bricht bei lokalen Änderungen ab, nur Fast-Forward, aktualisiert Abhängigkeiten, startet den Service neu. |
| `build-cage.sh` | Baut cage 0.3.1 mit dem Touch-Output-Mapping-Patch und installiert das Binary als `/usr/local/bin/cage`; Paketinstallation und Installationsschritt benötigen Root-Rechte. |
| `fix-kiosk.sh` | Richtet nach Installation des gepatchten cage die alternative Pi-5-Kiosk-Sitzung ein: tty1-Autologin, `kiosk-session.sh` und `homepanel-vnc.service`; deaktiviert dabei `homepanel.service`. Vorher Änderungen an Login- und systemd-Konfiguration prüfen. |
| `configure_ha.py` | Home-Assistant-Konfiguration ohne Touchscreen (headless per SSH). `--url --token`, `--demo`, `--no-demo`, `--show` (maskiert), `--skip-test`. |
| `kiosk-start.sh` | Manueller Kiosk-Start (xcb, xset screensaver aus). Zum Testen ohne systemd. |
| `kiosk-session.sh` | Startet cage aus der tty1-Login-Sitzung, setzt die 270°-Rotation, initialisiert den DSI-Ausgang nach einem Compositor-Neustart neu und startet cage bei Ende erneut. |
| `homepanel-vnc.sh` | Startet eine zweite HomePanel-Instanz auf Xvfb und stellt sie über x11vnc/noVNC auf Port `6080` bereit; verwendet `systemd/homepanel-vnc.service`. |
| `ensure-touch.sh` | Versucht bis zu 60 Sekunden, den Goodix-Touchscreen zu erkennen bzw. den I²C-Treiber neu zu binden. Für das Treiber-Rebind sind Root-Rechte nötig. |
| `sync-pi.sh` | Synchronisiert Code auf den Pi (rsync). Geschützt: `.venv/`, `data/`, `.git/`, `thoughts/`. Argument: Ziel-User@IP. |

`fix-kiosk.sh` wechselt vom direkten `homepanel.service`-Start zur tty1-
Autologin-Sitzung. Ein Neustart ist nach der Einrichtung erforderlich. Die
noVNC-Ansicht läuft ohne eigene Passwortabfrage; nur in einem vertrauenswürdigen
LAN betreiben und Port `6080` per Firewall auf berechtigte Clients begrenzen.
`systemd/homepanel-touch.service` ist eine separate oneshot-Unit für
`ensure-touch.sh`; sie wird nicht durch `fix-kiosk.sh` aktiviert.

## Diagnose

| Skript | Zweck |
|---|---|
| `diagnose-pi.sh` | Sammelt gebündelt alle Diagnoseinfos (System, Gruppen, Service-Datei, systemctl, Logs, venv-Python) – auf dem Pi ausführen. |

## Verifikation (Regressionstests, headless)

Alle `verify_*.py`-Skripte in `scripts/verify/` laufen ohne Display/GUI und
prüfen einzelne Bestandteile. Ausführen nach jeder Änderung am betroffenen
Bereich:

```bash
.venv/bin/python scripts/verify/verify_conditions.py
```

| Skript | Prüft |
|---|---|
| `verify_plugin_boot.py` | Dass alle mitgelieferten Plugins sauber laden (Lifecycle end-to-end). |
| `verify_plugin_error_isolation.py` | Dass ein absichtlich kaputtes Plugin isolierte Fehler erzeugt und die App nicht abstürzt. |
| `verify_conditions.py` | Operator-Auswertung (`matches_condition`). |
| `verify_animations.py` | Animation-Engine (Namen/Viabilität). |
| `verify_templates.py` | Speichern und Laden von Widget- und Service-Aktionsvorlagen in der Datenbank. |
| `verify_expressions.py` | Expression-Engine inkl. Abwehrung unsicherer Ausdrücke. |
| `verify_workflows.py` | Workflow-Engine, Service-Aktionen und Speicherung. |
| `verify_workflow_ui.py` | Offscreen-Erstellung, Anzeige und Aktivierungswechsel in der Workflow-Verwaltung. |
| `verify_swipe_navigation.py` | Dashboard-Seitenwechsel per horizontalem Wisch, Seitengrenzen und Editor-Sperre. |
| `verify_app_store.py` | Lokaler Store-Katalog, Installieren/Entfernen und Erzeugung der gebündelten App-Views. |
| `verify_backup.py` | Backup/Export/Import – inkl. Geheimnis-Ausschluss und Roundtrip. |
| `verify_custom_widget.py` | Custom-Widget-Rendering und Builder-Persistenzpfad. |
| `verify_screensaver.py` | Screensaver-Modi + Hintergrundbild-Einstellung. |
| `verify_docker.py` | Docker-Plugin-API-Wrapper. |
| `verify_system_monitor.py` | System-Monitor-API (Metriken aus /proc, /sys). |
| `verify_network.py` | Sichere private CIDR-Grenzen, lokale Netzerkennung und Discovery-Ergebnisse ohne echte Netzwerkanfragen. |
| `verify_web_widget.py` | Web-Widget-Logik inkl. Fallback ohne QtWebEngine. |

Die Liste oben umfasst die derzeit versionierten `verify_*.py`-Skripte. Die
Skripte laufen einzeln; für einen vollständigen Lauf:

```bash
for test in scripts/verify/verify_*.py; do .venv/bin/python "$test" || exit 1; done
```

Hinweis: `scripts/verify/*.py` benötigen kein Hardware-/Display-Setup.
`verify_docker.py` setzt zusätzlich ein installiertes Docker-CLI und einen
erreichbaren Docker-Daemon voraus; die übrigen Tests können unabhängig davon
auf dem Entwicklungsrechner laufen.