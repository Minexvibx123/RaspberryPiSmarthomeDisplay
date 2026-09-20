# Plugin: example_plugin

Minimales, **funktionierendes** Referenz-Plugin, das den Plugin-Seam von
HomePanel end-to-end demonstriert – ohne Fake-Widgets.

## Zweck

Zeigt den kompletten Lifecycle:

1. Discovery lädt `manifest.json` + `plugin.py`.
2. Der PluginManager injiziert `services` (ServiceRegistry) und ein
   namespaced `settings`-Handle (`plugin.example_plugin.*`).
3. `on_load()` setzt Marker (`loaded=true`, zählt `load_count`).
4. `on_unload()` loggt lediglich.

Es registriert **bewusst keine** Widgets und liefert keine App-Ansicht.

## Einstellungen (Demo)

| key | label | Typ |
|---|---|---|
| `endpoint` | Lokale Dienstadresse | text |
| `poll_interval` | Aktualisierung (Sekunden) | number |
| `notifications` | Benachrichtigungen | bool |
| `display_mode` | Anzeige | select (compact/detailed) |

## Verwendung als Vorlage

Neues Plugin: dieses Verzeichnis kopieren, `id`/`name` im Manifest und die
Resterfunktion anpassen. Eine Schritt-für-Schritt-Anleitung steht in
[`docs/plugin-development.md`](../../docs/plugin-development.md).