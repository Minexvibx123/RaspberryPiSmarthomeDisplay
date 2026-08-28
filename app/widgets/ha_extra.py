"""Additional Home Assistant domain widgets: calendar, to-do, alarm panel,
vacuum, fan, lock, humidifier, person presence, scene grid, number input
and select/dropdown. These extend coverage well beyond the original core
widget set while following the exact same BaseWidget/PropertyDef pattern.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSlider, QVBoxLayout, QWidget,
)

from app.widgets.base import BaseWidget, PropertyDef
from app.widgets.icons import IconGlyph


class CalendarWidget(BaseWidget):
    type_name = "calendar"
    display_name = "Kalender"
    category = "Anzeige"
    icon = "calendar"
    default_size = (240, 150)
    requires_entity = True
    entity_domains = ["calendar"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["calendar"], group="Verbindung"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        header = QHBoxLayout()
        self.icon_label = IconGlyph("calendar", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(28, 28)
        self.name_label = QLabel(self.get_prop("name") or "Kalender")
        self.name_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 600; border: none; background: transparent;")
        header.addWidget(self.icon_label)
        header.addWidget(self.name_label, 1)
        self.content_layout.addLayout(header)

        self.event_label = QLabel("Kein anstehendes Ereignis")
        self.event_label.setWordWrap(True)
        self.event_label.setStyleSheet(f"color: {self.get_prop('accent_color', '#4C8DFF')}; font-size: 14px; border: none; background: transparent;")
        self.time_label = QLabel("")
        self.time_label.setStyleSheet("color: #AAAAAA; font-size: 12px; border: none; background: transparent;")
        self.content_layout.addWidget(self.event_label)
        self.content_layout.addWidget(self.time_label)
        self.content_layout.addStretch()

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            return
        self.event_label.setText(e.attributes.get("message") or e.state or "Kein anstehendes Ereignis")
        start = e.attributes.get("start_time", "")
        self.time_label.setText(start)


class TodoListWidget(BaseWidget):
    type_name = "todo_list"
    display_name = "To-Do-Liste"
    category = "Anzeige"
    icon = "list"
    default_size = (240, 220)
    requires_entity = True
    entity_domains = ["todo"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["todo"], group="Verbindung"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.title_label = QLabel(self.get_prop("name") or "To-Do")
        self.title_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 600; border: none; background: transparent;")
        self.content_layout.addWidget(self.title_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.list_container)
        self.content_layout.addWidget(self.scroll)

    def refresh_from_state(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        e = self.entity()
        count = e.attributes.get("all_items") if e else None
        items = count if isinstance(count, list) else []
        if not items:
            summary = QLabel(f"{e.state if e else '--'} offene Aufgaben")
            summary.setStyleSheet("color: #AAAAAA; font-size: 13px; border: none; background: transparent;")
            self.list_layout.addWidget(summary)
        else:
            for entry in items[:10]:
                summary = entry.get("summary", str(entry)) if isinstance(entry, dict) else str(entry)
                label = QLabel(f"\u2610  {summary}")
                label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: 13px; border: none; background: transparent;")
                self.list_layout.addWidget(label)
        self.list_layout.addStretch()


class AlarmPanelWidget(BaseWidget):
    type_name = "alarm_panel"
    display_name = "Alarmanlage"
    category = "Steuerung"
    icon = "shield"
    default_size = (220, 180)
    requires_entity = True
    entity_domains = ["alarm_control_panel"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["alarm_control_panel"], group="Verbindung"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.icon_label = IconGlyph("shield", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(40, 40)
        self.state_label = QLabel("--")
        self.state_label.setAlignment(Qt.AlignCenter)
        self.state_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 700; border: none; background: transparent;")
        self.content_layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)
        self.content_layout.addWidget(self.state_label)

        row = QHBoxLayout()
        self.arm_btn = QPushButton("Scharf")
        self.disarm_btn = QPushButton("Unscharf")
        for b, service in ((self.arm_btn, "alarm_arm_away"), (self.disarm_btn, "alarm_disarm")):
            b.setStyleSheet(f"background: rgba(255,255,255,20); color: {self.get_prop('text_color', '#FFFFFF')}; border-radius: 8px; padding: 6px;")
            b.clicked.connect(lambda checked=False, s=service: self.call_service("alarm_control_panel", s))
            row.addWidget(b)
        self.content_layout.addLayout(row)

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            return
        armed = e.state not in ("disarmed", "unknown")
        self.set_active(armed)
        labels = {
            "armed_away": "Scharf (Abwesend)", "armed_home": "Scharf (Zuhause)",
            "disarmed": "Unscharf", "pending": "Wird aktiviert...", "triggered": "ALARM!",
        }
        self.state_label.setText(labels.get(e.state, e.state.capitalize()))
        self.icon_label.set_color("#E05555" if e.state == "triggered" else (self.get_prop("accent_color", "#4C8DFF") if armed else "#777777"))


class VacuumWidget(BaseWidget):
    type_name = "vacuum"
    display_name = "Staubsauger"
    category = "Steuerung"
    icon = "vacuum"
    default_size = (220, 170)
    requires_entity = True
    entity_domains = ["vacuum"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["vacuum"], group="Verbindung"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.icon_label = IconGlyph("vacuum", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(40, 40)
        self.state_label = QLabel("--")
        self.state_label.setAlignment(Qt.AlignCenter)
        self.state_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; border: none; background: transparent;")
        self.battery_label = QLabel("")
        self.battery_label.setAlignment(Qt.AlignCenter)
        self.battery_label.setStyleSheet("color: #AAAAAA; font-size: 12px; border: none; background: transparent;")
        for w in (self.icon_label, self.state_label, self.battery_label):
            self.content_layout.addWidget(w, alignment=Qt.AlignCenter)

        row = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.dock_btn = QPushButton("Andocken")
        for b, service in ((self.start_btn, "start"), (self.dock_btn, "return_to_base")):
            b.setStyleSheet(f"background: rgba(255,255,255,20); color: {self.get_prop('text_color', '#FFFFFF')}; border-radius: 8px; padding: 6px;")
            b.clicked.connect(lambda checked=False, s=service: self.call_service("vacuum", s))
            row.addWidget(b)
        self.content_layout.addLayout(row)

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            return
        self.set_active(e.state == "cleaning")
        self.state_label.setText(e.state.capitalize())
        battery = e.attributes.get("battery_level")
        self.battery_label.setText(f"Akku: {battery}%" if battery is not None else "")


class FanWidget(BaseWidget):
    type_name = "fan"
    display_name = "Lüfter"
    category = "Steuerung"
    icon = "fan"
    default_size = (200, 150)
    requires_entity = True
    entity_domains = ["fan"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["fan"], group="Verbindung"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        header = QHBoxLayout()
        self.icon_label = IconGlyph("fan", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(28, 28)
        self.name_label = QLabel(self.get_prop("name") or "Lüfter")
        self.name_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 600; border: none; background: transparent;")
        header.addWidget(self.icon_label)
        header.addWidget(self.name_label, 1)
        self.content_layout.addLayout(header)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.sliderReleased.connect(self._on_speed_changed)
        self.content_layout.addWidget(self.slider)
        self.content_layout.addStretch()

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            return
        is_on = e.state == "on"
        self.set_active(is_on)
        self.icon_label.set_color(self.get_prop("accent_color", "#4C8DFF") if is_on else "#777777")
        pct = e.attributes.get("percentage")
        if pct is not None:
            self.slider.blockSignals(True)
            self.slider.setValue(int(pct))
            self.slider.blockSignals(False)

    def _on_speed_changed(self) -> None:
        self.call_service("fan", "set_percentage", percentage=self.slider.value())

    def mouseReleaseEvent(self, event) -> None:
        if not self.slider.underMouse():
            self.call_service("fan", "toggle")
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class LockWidget(BaseWidget):
    type_name = "lock"
    display_name = "Schloss"
    category = "Steuerung"
    icon = "lock"
    default_size = (200, 120)
    requires_entity = True
    entity_domains = ["lock"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["lock"], group="Verbindung"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        row = QHBoxLayout()
        self.icon_label = IconGlyph("lock", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(30, 30)
        self.name_label = QLabel(self.get_prop("name") or "Schloss")
        self.name_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 600; border: none; background: transparent;")
        row.addWidget(self.icon_label)
        row.addWidget(self.name_label, 1)
        self.content_layout.addLayout(row)
        self.state_label = QLabel("")
        self.state_label.setStyleSheet("color: #AAAAAA; font-size: 13px; border: none; background: transparent;")
        self.content_layout.addWidget(self.state_label)
        self.content_layout.addStretch()

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            return
        locked = e.state == "locked"
        self.set_active(not locked)  # unlocked = attention-worthy state
        self.state_label.setText("Verriegelt" if locked else "Entriegelt")
        self.icon_label.set_color(self.get_prop("accent_color", "#4C8DFF") if locked else "#E0A030")

    def mouseReleaseEvent(self, event) -> None:
        e = self.entity()
        service = "unlock" if e and e.state == "locked" else "lock"
        self.call_service("lock", service)
        self.clicked.emit()
        super().mouseReleaseEvent(event)


class HumidifierWidget(BaseWidget):
    type_name = "humidifier"
    display_name = "Luftbefeuchter"
    category = "Steuerung"
    icon = "drop"
    default_size = (200, 160)
    requires_entity = True
    entity_domains = ["humidifier"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["humidifier"], group="Verbindung"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.icon_label = IconGlyph("drop", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(36, 36)
        self.target_label = QLabel("--%")
        self.target_label.setAlignment(Qt.AlignCenter)
        self.target_label.setStyleSheet(f"color: {self.get_prop('accent_color', '#4C8DFF')}; font-size: {int(self.get_prop('font_size', 16)) + 8}px; font-weight: 700; border: none; background: transparent;")
        self.state_label = QLabel("")
        self.state_label.setAlignment(Qt.AlignCenter)
        self.state_label.setStyleSheet("color: #AAAAAA; font-size: 12px; border: none; background: transparent;")
        for w in (self.icon_label, self.target_label, self.state_label):
            self.content_layout.addWidget(w, alignment=Qt.AlignCenter)

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            return
        is_on = e.state == "on"
        self.set_active(is_on)
        target = e.attributes.get("humidity")
        self.target_label.setText(f"{target}%" if target is not None else "--%")
        self.state_label.setText("An" if is_on else "Aus")

    def mouseReleaseEvent(self, event) -> None:
        self.call_service("humidifier", "toggle")
        self.clicked.emit()
        super().mouseReleaseEvent(event)


class PersonWidget(BaseWidget):
    type_name = "person"
    display_name = "Person"
    category = "Anzeige"
    icon = "person"
    default_size = (160, 150)
    requires_entity = True
    entity_domains = ["person"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["person"], group="Verbindung"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.icon_label = IconGlyph("person", self.get_prop("accent_color", "#4C8DFF"))
        self.icon_label.setFixedSize(40, 40)
        self.name_label = QLabel(self.get_prop("name") or "Person")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 600; border: none; background: transparent;")
        self.state_label = QLabel("")
        self.state_label.setAlignment(Qt.AlignCenter)
        self.state_label.setStyleSheet("color: #AAAAAA; font-size: 12px; border: none; background: transparent;")
        for w in (self.icon_label, self.name_label, self.state_label):
            self.content_layout.addWidget(w, alignment=Qt.AlignCenter)

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            return
        home = e.state == "home"
        self.set_active(home)
        self.icon_label.set_color(self.get_prop("accent_color", "#4C8DFF") if home else "#777777")
        self.state_label.setText("Zuhause" if home else e.state.replace("_", " ").capitalize())


class SceneGridWidget(BaseWidget):
    """A small grid of scene-activation buttons (comma-separated entity_ids)."""

    type_name = "scene_grid"
    display_name = "Szenen-Grid"
    category = "Steuerung"
    icon = "scene"
    default_size = (300, 200)
    requires_entity = False

    PROPERTY_SCHEMA = [
        PropertyDef("scenes", "Szenen (Komma-getrennt: entity_id=Anzeigename)", "text", "", group="Inhalt"),
        PropertyDef("columns", "Spalten", "number", 2, min=1, max=4, group="Format"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        grid = QGridLayout()
        grid.setSpacing(8)
        raw = self.get_prop("scenes", "")
        entries = [e.strip() for e in raw.split(",") if e.strip()]
        columns = max(1, int(self.get_prop("columns", 2)))
        for i, entry in enumerate(entries):
            entity_id, _, label_text = entry.partition("=")
            entity_id = entity_id.strip()
            label_text = label_text.strip() or entity_id
            btn = QPushButton(label_text)
            btn.setStyleSheet(
                f"background: rgba(255,255,255,20); color: {self.get_prop('text_color', '#FFFFFF')}; border-radius: 10px; padding: 10px;"
            )
            btn.clicked.connect(lambda checked=False, eid=entity_id: self._activate(eid))
            grid.addWidget(btn, i // columns, i % columns)
        self.content_layout.addLayout(grid)
        self.content_layout.addStretch()

    def refresh_from_state(self) -> None:
        pass

    def _activate(self, entity_id: str) -> None:
        if self.state_manager and entity_id:
            self.state_manager.call_service("scene", "turn_on", entity_id=entity_id)


class NumberInputWidget(BaseWidget):
    type_name = "number_input"
    display_name = "Zahlenwert"
    category = "Steuerung"
    icon = "gauge"
    default_size = (200, 150)
    requires_entity = True
    entity_domains = ["number", "input_number"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["number", "input_number"], group="Verbindung"),
        PropertyDef("step", "Schrittweite", "number", 1, min=0.1, max=100, group="Verhalten"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.name_label = QLabel(self.get_prop("name") or "Wert")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {int(self.get_prop('font_size', 16)) - 1}px; border: none; background: transparent;")
        self.content_layout.addWidget(self.name_label)

        row = QHBoxLayout()
        self.minus_btn = QPushButton("-")
        self.plus_btn = QPushButton("+")
        for b in (self.minus_btn, self.plus_btn):
            b.setFixedSize(44, 44)
            b.setStyleSheet(f"QPushButton {{ font-size: 22px; border-radius: 22px; background: rgba(255,255,255,20); color: {self.get_prop('text_color', '#FFFFFF')}; }}")
        self.value_label = QLabel("--")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet(f"color: {self.get_prop('accent_color', '#4C8DFF')}; font-size: {int(self.get_prop('font_size', 16)) + 14}px; font-weight: 700; border: none; background: transparent;")
        self.minus_btn.clicked.connect(lambda: self._adjust(-self.get_prop("step", 1)))
        self.plus_btn.clicked.connect(lambda: self._adjust(self.get_prop("step", 1)))
        row.addWidget(self.minus_btn)
        row.addWidget(self.value_label, 1)
        row.addWidget(self.plus_btn)
        self.content_layout.addLayout(row)

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            return
        try:
            self.value_label.setText(f"{float(e.state):g}")
        except (ValueError, TypeError):
            self.value_label.setText(e.state)

    def _adjust(self, delta: float) -> None:
        e = self.entity()
        if not e:
            return
        try:
            new_val = round(float(e.state) + delta, 2)
        except (ValueError, TypeError):
            return
        domain = self.config.get("entity_id", "number.").split(".")[0]
        self.call_service(domain, "set_value", value=new_val)


class SelectWidget(BaseWidget):
    type_name = "select"
    display_name = "Auswahlliste"
    category = "Steuerung"
    icon = "list"
    default_size = (220, 130)
    requires_entity = True
    entity_domains = ["select", "input_select"]

    PROPERTY_SCHEMA = [
        PropertyDef("entity_id", "Entity", "entity", "", entity_domains=["select", "input_select"], group="Verbindung"),
    ]

    def build_ui(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.name_label = QLabel(self.get_prop("name") or "Auswahl")
        self.name_label.setStyleSheet(f"color: {self.get_prop('text_color', '#FFFFFF')}; font-size: {self.get_prop('font_size', 16)}px; font-weight: 600; border: none; background: transparent;")
        self.content_layout.addWidget(self.name_label)
        self.combo = QComboBox()
        self.combo.activated.connect(self._on_selected)
        self.content_layout.addWidget(self.combo)
        self.content_layout.addStretch()

    def refresh_from_state(self) -> None:
        e = self.entity()
        if not e:
            return
        options = e.attributes.get("options", [])
        self.combo.blockSignals(True)
        if [self.combo.itemText(i) for i in range(self.combo.count())] != options:
            self.combo.clear()
            self.combo.addItems(options)
        if e.state in options:
            self.combo.setCurrentText(e.state)
        self.combo.blockSignals(False)

    def _on_selected(self, index: int) -> None:
        domain = self.config.get("entity_id", "select.").split(".")[0]
        self.call_service(domain, "select_option", option=self.combo.itemText(index))
