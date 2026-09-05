"""Headless verification for the CustomWidget builder-driven element rendering."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.widgets.custom_widget import CustomWidget  # noqa: E402


class _FakeEntity:
    def __init__(self, state):
        self.state = state


class _FakeStateManager:
    def __init__(self):
        self.entities = {"sensor.temp": _FakeEntity("23.4"), "input_boolean.demo": _FakeEntity("on")}
        self.calls = []

    def get_entity(self, entity_id):
        return self.entities.get(entity_id)

    def call_service(self, domain, service, entity_id=None, **_data):
        self.calls.append((domain, service, entity_id))


app = QApplication(sys.argv)

config = {
    "elements": [
        {"type": "text", "template": "{{ state }} °C", "entity_id": "sensor.temp", "x": 0, "y": 0, "w": 150, "h": 30, "color": "#FFFFFF"},
        {"type": "progress_bar", "template": "{{ state }}", "entity_id": "sensor.temp", "x": 0, "y": 40, "w": 150, "h": 20},
        {"type": "icon", "icon": "star", "x": 0, "y": 70, "w": 30, "h": 30, "color": "#FFFFFF"},
        {"type": "button", "template": "Toggle", "entity_id": "input_boolean.demo", "x": 0, "y": 110, "w": 100, "h": 30},
    ],
}

state_manager = _FakeStateManager()
widget = CustomWidget(1, config, state_manager=state_manager)

assert len(widget._element_widgets) == 4, "expected 4 rendered elements"
text_widget = widget._element_widgets[0]
assert text_widget.text() == "23.4 °C", f"unexpected text: {text_widget.text()!r}"
progress_widget = widget._element_widgets[1]
assert progress_widget.value() == 23, f"unexpected progress value: {progress_widget.value()}"

# rebuild must not leak previous children
widget.build_ui()
assert len(widget._element_widgets) == 4

# button click toggles the bound entity via the shared state manager
button_widget = widget._element_widgets[3]
button_widget.click()
assert state_manager.calls == [("input_boolean", "toggle", "input_boolean.demo")], state_manager.calls

print("VERIFICATION PASSED")
