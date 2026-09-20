# Plugin: browser

Interner, touch-optimierter Browser für HomePanel – öffnet sich über den
App-Launcher als Vollbild-App **innerhalb** von HomePanel (kein externer
Prozess).

## Funktionen

- Navigation: Zurück, Vor, Neu laden, Home.
- URL-Eingabezeile.
- **Bookmarks** (Konfiguration `Name|URL;Name|URL`, default: Home Assistant +
  Router).
- Vollbild-Toggle.
- **Sicherer Fallback:** Ohne `PySide6.QtWebEngineWidgets` wird eine
  Hinweismeldung angezeigt und die Buttons sind deaktiviert – kein Absturz.

## Struktur

| Datei | Inhalt |
|---|---|
| `plugin.py` | `Settings-schema` (`home_url`, `bookmarks`) + `create_app_view()` |
| `view.py` | `BrowserView` (Qt-Widget, optional `QWebEngineView`) + `parse_bookmarks()` |

## Abhängigkeit

Optional: `PySide6.QtWebEngineWidgets` (liegt auf den meisten Plattformen im
`PySide6`-Wheel bei). Fehlt es, degradiert das Plugin graceful.

## Bedienung

1. Einstellungen → Plugins → Browser → Home-URL/Bookmarks setzen.
2. Im Panel auf den App-Launcher gehen → Browser öffnen.
3. Vollbild-Toggle zum Hin- und Herschalten zwischen Kiosk und Fenster.