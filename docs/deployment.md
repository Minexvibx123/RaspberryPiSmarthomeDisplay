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
6. Aktiviert `homepanel.service` für den Autostart beim Booten. Die Installation
  startet den Dienst nicht unmittelbar; nach dem nötigen Neustart startet er
  automatisch oder kann manuell gestartet werden.

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
TTYPath=/dev/tty1
Environment=QT_QPA_PLATFORM=wayland
Environment=PYTHONUNBUFFERED=1
ExecStartPost=/bin/sh -c 'i=0; until [ -S /run/user/$(id -u)/wayland-0 ] && XDG_RUNTIME_DIR=/run/user/$(id -u) WAYLAND_DISPLAY=wayland-0 wlr-randr --output DSI-1 --transform 270; do i=$((i+1)); sleep 0.5; [ $i -ge 30 ] && break; done'
WorkingDirectory=/home/pi/homepanel
ExecStart=/bin/sh -c 'export XDG_RUNTIME_DIR=/run/user/$(id -u); exec /usr/bin/cage -d -- /home/pi/homepanel/.venv/bin/python -m app.main'
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Wichtige Punkte:

- **DRM-Sitzung auf `tty1`:** `PAMName=login` zusammen mit `TTYPath=/dev/tty1`
  stellt die lokale Seat-Sitzung bereit, die cage für den DRM-Zugriff benötigt.
- **`cage -d`** ist ein minimaler Wayland-Kiosk-Compositor. Er ist nötig,
  weil auf dem Pi 5 das DSI-Panel an einem eigenen DRM-Device
  (`drm-rp1-dsi`) hängt: Qt-`eglfs` würde dort abstrürzen (SIGABRT),
  `linuxfb` kann nicht rotieren. `cage` bringt GPU-Beschleunigung (v3d),
  Output-Rotation und mitgedrehte Touch-Koordinaten (wlroots/libinput).
- **`QT_QPA_PLATFORM=wayland`** – Qt nutzt den Wayland-Backend.
- **`WAYLAND_DISPLAY` darf nicht vorab gesetzt sein** – cage exportiert es
  selbst für die Clients.
- **`XDG_RUNTIME_DIR`** wird für cage aus der UID des Dienstbenutzers gebildet.
- **Rotation** über `ExecStartPost`: Nach Erscheinen des Wayland-Sockets wird
  der Pi-5-Ausgang `DSI-1` auf `270` gedreht (bis zu 30 Versuche im Abstand
  von 0,5 s). Diese Standard-Unit startet `/usr/bin/cage`; sie verwendet nicht
  automatisch den Touch-Patch aus `/usr/local/bin/cage`.
- `Restart=always` + `RestartSec=3` für Crash-Recovery.
- Die separate Unit `systemd/homepanel-touch.service` kann den Goodix-Touch-
  Probeversuch ausführen. Sie wird weder von `install.sh` noch von
  `fix-kiosk.sh` aktiviert. `systemd/homepanel-vnc.service` startet die
  optionale Browser-/VNC-Ansicht im alternativen tty1-Modell. Details stehen
  in [Skripte](scripts.md).

`install.sh` verwendet den oben gezeigten direkten systemd-Start. Für Geräte,
bei denen logind den DRM-Seat mit diesem Startmodell nicht zuverlässig
bereitstellt, gibt es das alternative tty1-Modell: `build-cage.sh` installiert
das gepatchte cage, anschließend richtet `fix-kiosk.sh` tty1-Autologin und den
Start über `kiosk-session.sh` ein. Dieses Skript ruft explizit
`/usr/local/bin/cage` auf. `fix-kiosk.sh` deaktiviert `homepanel.service`. Nach
diesem Wechsel ist ein Neustart nötig. Beide Kiosk-Modelle nicht gleichzeitig
starten.

Die von `fix-kiosk.sh` eingerichtete noVNC-Ansicht ist unter
`http://<pi-ip>:6080/vnc.html` erreichbar. Sie hat keine eigene
Passwortabfrage; Port `6080` daher nur in einem vertrauenswürdigen LAN und
mit Firewall-Beschränkung auf berechtigte Clients bereitstellen. Display- und
Browser-Instanz teilen die SQLite-Konfiguration und übernehmen Änderungen
gegenseitig.

## 3. Codeänderungen auf ein Gerät übertragen

```bash
./scripts/sync-pi.sh                    # Ziel: supervisor@192.168.178.138
./scripts/sync-pi.sh user@andere-ip     # anderes Ziel
```

Geschützt: `.venv/`, `data/` (SQLite), `.git/`, `thoughts/`.
Danach auf dem Pi: Abhängigkeiten installieren und Dienst neu starten.

Die systemd-Vorlage wird bei der Installation auf Benutzer und Installationspfad
angepasst. Für Änderungen am Kiosk-Setup bevorzugt die passenden Skripte aus
[`scripts/`](scripts.md); Zugangsdaten gehören nicht in Shell-Befehle oder
Versionskontrolle.

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
| SIGABRT-Crashloop mit `eglfs` | eglfs auf DSI nicht nutzbar → cage verwenden |

Für ein alternatives Startmodell, Goodix-Touch-Fehlersuche und den Bau des
gepatchten cage siehe die Befehle und Voraussetzungen in
[`scripts.md`](scripts.md).