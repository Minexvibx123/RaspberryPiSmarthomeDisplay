# Widget-System & Widget-Referenz

Widgets sind die zentrale Erweiterungsfläche von HomePanel. Jedes Widget ist
eine Qt-Klasse, die `BaseWidget` (`app/widgets/base.py`) erbt und ein
eigenes `PROPERTY_SCHEMA` deklariert. Editor, Bibliothek und
Eigenschaftenpanel sind rein schema-getrieben.

## `BaseWidget`

Zeigt übliches Verhalten: Styling, Entity-Bindung, Animation, bedingte
Sichtbarkeit/Styling, Editor-Auswahl.

Klassenattribute:
- `type_name` – eindeutige ID (z. B. `"light"`).
- `display_name` – Anzeigename in der Bibliothek.
- `category` – Gruppierung in der Bibliothek (`Steuerung`, `Anzeige`, `Internet`,
  `System`, `Allgemein`, `Apps`, `Custom`, …).
- `icon` – Emoji/Glpyh für die Bibliothek.
- `default_size` – `(breite, höhe)`.
- `requires_entity` – ob das Widget zwingend eine Entity braucht.
- `entity_domains` – erlaubte HA-Domains für den Entity-Picker.
- `PROPERTY_SCHEMA` – Liste zusätzlicher `PropertyDef`s.

Wichtige Methoden (überschreibbar):
- `build_ui()` – Kind-Widgets/Layouts anlegen.
- `refresh_from_state()` – Aussehen aus dem aktuellen Entity-Zustand aktualisieren.

Hilfsmethoden:
- `self.get_prop(key, fallback=None)` – Config lesen (beachtet Schema-Defaults
  und bedingte Overrides).
- `self.call_service(domain, service, **data)` – Service-Aufruf über den
  State-Manager (im Demo-Modus lokal simuliert).
- `self.entity()` – gebundene Entity-Instanz oder `None`.
- `self.set_active(active)` / `self.set_selected(selected)` – visueller Zustand.
- `self.full_schema()` – `COMMON_SCHEMA` + eigene `PROPERTY_SCHEMA`.

## `PropertyDef` und `COMMON_SCHEMA`

```python
PropertyDef(key, label, type, default=None, options=None, min=None, max=None,
            entity_domains=None, action="", group="Allgemein")
```

`PropertyDef.type` kann sein: `text`, `number`, `color`, `bool`, `select`,
`icon`, `entity`, `font_size`, `image`, `action`.

`COMMON_SCHEMA` gilt für **jedes** Widget:
- **Darstellung:** `bg_color`, `text_color`, `accent_color`, `radius`, `opacity`,
  `bg_gradient_enabled`, `gradient_color`, `gradient_direction`, `bg_image_path`,
  `bg_image_opacity`, `shadow`, `font_size`, `font_family`.
- **Layout:** `icon_position`, `padding`.
- **Sichtbarkeit:** `visible_entity`, `visible_operator`, `visible_state`,
  `visible_invert`.
- **Bedingtes Styling:** `style_enabled`, `style_entity`, `style_operator`,
  `style_value`, `style_bg_color`, `style_text_color`.
- **Animation:** `entrance_animation`, `state_animation`, `animation_speed`.

## Registry (`app/widgets/registry.py`)

- `WIDGET_CLASSES` – Liste aller eingebauten Klassen.
- `WIDGET_REGISTRY` – `dict[type_name] → Klasse`.
- `widget_class(type_name)`, `widgets_by_category()`.
- `register_widget_class(cls)` / `unregister_widget_class(type_name)` – für
  Plugins; `unregister` entfernt nur nachträglich registrierte Typen.

**Neues Widget einbauen:** Klasse schreiben, in `registry.py` importieren und
in `WIDGET_CLASSES` aufnehmen – sonst nichts.

## Eingebaute Widget-Typen (43)

### Steuerung
| type_name | Anzeigename | Datei |
|---|---|---|
| `button` | Button | `button.py` |
| `light` | Licht | `light.py` |
| `switch` | Schalter | `switch.py` |
| `slider` | Slider | `slider.py` |
| `thermostat` | Thermostat | `thermostat.py` |
| `cover` | Rollladen | `cover.py` |
| `media_player` | Medienplayer | `media_player.py` |
| `timer` | Timer | `timer.py` |
| `fan` | Lüfter | `ha_extra.py` |
| `lock` | Schloss | `ha_extra.py` |
| `humidifier` | Luftbefeuchter | `ha_extra.py` |
| `alarm_panel` | Alarmanlage | `ha_extra.py` |
| `vacuum` | Saugroboter | `ha_extra.py` |
| `scene_grid` | Szenen-Grid | `ha_extra.py` |
| `number_input` | Zahlenwert | `ha_extra.py` |
| `select` | Auswahlliste | `ha_extra.py` |

