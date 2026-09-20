# Deployment & systemd

HomePanel läuft als Kiosk-Anwendung auf einem Raspberry Pi 5 mit 7"-Touch
Display 2 (DSI2, portrait-native 720x1280). Dieses Dokument beschreibt, wie das
Panel installiert, gestartet, gedreht und aktualisiert wird.

## 1. Installation

### Lokal (Manuell, Entwicklung)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main --windowed        # Fenster statt Fullscreen
python -m app.main --windowed --demo # Demo-Modus (kein Home Assistant nötig)
```

Beim ersten Start öffnet sich der Einrichtungsassistent (Sprache,
HA-Adresse + Long-Lived-Token oder Demo-Modus).

### Auf dem Raspberry Pi

```bash
./scripts/install.sh
```

Das Skript:
1. Installiert alle **Systempakete**: den Wayland-Kiosk-Stack (`cage`,
   `wlr-randr`, `xwayland`), die Qt/PySide6-Laufzeitbibliotheken (`libgl1`,
   `libegl1`, `libglib2.0-0[t64]`, `libxcb-*`, `libxkbcommon*`,
   `libwayland-*`, `libfontconfig1`, …) sowie `python3-venv/python3-pip`
   (und verifiziert danach, dass `cage` und `wlr-randr` verfügbar sind).
   Hinweis: `libglib2.0-0t64` wird auf älteren Systemen (Bookworm)
   automatisch durch `libglib2.0-0` ersetzt.
2. Stellt sicher, dass der Benutzer in der Gruppe `video` ist (Backlight/DRM).
3. Legt `.venv` an und installiert die Python-Abhängigkeiten.
4. Kopiert und patcht `systemd/homepanel.service`
   (`/home/pi/homepanel` → echter Pfad, `User=pi` → aktueller Benutzer).
5. Installiert eine udev-Regel für Backlight-Schreibzugriff
   (`/etc/udev/rules.d/99-homepanel-backlight.rules`, Gruppe `video`).
6. Aktiviert und startet den Dienst `homepanel.service`.

Danach optional Neuanmeldung, damit die `video`-Gruppe greift.

### Frisch aus GitHub (empfohlen für neue Geräte)

```bash
curl -fsSL https://raw.githubusercontent.com/Minexvibx123/RaspberryPiSmarthomeDisplay/main/scripts/install-github.sh | bash
```

- Klont nach `~/homepanel` und ruft `install.sh` auf.
- Überschreibbar per Umgebungsvariablen:
  `HOMEPANEL_DIR`, `HOMEPANEL_BRANCH`, `HOMEPANEL_REPOSITORY`.

## 2. systemd-Dienst

Vorlage: `systemd/homepanel.service`

```ini
[Unit]
Description=HomePanel - Home Assistant Touchpanel
After=network-online.target systemd-user-sessions.service getty@tty1.service
Conflicts=getty@tty1.service
Wants=network-online.target

[Service]
Type=simple
User=pi                      # wird von install.sh gepatcht
PAMName=login
Environment=QT_QPA_PLATFORM=wayland
Environment=PYTHONUNBUFFERED=1
ExecStartPost=/bin/sh -c 'i=0; until wlr-randr --output DSI-2 --transform normal || [ $i -ge 20 ]; do i=$((i+1)); sleep 0.5; done'
WorkingDirectory=/home/pi/homepanel
ExecStart=/usr/bin/cage -d -- /home/pi/homepanel/.venv/bin/python -m app.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Wichtige Punkte:

- **`cage -d`** ist ein minimaler Wayland-Kiosk-Compositor. Er ist nötig,
  weil auf dem Pi 5 das DSI-Panel an einem eigenen DRM-Device
  (`drm-rp1-dsi`) hängt: Qt-`eglfs` würde dort abstrürzen (SIGABRT),
  `linuxfb` kann nicht rotieren. `cage` bringt GPU-Beschleunigung (v3d),
  Output-Rotation und mitgedrehte Touch-Koordinaten (wlroots/libinput).
- **`QT_QPA_PLATFORM=wayland`** – Qt nutzt den Wayland-Backend.
- **`WAYLAND_DISPLAY` darf nicht vorab gesetzt sein** – cage exportiert es
  selbst für die Clients.
- **Rotation** über `ExecStartPost` mit `wlr-randr --output DSI-2
  --transform normal|90|180|270` (bis zu 20 Versuche, 0,5 s Abstand).
- `Restart=always` + `RestartSec=3` für Crash-Recovery.
- Der Enwurf verwendet `PAMName=login` für die Kiosk-Sitzung.

## 3. Deploy-Codeänderungen

```bash
./scripts/sync-pi.sh                    # Ziel: supervisor@192.168.178.138
./scripts/sync-pi.sh user@andere-ip     # anderes Ziel
```

Geschützt: `.venv/`, `data/` (SQLite), `.git/`, `thoughts/`.
Danach auf dem Pi: Abhängigkeiten installieren und Dienst neu starten.

Manuell (systemd-Unit aktualisieren):

```bash
scp systemd/homepanel.service supervisor@192.168.178.138:/tmp/
ssh supervisor@192.168.178.138 'echo 0908 | sudo -S sh -c \
  "sed \"s#/home/pi/homepanel#/home/supervisor/homepanel#g; s#User=pi#User=supervisor#g\" /tmp/homepanel.service > /etc/systemd/system/homepanel.service && systemctl daemon-reload && systemctl restart homepanel.service"'
```

## 4. Updates

```bash
~/homepanel/scripts/update-github.sh
```

- Bricht ab, wenn lokale Codeänderungen vorliegen (diese bleiben geschützt).
- Nur Git-Fast-Forward; aktualisiert Python-Abhängigkeiten.
- Startet den laufenden Service danach neu; `data/homepanel.db` bleibt
  unverändert.

## 5. Verifikation & Diagnose

Auf dem Pi:

```bash
systemctl is-enabled homepanel.service
systemctl is-active homepanel.service
journalctl -u homepanel.service -n 40 --no-pager
ps aux | grep -E "cage|app.main" | grep -v grep
bash scripts/diagnose-pi.sh        # sammelt alles obige gebündelt
```

Framebuffer-Dump-Trick (Remote-Screen-Check):

```bash
ssh supervisor@192.168.178.138 'dd if=/dev/fb0 of=/tmp/fb.raw bs=4096 count=900'
scp supervisor@192.168.178.138:/tmp/fb.raw /tmp/fb.raw
magick -size 720x1280 -depth 8 rgba:/tmp/fb.raw /tmp/fb.png
tesseract /tmp/fb.png - --psm 0     # Orientation in Grad; 90/270 = Rotation aktiv
```

Fehlerbilder:

| Fehler | Ursache |
|---|---|
| „Could not connect to remote display“ | `WAYLAND_DISPLAY` wurde vorab gesetzt (aus der Unit entfernen) |
| „Unable to open DRM device“ | Seat-/Gruppen-Problem (`video`, `render`, `input`) |
| SIGABRT-Crashloop mit `eglfs` | eglfs auf DSI2 nicht nutzbar → cage verwenden |

Ausführliche Schritt-für-Schritt-Anleitung für das DSI2/cage-Setup: siehe
[`SETUP-STATUS.md`](../SETUP-STATUS.md) im Projektwurzelverzeichnis.