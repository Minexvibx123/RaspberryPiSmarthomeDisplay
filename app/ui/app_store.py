"""App-Store: browse, install and remove bundled apps, plugins and apps from GitHub repositories."""
from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from app.apps.catalog import CATEGORIES, AppCatalog
from app.apps.kit import card
from app.plugins import installer
from app.widgets.icons import IconGlyph

_DOWNLOADS: set[QThread] = set()
SOURCE_LABEL = {"builtin": "Mitgeliefert", "plugin": "Plugin", "repo": "Aus Repository"}


class _Download(QThread):
    done, failed = Signal(bytes), Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self) -> None:
        try:
            self.done.emit(installer.download_archive(self.url))
        except installer.InstallError as exc:
            self.failed.emit(str(exc))


class AppStore(QWidget):
    exit_requested = Signal()

    def __init__(self, catalog: AppCatalog, parent=None):
        super().__init__(parent)
        self.catalog = catalog
        self.plugins_root = catalog.plugin_manager.plugins_root
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        back = QPushButton("\u2190 Zurück zu Apps")
        back.clicked.connect(self.exit_requested.emit)
        title = QLabel("App-Store")
        title.setStyleSheet("font-size: 26px; font-weight: 800;")
        self.repo_button = QPushButton("Aus Repository …")
        self.repo_button.clicked.connect(self.ask_repository)
        top.addWidget(back)
        top.addWidget(title, 1, Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self.repo_button)
        root.addLayout(top)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Apps suchen")
        self.category = QComboBox()
        self.category.addItems(["Alle"] + CATEGORIES)
        self.search.textChanged.connect(self.refresh)
        self.category.currentTextChanged.connect(self.refresh)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.category)
        root.addLayout(filters)
        self.status = QLabel()
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        root.addWidget(self.scroll, 1)
        catalog.changed.connect(self.refresh)
        self.refresh()

    def refresh(self, *_args) -> None:
        query = self.search.text().strip().casefold()
        category = self.category.currentText()
        container = QWidget()
        layout = QVBoxLayout(container)
        shown = 0
        for entry in self.catalog.entries():
            haystack = f"{entry.name} {entry.description} {entry.author} {entry.id}".casefold()
            if (query and query not in haystack) or (category != "Alle" and entry.category != category):
                continue
            layout.addWidget(self._row(entry))
            shown += 1
        if not shown:
            layout.addWidget(QLabel("Keine Apps gefunden."))
        layout.addStretch(1)
        self.scroll.setWidget(container)

    def _row(self, entry) -> QWidget:
        frame, outer = card()
        row = QHBoxLayout()
        glyph = IconGlyph(entry.icon, "#FFFFFF")
        glyph.setFixedSize(40, 40)
        details = QVBoxLayout()
        name = QLabel(entry.name)
        name.setStyleSheet("font-size: 17px; font-weight: 800;")
        description = QLabel(entry.description or "Keine Beschreibung.")
        description.setWordWrap(True)
        meta = QLabel(f"{entry.category} · v{entry.version} · {entry.author} · {SOURCE_LABEL[entry.source]}"
                      + (" · installiert" if entry.installed else ""))
        meta.setStyleSheet("font-size: 12px;")
        details.addWidget(name)
        details.addWidget(description)
        details.addWidget(meta)
        if entry.error:
            error = QLabel(entry.error)
            error.setWordWrap(True)
            error.setStyleSheet("color: #E5645A; font-size: 12px;")
            details.addWidget(error)
        row.addWidget(glyph)
        row.addLayout(details, 1)
        buttons = QVBoxLayout()
        if entry.installed:
            action = QPushButton("Neu laden" if entry.error else "Entfernen")
        else:
            action = QPushButton("Installieren")
            action.setProperty("variant", "primary")
        action.setMinimumWidth(130)
        action.clicked.connect(lambda _c=False, e=entry: self.toggle(e))
        buttons.addWidget(action)
        if entry.removable:
            delete = QPushButton("Löschen")
            delete.setProperty("variant", "danger")
            delete.clicked.connect(lambda _c=False, e=entry: self.delete(e))
            buttons.addWidget(delete)
        row.addLayout(buttons)
        outer.addLayout(row)
        return frame

    def toggle(self, entry) -> None:
        if entry.installed and not entry.error:
            self.catalog.remove(entry.id)
            return
        if entry.source == "repo" and not entry.installed and not self.confirm_code(entry.name):
            return
        if entry.installed:
            self.catalog.plugin_manager.reload(entry.id)
            self.catalog.changed.emit()
        elif not self.catalog.install(entry.id):
            QMessageBox.warning(self, "App-Store", "Die App konnte nicht geladen werden. Details stehen im Eintrag.")

    def confirm_code(self, name: str) -> bool:
        answer = QMessageBox.warning(
            self, "Code aus fremder Quelle",
            f"„{name}“ besteht aus Python-Code, der mit allen Rechten von HomePanel läuft "
            "(Zugriff auf Home-Assistant-Token, Dateien und Netzwerk).\n\nAktiviere nur Apps, "
            "deren Quelle du vertraust. Jetzt aktivieren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        return answer == QMessageBox.StandardButton.Yes

    def delete(self, entry) -> None:
        answer = QMessageBox.question(self, "App löschen", f"„{entry.name}“ endgültig löschen?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        manager = self.catalog.plugin_manager
        info = next((i for i in manager.list_plugins() if i.id == entry.id), None)
        manager.disable(entry.id)
        try:
            if info:
                installer.uninstall(info.plugin_dir, self.plugins_root)
        except installer.InstallError as exc:
            QMessageBox.warning(self, "App-Store", str(exc))
        self.catalog.changed.emit()

    def ask_repository(self) -> None:
        url, accepted = QInputDialog.getText(
            self, "Aus Repository installieren",
            "GitHub-Adresse (z. B. https://github.com/benutzer/repo oder …/tree/branch):")
        if accepted and url.strip():
            self.download_repository(url.strip())

    def download_repository(self, url: str) -> None:
        try:
            installer.parse_repo_url(url)
        except installer.InstallError as exc:
            QMessageBox.warning(self, "App-Store", str(exc))
            return
        self.repo_button.setEnabled(False)
        self.status.setText("Lade Repository …")
        job = _Download(url)
        _DOWNLOADS.add(job)
        job.done.connect(lambda data, u=url: self.review_archive(data, u))
        job.failed.connect(self.repository_failed)
        job.finished.connect(lambda j=job: _DOWNLOADS.discard(j))
        job.start()

    def repository_failed(self, message: str) -> None:
        self.repo_button.setEnabled(True)
        self.status.setText("")
        QMessageBox.warning(self, "App-Store", message)

    def review_archive(self, data: bytes, url: str) -> None:
        self.repo_button.setEnabled(True)
        self.status.setText("")
        try:
            found = installer.inspect_archive(data)
        except installer.InstallError as exc:
            QMessageBox.warning(self, "App-Store", str(exc))
            return
        listing = "\n".join(f"• {p['name']} {p['version']} ({p['id']})" for p in found)
        answer = QMessageBox.question(
            self, "Apps installieren?",
            f"Quelle: {url}\n\nGefunden:\n{listing}\n\nDie Apps werden nur heruntergeladen und bleiben "
            "deaktiviert, bis du sie im Store aktivierst.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.install_archive(data, [p["id"] for p in found], url)

    def install_archive(self, data: bytes, plugin_ids: list[str], source: str) -> list[str]:
        try:
            installed = installer.install_archive(data, self.plugins_root, plugin_ids, source)
        except installer.InstallError as exc:
            QMessageBox.warning(self, "App-Store", str(exc))
            return []
        for plugin_id in installed:
            self.catalog.db.set_setting(f"plugin.enabled.{plugin_id}", False)
        self.catalog.changed.emit()
        self.status.setText(f"Installiert: {', '.join(installed)} – noch deaktiviert.")
        return installed
