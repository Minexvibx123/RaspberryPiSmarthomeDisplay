# SETUP-STATUS / Speicherpunkt (21.08.2026, ~23:20)

> **Status (aktualisiert):** Das hier beschriebene Rendering-/Rotation-Problem
> ist gelöst und der Autostart läuft stabil auf dem Pi. Diese Datei bleibt als
> Hardware-Troubleshooting-Playbook für das DSI2/cage-Setup erhalten (Framebuffer-
> Dump-Trick, Stolperfallen). Für den aktuellen Architektur- und Feature-Stand
> siehe [AI-CONTEXT.md](AI-CONTEXT.md), für Installation/Update siehe [README.md](README.md).

Stand der Dinge nach der Debugging-Session – hier weitermachen.

## Zugang zum Pi

```bash
ssh supervisor@192.168.178.138          # passwortlos (SSH-Key installiert)
# sudo auf dem Pi:  echo 0908 | sudo -S <befehl>
```

Pi: Raspberry Pi 5, Debian 13 (trixie) aarch64, offizielles 7"-Touch Display 2
(DSI2, **720x1280 portrait-native**), User `supervisor` (Gruppen: video, render, input ✓).

## Was das Problem war (gelöst)

1. **SIGABRT-Crashloop**: Pi 5 hängt das DSI-Panel an ein EIGENES DRM-Device
   (`/dev/dri/card1` = drm-rp1-dsi; card0=v3d GPU, card2=vc4 HDMI).
   Qt-eglfs braucht Render+Display am selben Device → Surface-Erstellung
   schlug fehl → Qt abort() → Crash alle ~3s. eglfs ist auf dieser Hardware
   **nicht benutzbar**, auch nicht mit KMS-Config-Pinning.
   → Zwischenlösung linuxfb lief stabil, kann aber NICHT rotieren.
2. **Lösung jetzt: cage (Wayland-Kiosk)** – GPU-Beschleunigung + Rotation +
   Touch-Mitdrehung via wlroots/libinput. `cage` und `wlr-randr` sind per apt
   installiert.
3. **Kein Einrichtungsassistent / Demo-Modus**: Meine früheren Testläufe mit
   `--demo` hatten `demo_mode=true` + `setup_complete=true` in die SQLite-DB
   geschrieben (main.py persistiert das). **DB ist gefixt**: beide Keys = false
   (`~/homepanel/data/homepanel.db`, Tabelle `settings`). Beim nächsten
   App-Start kommt der Wizard wieder.

## Aktueller Stand auf dem Pi

- Service: `active`, `enabled` (Autostart-Symlink liegt jetzt korrekt in
  `multi-user.target.wants`, vorher graphical.target = wurde beim Boot nie erreicht)
- cage läuft als PID mit ExecStart `/usr/bin/cage -d -- .venv/bin/python -m app.main`
- **UNGEKLÄRT (als Nächstes prüfen!)**: Ob die App unter cage erfolgreich rendert
  und ob die Landscape-Rotation (transform 90) stimmt. Erste cage-Version startete
  im Wayland-Backend statt DRM ("Could not connect to remote display") – Ursache
  war die vorgesezte Env `WAYLAND_DISPLAY`; die Zeile ist inzwischen aus der
  Unit entfernt. Danach wurde neu deployt + gestartet, aber noch NICHT verifiziert!

## Nächste Schritte (in dieser Reihenfolge)

1. Verifizieren:
   ```bash
   systemctl is-active homepanel.service
   echo 0908 | sudo -S journalctl -u homepanel.service --since "5 min ago" --no-pager | grep -viE "pam_unix|failed to connect"
   ps aux | grep -E "cage|app.main" | grep -v grep
   ```
   Fehlerbild "Could not connect to remote display" = WAYLAND_DISPLAY-Problem
   (sollte gefixt sein); Fehler "Unable to open DRM device" o.ä. = Seat-Problem.

2. Rendering + Rotation verifizieren (OCR-Trick, tesseract lokal):
   ```bash
   ssh supervisor@192.168.178.138 'dd if=/dev/fb0 of=/tmp/fb.raw bs=4096 count=900'
   scp supervisor@...:/tmp/fb.raw /tmp/opencode/fb.raw
   magick -size 720x1280 -depth 8 rgba:/tmp/opencode/fb.raw /tmp/opencode/fb.png
   tesseract /tmp/opencode/fb.png - --psm 11        # erkannter Text?
   tesseract /tmp/opencode/fb.png - --psm 0         # Orientation in Grad
   ```
   - Orientation 0° + Text lesbar → Inhalt noch portrait → cage rendert evtl. gar nicht (FB zeigt alten Inhalt!)
   - Orientation 90° oder 270° → Rotation aktiv! Richtung prüfen: Wenn Text falsch herum, in der Unit `--transform 90` ↔ `--transform 270` tauschen, `daemon-reload && restart`.

3. Wizard-Check: Panel sollte den Einrichtungsassistenten zeigen
   (setup_complete=false). Durchspielen (HA-Token oder Demo wählen).

4. Touch testen (unter cage sollte wlroots die Koordinaten automatisch
   mitrotieren). Goodix hängt an /dev/input/event9.

5. Boot-Autostart testen: `sudo reboot` → Panel muss ohne Zutun hochkommen.

## Wichtige Dateien

- **Lokal**: `systemd/homepanel.service` = aktuelle cage-Version (User=pi,
  Pfade /home/pi/homepanel als Platzhalter – Deploy-SED macht daraus supervisor):
  ```bash
  scp systemd/homepanel.service supervisor@192.168.178.138:/tmp/
  ssh supervisor@192.168.178.138 'echo 0908 | sudo -S sh -c \
    "sed \"s#/home/pi/homepanel#/home/supervisor/homepanel#g; s#User=pi#User=supervisor#g\" /tmp/homepanel.service > /etc/systemd/system/homepanel.service && systemctl daemon-reload && systemctl restart homepanel.service"'
  ```
- Rotation stecken in der Unit: `ExecStartPost=... wlr-randr --output DSI-2 --transform 90`
- DB: `~/homepanel/data/homepanel.db` → Tabelle settings (Werte JSON-kodiert)

## Stolperfallen

- `pkill -f "app.main --demo"` killt die eigene SSH-Session (Muster matcht den
  SSH-Befehl selbst). Besser: `pkill -f "bin/python -m app.main"`
- Subagents/Automatisierung liefen ins Leere → alles direkt machen
- Framebuffer-Dump immer mit bs=4096 count=900 (= 3.686.400 Bytes = 720*1280*4)