### Anzeige
| type_name | Anzeigename | Datei |
|---|---|---|
| `sensor` | Sensor | `sensor.py` |
| `weather` | Wetter (Home Assistant) | `weather.py` |
| `weather_api` | Wetter (Open-Meteo) | `weather_api.py` |
| `clock` | Uhr | `clock.py` |
| `text` | Text | `text.py` |
| `icon` | Icon | `icon_widget.py` |
| `entity_list` | Entity-Liste | `entity_list.py` |
| `camera` | Kamera | `camera.py` |
| `sensor_graph` | Sensor-Verlauf | `sensor_graph.py` |
| `calendar` | Kalender | `ha_extra.py` |
| `todo_list` | To-Do-Liste | `ha_extra.py` |
| `person` | Person | `ha_extra.py` |
| `notification` | Benachrichtigungen | `notification.py` |
| `energy` | Energie | `energy.py` |

### Internet
| type_name | Anzeigename | Datei |
|---|---|---|
| `crypto_price` | Kryptokurs | `internet.py` |
| `stock_price` | Aktienkurs | `internet.py` |
| `currency` | Wechselkurs | `internet.py` |
| `quote` | Zitat | `internet.py` |
| `joke` | Witz | `internet.py` |
| `holiday` | Feiertag | `internet.py` |
| `internet_status` | Internet-Status | `internet.py` |
| `news` | News-Feed | `internet.py` |
| `system_monitor` | System-Monitor | `internet.py` |

### System / Apps / Custom / Allgemein
| type_name | Anzeigename | Datei |
|---|---|---|
| `console` | Konsole | `console.py` |
| `container` | Container | `container.py` |
| `web` | Web Panel | `web.py` |
| `custom_widget` | Eigenes Widget | `custom_widget.py` |

### Besondere Widgets

- **`weather_api`** (`weather_api.py`) – Wetter ohne API-Key direkt von der
  Open-Meteo-API (aktuell + 3-Tage-Vorschau). Einstellbar: Ortsname,
  Breitengrad/Längengrad, Aktualisierungsintervall. Nützlich, wenn keine
  HA-Wetter-Entity existiert. Lädt im Hintergrund über `core/http_fetch.py`.
- **`custom_widget`** (`custom_widget.py`) – Rendert `config["elements"]`
  (Text, Icon, Sensor-Wert, Fortschrittsbalken, Button) absolut positioniert,
  gebunden über die sicheren Templates aus `core/expressions.py`. Konfiguriert
  über den Custom Widget Builder.
- **`web`** (`web.py`) – Optionaler QtWebEngine-Browser als Widget; ohne
  installiertes `PySide6.QtWebEngineWidgets` zeigt es einen Hinweistext statt
  abzustürzen.
- **`system_monitor`** (Internet-Kategorie) – eingebautes Demo-System-Monitoring;
  das „richtige" System-Monitoring kommt aus dem `system_monitor`-Plugin.

## Plugin-Widgets

Plugins können zur Laufzeit weitere Widget-Typen registrieren
(`register_widget_class`). Beispiele:

| type_name | Plugin | Beschreibung |
|---|---|---|
| `system_cpu`, `system_ram`, `system_storage`, `system_network`, `system_services` | `system_monitor` | /proc-/sys-basierte Metriken + systemd-Dienste |
| `flashforge_camera` | `flashforge` | Drucker-Kamera (MJPEG-Livestream) |
| `printer_status`, `print_control`, … | `flashforge` | Drucker-Status und -Steuerung |
| `pihole_stats`, `pihole_control` | `pihole` | Pi-hole-Statistiken + Blocking |
| `network_device` | `network` | Geräte-Erreichbarkeit (Ping) |
| `docker_containers` | `docker` | Container-Liste + Start/Stop/Neustart |

Siehe [Plugin-Entwicklung](plugin-development.md) und
[Plugin-Katalog](plugins/README.md).