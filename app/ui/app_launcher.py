"""Touch-first launcher for plugin-provided internal HomePanel apps."""
from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class AppLauncher(QWidget):
    def __init__(self, plugin_manager, open_app, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel("Apps")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        layout.addWidget(title)
        grid = QGridLayout()
        index = 0
        for info in plugin_manager.list_plugins():
            plugin = plugin_manager.get_instance(info.id)
            if plugin is None or type(plugin).create_app_view is getattr(__import__("app.plugins.api", fromlist=["Plugin"]), "Plugin").create_app_view:
                continue
            button = QPushButton(info.name)
            button.setMinimumHeight(72)
            button.clicked.connect(lambda _checked=False, plugin_id=info.id: open_app(plugin_id))
            grid.addWidget(button, index // 2, index % 2)
            index += 1
        if index == 0:
            layout.addWidget(QLabel("Keine Plugin-Apps verfügbar."))
        else:
            layout.addLayout(grid)
        layout.addStretch()