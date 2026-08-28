#!/usr/bin/env python3
"""Configure Home Assistant connection without touching the touchscreen UI.

Useful for headless setup over SSH, e.g. when the panel has no keyboard
attached and pasting a 50+ character long-lived access token via the
on-screen wizard isn't practical.

Usage:
    .venv/bin/python scripts/configure_ha.py --url http://homeassistant.local:8123 --token <TOKEN>
    .venv/bin/python scripts/configure_ha.py --demo   # switch to demo mode instead
    .venv/bin/python scripts/configure_ha.py --show   # print current (token masked) settings
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import Database
from app.core.homeassistant import HomeAssistantClient
from app.core.settings import AppSettings


def mask(token: str) -> str:
    if not token:
        return "(nicht gesetzt)"
    return f"{token[:4]}...{token[-4:]} ({len(token)} Zeichen)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Home Assistant Adresse, z. B. http://homeassistant.local:8123")
    parser.add_argument("--token", help="Long-Lived Access Token")
    parser.add_argument("--demo", action="store_true", help="Demo-Modus aktivieren (kein Home Assistant nötig)")
    parser.add_argument("--no-demo", action="store_true", help="Demo-Modus deaktivieren")
    parser.add_argument("--show", action="store_true", help="Aktuelle Einstellungen anzeigen und beenden")
    parser.add_argument("--skip-test", action="store_true", help="Verbindungstest überspringen")
    args = parser.parse_args()

    db = Database()
    settings = AppSettings(db)

    if args.show:
        print(f"ha_url:         {settings.ha_url or '(nicht gesetzt)'}")
        print(f"ha_token:       {mask(settings.ha_token)}")
        print(f"demo_mode:      {settings.demo_mode}")
        print(f"setup_complete: {settings.setup_complete}")
        return 0

    if args.demo:
        settings.demo_mode = True
        settings.setup_complete = True
        print("Demo-Modus aktiviert.")
        return 0

    if args.no_demo:
        settings.demo_mode = False

    if args.url:
        settings.ha_url = args.url
    if args.token:
        settings.ha_token = args.token

    if not settings.ha_url or not settings.ha_token:
        print("Fehler: --url und --token werden benötigt (oder --demo für Demo-Modus).", file=sys.stderr)
        return 1

    if not args.skip_test:
        client = HomeAssistantClient(settings.ha_url, settings.ha_token)
        ok, msg = client.test_connection()
        print(f"Verbindungstest: {'OK' if ok else 'FEHLGESCHLAGEN - ' + msg}")
        if not ok:
            print("Einstellungen wurden NICHT übernommen. Mit --skip-test erzwingen.", file=sys.stderr)
            return 1

    settings.demo_mode = False
    settings.setup_complete = True
    print("Gespeichert. Bitte 'sudo systemctl restart homepanel.service' ausführen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
