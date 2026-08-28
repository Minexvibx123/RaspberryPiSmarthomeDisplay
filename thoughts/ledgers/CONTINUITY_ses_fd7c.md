---
session: ses_fd7c
updated: 2026-08-22T07:57:57.002Z
---

# Sitzungszusammenfassung

## Ziel
Browser-Widget + QtWebEngine aus HomePanel entfernen ✅; Projekt auf den Pi übertragen ✅; schwarzes DSI-Display (offizielles 7" Touch Display 2) reparieren – es fehlt `dtoverlay=vc4-kms-dsi-7inch` in der config.txt.

## Einschränkungen & Präferenzen
- Auf Deutsch antworten; bestehende Skripte nutzen (`sync-pi.sh`, `install.sh`) – User-Zitat: „das macht das install script"
- SSH `supervisor@192.168.178.138`, Passwort `0908`; sudo nur via `ssh -t` (Prompts per pty_write mit `0908` beantworten) oder `echo 0908 | sudo -S <cmd>` **auf dem Pi**
- **Lektion (pty_635bfde7-Fehler)**: Pipes in unquoted ssh-args wurden LOKAL geparst → Remote-Befehl degenerierte zu `echo 0908`. Remote-Befehl immer als EIN quoted Argument senden
- Kein WAYLAND_DISPLAY vor cage setzen; Rotation via `wlr-randr --output DSI-2 --transform 90`

## Fortschritt
### Erledigt
- [x] Browser/QtWebEngine entfernt: `app/widgets/browser.py` gelöscht; registry.py bereinigt (40 Widgets); install.sh ohne libqt6webengine*; diagnose-pi.sh WebEngine-Sektion ersetzt; sync-pi.sh-Kommentare; README 41→40. Verifiziert (grep 0 Treffer, Importtests OK)
- [x] Host-Key gefixt (`ssh-keygen -R 192.168.178.138`); rsync ~9,9 MB → `/home/supervisor/homepanel`
- [x] `sudo ./scripts/install.sh`: apt deps, PySide6 6.11.2, systemd aktiviert, udev backlight rule; Neustart
- [x] cage + wlr-randr nachinstalliert (`ssh -t ... sudo apt-get install -y cage wlr-randr`); Service **aktiv**
- [x] Diagnose schwarz: KEIN DSI-Konnektor in `/sys/class/drm/`, kein Backlight, journalctl „unknown output DSI-2"; config.txt OHNE Panel-Overlay
- [x] Display identifiziert (SETUP-STATUS.md): offizielles Pi 7" Touch Display 2, DSI2, 720x1280 Hochformat-nativ

### In Bearbeitung
- [ ] **Overlay NICHT bestätigt**: pty_635bfde7 end
