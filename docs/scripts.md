# Skripte (`scripts/`)

Alle Hilfsskripte für Installation, Deployment, Diagnose und Verifikation.

## Installation & Update

| Skript | Zweck |
|---|---|
| `install.sh` | Einmalige Installation auf dem Raspberry Pi: Systempakete, `video`-Gruppe, `.venv`, systemd-Dienst, Backlight-udev-Regel, Start. |
| `install-github.sh` | Frische Installation direkt aus GitHub: klont das Repository und ruft `install.sh` auf. Optionale Env: `HOMEPANEL_DIR`, `HOMEPANEL_BRANCH`, `HOMEPANEL_REPOSITORY`. |
| `update-github.sh` | Safe Update eines bestehenden Checkouts: bricht bei lokalen Änderungen ab, nur Fast-Forward, aktualisiert Abhängigkeiten, startet den Service neu. |
| `configure_ha.py` | Home-Assistant-Konfiguration ohne Touchscreen (headless per SSH). `--url --token`, `--demo`, `--no-demo`, `--show` (maskiert), `--skip-test`. |
| `kiosk-start.sh` | Manueller Kiosk-Start (xcb, xset screensaver aus). Zum Testen ohne systemd. |
| `sync-pi.sh` | Synchronisiert Code auf den Pi (rsync). Geschützt: `.venv/`, `data/`, `.git/`, `thoughts/`. Argument: Ziel-User@IP. |

## Diagnose

| Skript | Zweck |
|---|---|
| `diagnose-pi.sh` | Sammelt gebündelt alle Diagnoseinfos (System, Gruppen, Service-Datei, systemctl, Logs, venv-Python) – auf dem Pi ausführen. |

## Verifikation (Regressionstests, headless)

Alle `verify_*.py`-Skripte laufen ohne Display/GUI und prüfen einzelne
Bestandteile. Ausführen nach jeder Änderung am betroffenen Bereich:

```bash
.venv/bin/python scripts/verify_conditions.py
```

| Skript | Prüft |
|---|---|
| `verify_plugin_boot.py` | Dass alle mitgelieferten Plugins sauber laden (Lifecycle end-to-end). |
| `verify_plugin_error_isolation.py` | Dass ein absichtlich kaputtes Plugin isolierte Fehler erzeugt und die App nicht abstürzt. |
| `verify_conditions.py` | Operator-Auswertung (`matches_condition`). |
| `verify_animations.py` | Animation-Engine (Namen/Viabilität). |
| `verify_templates.py` | Savable Vorlagen in der Datenbank. |
| `verify_expressions.py` | Expression-Engine inkl. Abwehrung unsicherer Ausdrücke. |
| `verify_workflows.py` | Workflow-Engine und Speicherung. |
| `verify_backup.py` | Backup/Export/Import – inkl. Geheimnis-Ausschluss. |
| `verify_custom_widget.py` | Custom-Widget-Rendering und Builder-Persistenzpfad. |
| `verify_screensaver.py` | Screensaver-Modi + Hintergrundbild-Einstellung. |
| `verify_docker.py` | Docker-Plugin-API-Wrapper. |
| `verify_system_monitor.py` | System-Monitor-API (Metriken aus /proc, /sys). |
| `verify_web_widget.py` | Web-Widget-Logik inkl. Fallback ohne QtWebEngine. |

Hinweis: `verify_*.py` besitzen keine Abhängigkeit vom Hardware-/Display-Setup
und können auch auf dem Entwicklungsrechner laufen.