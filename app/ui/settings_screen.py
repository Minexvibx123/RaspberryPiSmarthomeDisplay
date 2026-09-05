"""Settings screen: connection, themes, security, backup/import/export.

Everything here is graphical - no config file ever needs to be hand-edited.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QColorDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSlider, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget,
)

from app.core.homeassistant import HomeAssistantClient
from app.ui.themes import BUILT_IN_THEMES, build_stylesheet


class SettingsScreen(QWidget):
    def __init__(self, db, settings, theme_manager, app, on_theme_applied=None, parent=None, plugin_manager=None):
        super().__init__(parent)
        self.db = db
        self.settings = settings
        self.theme_manager = theme_manager
        self.app = app
        self.on_theme_applied = on_theme_applied
        self.plugin_manager = plugin_manager

        root = QVBoxLayout(self)
        title = QLabel("Einstellungen")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        root.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), "Allgemein")
        tabs.addTab(self._build_ha_tab(), "Home Assistant")
        tabs.addTab(self._build_theme_tab(), "Design")
        tabs.addTab(self._build_standby_tab(), "Standby & Display")
        tabs.addTab(self._build_plugins_tab(), "Plugins")
        tabs.addTab(self._build_security_tab(), "Sicherheit")
        tabs.addTab(self._build_backup_tab(), "Backup")
        root.addWidget(tabs, 1)

    # ------------------------------------------------------------------ #
    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        lang_combo = QComboBox()
        lang_combo.addItems(["Deutsch", "English"])
        lang_combo.setCurrentText("Deutsch" if self.settings.language == "de" else "English")
        lang_combo.currentTextChanged.connect(lambda t: setattr(self.settings, "language", "de" if t == "Deutsch" else "en"))
        form.addRow("Sprache", lang_combo)

        nav_combo = QComboBox()
        nav_combo.addItems(["bottom", "sidebar"])
        nav_combo.setCurrentText(self.settings.navigation_style)
        nav_combo.currentTextChanged.connect(lambda t: setattr(self.settings, "navigation_style", t))
        form.addRow("Navigation", nav_combo)

        orient_combo = QComboBox()
        orient_combo.addItems(["landscape", "portrait"])
        orient_combo.setCurrentText(self.settings.orientation)
        orient_combo.currentTextChanged.connect(lambda t: setattr(self.settings, "orientation", t))
        form.addRow("Ausrichtung", orient_combo)
        orient_hint = QLabel("Nach dem Ändern HomePanel neu starten (und ggf. den Bildschirm per config.txt drehen).")
        orient_hint.setWordWrap(True)
        orient_hint.setStyleSheet("color: #9AA1B4; font-size: 12px;")
        form.addRow("", orient_hint)
        return w

    def _build_standby_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.standby_check = QCheckBox("Standby aktivieren")
        self.standby_check.setChecked(self.settings.standby_enabled)
        self.standby_check.toggled.connect(lambda v: setattr(self.settings, "standby_enabled", v))
        form.addRow("", self.standby_check)

        self.dim_spin = QSpinBox()
        self.dim_spin.setRange(1, 60)
        self.dim_spin.setValue(self.settings.standby_dim_minutes)
        self.dim_spin.valueChanged.connect(lambda v: setattr(self.settings, "standby_dim_minutes", v))
        form.addRow("Abdunkeln nach (Minuten)", self.dim_spin)

        self.off_spin = QSpinBox()
        self.off_spin.setRange(1, 120)
        self.off_spin.setValue(self.settings.standby_off_minutes)
        self.off_spin.valueChanged.connect(lambda v: setattr(self.settings, "standby_off_minutes", v))
        form.addRow("Display aus nach (Minuten)", self.off_spin)

        dim_opacity_row = QHBoxLayout()
        self.dim_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.dim_opacity_slider.setRange(10, 95)
        self.dim_opacity_slider.setValue(self.settings.standby_dim_opacity)
        self.dim_opacity_label = QLabel(f"{self.settings.standby_dim_opacity}%")
        self.dim_opacity_slider.valueChanged.connect(self._on_dim_opacity_changed)
        dim_opacity_row.addWidget(self.dim_opacity_slider, 1)
        dim_opacity_row.addWidget(self.dim_opacity_label)
        form.addRow("Abdunkel-Stärke (%)", dim_opacity_row)

        self.screensaver_mode_combo = QComboBox()
        self.screensaver_mode_combo.addItem("Digitale Uhr", "digital_clock")
        self.screensaver_mode_combo.addItem("Systeminformationen", "system_info")
        current_mode_index = self.screensaver_mode_combo.findData(self.settings.screensaver_mode)
        self.screensaver_mode_combo.setCurrentIndex(max(0, current_mode_index))
        self.screensaver_mode_combo.currentIndexChanged.connect(
            lambda index: setattr(self.settings, "screensaver_mode", self.screensaver_mode_combo.itemData(index))
        )
        form.addRow("Screensaver-Modus", self.screensaver_mode_combo)

        background_row = QHBoxLayout()
        self.screensaver_background_edit = QLineEdit(self.settings.screensaver_background_path)
        self.screensaver_background_edit.setReadOnly(True)
        browse_background_btn = QPushButton("Durchsuchen…")
        browse_background_btn.clicked.connect(self._pick_screensaver_background)
        clear_background_btn = QPushButton("✕")
        clear_background_btn.setFixedWidth(28)
        clear_background_btn.clicked.connect(self._clear_screensaver_background)
        background_row.addWidget(self.screensaver_background_edit, 1)
        background_row.addWidget(browse_background_btn)
        background_row.addWidget(clear_background_btn)
        form.addRow("Hintergrundbild", background_row)

        return w

    def _pick_screensaver_background(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Hintergrundbild auswählen", "",
            "Bilder (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if path:
            self.settings.screensaver_background_path = path
            self.screensaver_background_edit.setText(path)

    def _clear_screensaver_background(self) -> None:
        self.settings.screensaver_background_path = ""
        self.screensaver_background_edit.setText("")

    def _on_dim_opacity_changed(self, value: int) -> None:
        self.settings.standby_dim_opacity = value
        self.dim_opacity_label.setText(f"{value}%")

    def _build_plugins_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        if self.plugin_manager is None:
            layout.addWidget(QLabel("Keine Plugins verfügbar."))
            return w

        self._plugin_list = QListWidget()
        layout.addWidget(self._plugin_list, 1)

        btns = QHBoxLayout()
        self._plugin_enable_btn = QPushButton("Aktivieren")
        self._plugin_disable_btn = QPushButton("Deaktivieren")
        self._plugin_reload_btn = QPushButton("Neu laden")
        self._plugin_settings_btn = QPushButton("Einstellungen")
        self._plugin_enable_btn.clicked.connect(self._enable_selected_plugin)
        self._plugin_disable_btn.clicked.connect(self._disable_selected_plugin)
        self._plugin_reload_btn.clicked.connect(self._reload_selected_plugin)
        self._plugin_settings_btn.clicked.connect(self._open_selected_plugin_settings)
        for b in (
            self._plugin_enable_btn,
            self._plugin_disable_btn,
            self._plugin_reload_btn,
            self._plugin_settings_btn,
        ):
            btns.addWidget(b)
        layout.addLayout(btns)

        self._refresh_plugin_list()
        return w

    def _refresh_plugin_list(self) -> None:
        if self.plugin_manager is None:
            return
        self._plugin_list.clear()
        for info in self.plugin_manager.list_plugins():
            text = f"{info.name} v{info.version} [{info.state}]"
            if info.error:
                text += f" \u2014 {info.error}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, info.id)
            self._plugin_list.addItem(item)

    def _selected_plugin_id(self):
        item = self._plugin_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _enable_selected_plugin(self) -> None:
        pid = self._selected_plugin_id()
        if pid:
            self.plugin_manager.enable(pid)
            self._refresh_plugin_list()

    def _disable_selected_plugin(self) -> None:
        pid = self._selected_plugin_id()
        if pid:
            self.plugin_manager.disable(pid)
            self._refresh_plugin_list()

    def _reload_selected_plugin(self) -> None:
        pid = self._selected_plugin_id()
        if pid:
            self.plugin_manager.reload(pid)
            self._refresh_plugin_list()

    def _open_selected_plugin_settings(self) -> None:
        plugin_id = self._selected_plugin_id()
        if not plugin_id:
            return
        plugin = self.plugin_manager.get_instance(plugin_id)
        if plugin is None:
            QMessageBox.warning(self, "Plugin-Einstellungen", "Das Plugin muss aktiviert sein.")
            return

        schema = getattr(plugin, "settings_schema", [])
        if not schema:
            QMessageBox.information(self, "Plugin-Einstellungen", "Dieses Plugin hat keine Einstellungen.")
            return

        try:
            for definition in schema:
                definition.validate()
        except (AttributeError, ValueError) as exc:
            QMessageBox.warning(self, "Plugin-Einstellungen", f"Ungültiges Einstellungs-Schema: {exc}")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"{plugin.manifest.name} - Einstellungen")
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        fields = {}
        for definition in schema:
            value = plugin.settings.get(definition.key, definition.default)
            if definition.field_type == "bool":
                field = QCheckBox()
                field.setChecked(bool(value))
            elif definition.field_type == "number":
                field = QDoubleSpinBox()
                field.setRange(-999999.0, 999999.0)
                field.setDecimals(3)
                field.setValue(float(value or 0))
            elif definition.field_type == "select":
                field = QComboBox()
                field.addItems(definition.options)
                field.setCurrentText(str(value if value is not None else definition.default))
            else:
                field = QLineEdit(str(value if value is not None else ""))
            fields[definition.key] = field
            form.addRow(definition.label, field)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(lambda: self._save_plugin_settings(plugin, schema, fields, dialog))
        layout.addWidget(buttons)
        dialog.exec()

    @staticmethod
    def _save_plugin_settings(plugin, schema, fields, dialog: QDialog) -> None:
        for definition in schema:
            field = fields[definition.key]
            if definition.field_type == "bool":
                value = field.isChecked()
            elif definition.field_type == "number":
                value = field.value()
            elif definition.field_type == "select":
                value = field.currentText()
            else:
                value = field.text().strip()
            plugin.settings.set(definition.key, value)
        dialog.accept()

    def _build_ha_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        form = QFormLayout()
        self.url_edit = QLineEdit(self.settings.ha_url)
        self.token_edit = QLineEdit(self.settings.ha_token)
        self.token_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Adresse", self.url_edit)
        form.addRow("Access Token", self.token_edit)
        v.addLayout(form)

        self.demo_check = QCheckBox("Demo-Modus (ohne Home Assistant)")
        self.demo_check.setChecked(self.settings.demo_mode)
        v.addWidget(self.demo_check)

        row = QHBoxLayout()
        test_btn = QPushButton("Verbindung testen")
        test_btn.clicked.connect(self._test_connection)
        self.status_label = QLabel("")
        row.addWidget(test_btn)
        row.addWidget(self.status_label, 1)
        v.addLayout(row)

        save_btn = QPushButton("Speichern (Neustart erforderlich)")
        save_btn.clicked.connect(self._save_ha)
        v.addWidget(save_btn)
        v.addStretch()
        return w

    def _build_theme_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Theme auswählen"))
        row = QHBoxLayout()
        for theme in self.theme_manager.all_themes():
            btn = QPushButton(theme.name)
            btn.clicked.connect(lambda checked=False, t=theme: self._apply_theme(t))
            row.addWidget(btn)
        v.addLayout(row)

        edit_theme_btn = QPushButton("Theme bearbeiten")
        edit_theme_btn.clicked.connect(self._edit_theme)
        v.addWidget(edit_theme_btn)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Modus"))
        mode_combo = QComboBox()
        mode_combo.addItems(["dark", "light", "auto"])
        mode_combo.setCurrentText(self.settings.theme_mode)
        mode_combo.currentTextChanged.connect(lambda t: setattr(self.settings, "theme_mode", t))
        mode_row.addWidget(mode_combo)
        v.addLayout(mode_row)
        v.addStretch()
        return w

    def _edit_theme(self) -> None:
        config = dict(self.theme_manager.active())
        dialog = QDialog(self)
        dialog.setWindowTitle("Theme bearbeiten")
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        name = QLineEdit(config.get("name", "Mein Theme"))
        form.addRow("Name", name)

        mode = QComboBox()
        mode.addItems(["dark", "light"])
        mode.setCurrentText(config.get("mode", "dark"))
        form.addRow("Modus", mode)

        color_fields = {}
        for key, label in (
            ("background", "Hintergrund"),
            ("surface", "Fläche"),
            ("primary", "Primärfarbe"),
            ("secondary", "Sekundärfarbe"),
            ("accent", "Akzentfarbe"),
            ("text", "Textfarbe"),
            ("text_secondary", "Sekundärtext"),
        ):
            button = QPushButton(config.get(key, "#FFFFFF"))
            button.setStyleSheet(f"background-color: {button.text()};")

            def choose_color(_checked=False, field=button):
                color = QColorDialog.getColor(QColor(field.text()), dialog)
                if color.isValid():
                    field.setText(color.name())
                    field.setStyleSheet(f"background-color: {color.name()};")

            button.clicked.connect(choose_color)
            color_fields[key] = button
            form.addRow(label, button)

        numeric_fields = {}
        for key, label, minimum, maximum in (
            ("card_radius", "Eckenradius", 0, 60),
            ("card_opacity", "Flächen-Transparenz", 10, 100),
            ("font_size_base", "Schriftgröße", 8, 32),
            ("spacing", "Abstand", 0, 40),
        ):
            field = QSpinBox()
            field.setRange(minimum, maximum)
            field.setValue(int(config.get(key, minimum)))
            numeric_fields[key] = field
            form.addRow(label, field)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.rejected.connect(dialog.reject)

        def save_theme() -> None:
            updated = dict(config)
            updated["name"] = name.text().strip() or "Mein Theme"
            updated["mode"] = mode.currentText()
            updated.update({key: field.text() for key, field in color_fields.items()})
            updated.update({key: field.value() for key, field in numeric_fields.items()})
            self.theme_manager.save_custom(updated["name"], updated, set_active=True)
            self.theme_manager.apply(self.app, updated)
            if self.on_theme_applied:
                self.on_theme_applied()
            dialog.accept()

        buttons.accepted.connect(save_theme)
        layout.addWidget(buttons)
        dialog.exec()

    def _build_security_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.pin_edit = QLineEdit(self.settings.edit_pin or "")
        self.pin_edit.setPlaceholderText("Leer lassen = kein PIN-Schutz")
        self.pin_edit.setEchoMode(QLineEdit.Password)
        save_btn = QPushButton("PIN speichern")
        save_btn.clicked.connect(lambda: setattr(self.settings, "edit_pin", self.pin_edit.text().strip() or None))
        form.addRow("Editor-PIN", self.pin_edit)
        form.addRow("", save_btn)
        return w

    def _build_backup_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        backup_btn = QPushButton("Backup erstellen")
        backup_btn.clicked.connect(self._create_backup)
        restore_btn = QPushButton("Backup wiederherstellen")
        restore_btn.clicked.connect(self._restore_backup)
        export_btn = QPushButton("Konfiguration exportieren")
        export_btn.clicked.connect(self._export_config)
        import_btn = QPushButton("Konfiguration importieren")
        import_btn.clicked.connect(self._import_config)
        for b in (backup_btn, restore_btn, export_btn, import_btn):
            v.addWidget(b)
        v.addStretch()
        return w

    # ------------------------------------------------------------------ #
    def _test_connection(self) -> None:
        client = HomeAssistantClient(self.url_edit.text().strip(), self.token_edit.text().strip())
        ok, msg = client.test_connection()
        self.status_label.setText("\u2705 Verbunden" if ok else f"\u274C {msg}")

    def _save_ha(self) -> None:
        self.settings.ha_url = self.url_edit.text().strip()
        self.settings.ha_token = self.token_edit.text().strip()
        self.settings.demo_mode = self.demo_check.isChecked()
        QMessageBox.information(self, "Gespeichert", "Bitte HomePanel neu starten, damit die Änderungen wirksam werden.")

    def _apply_theme(self, theme) -> None:
        self.theme_manager.set_active(theme.id)
        self.theme_manager.apply(self.app, theme.config)
        if self.on_theme_applied:
            self.on_theme_applied()

    def _create_backup(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Backup speichern", "homepanel-backup.db", "SQLite (*.db)")
        if path:
            self.db.backup_to_file(Path(path))
            QMessageBox.information(self, "Backup", "Backup wurde erstellt.")

    def _restore_backup(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Backup auswählen", "", "SQLite (*.db)")
        if path:
            confirm = QMessageBox.question(self, "Wiederherstellen?", "Aktuelle Konfiguration wird überschrieben. Fortfahren?")
            if confirm == QMessageBox.Yes:
                self.db.restore_from_file(Path(path))
                QMessageBox.information(self, "Wiederhergestellt", "Bitte HomePanel neu starten.")

    def _export_config(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Konfiguration exportieren", "homepanel-config.json", "JSON (*.json)")
        if path:
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.db.export_config(), f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Export", "Konfiguration wurde exportiert.")

    def _import_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Konfiguration importieren", "", "JSON (*.json)")
        if path:
            import json
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            confirm = QMessageBox.question(self, "Importieren?", "Aktuelle Seiten/Widgets werden ersetzt. Fortfahren?")
            if confirm == QMessageBox.Yes:
                self.db.import_config(data, replace=True)
                QMessageBox.information(self, "Import", "Konfiguration wurde importiert. Bitte neu starten.")
