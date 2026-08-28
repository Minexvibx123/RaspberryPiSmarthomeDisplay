"""First-run welcome wizard - language, Home Assistant connection, first layout."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from app.core.homeassistant import HomeAssistantClient


class SetupWizard(QWidget):
    finished = Signal(dict)  # {"language":..., "ha_url":..., "ha_token":..., "demo_mode": bool}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result_data: dict = {"language": "de", "ha_url": "", "ha_token": "", "demo_mode": False}

        root = QVBoxLayout(self)
        root.setContentsMargins(60, 60, 60, 60)
        header = QLabel("Willkommen bei HomePanel")
        header.setStyleSheet("font-size: 28px; font-weight: 800;")
        root.addWidget(header)
        sub = QLabel("Richte dein Touchpanel in wenigen Schritten ein.")
        sub.setStyleSheet("font-size: 15px; color: #9AA1B4;")
        root.addWidget(sub)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.stack.addWidget(self._build_language_step())
        self.stack.addWidget(self._build_connection_step())
        self.stack.addWidget(self._build_summary_step())

        nav = QHBoxLayout()
        self.back_btn = QPushButton("Zurück")
        self.back_btn.clicked.connect(self._go_back)
        self.next_btn = QPushButton("Weiter")
        self.next_btn.clicked.connect(self._go_next)
        nav.addWidget(self.back_btn)
        nav.addStretch()
        nav.addWidget(self.next_btn)
        root.addLayout(nav)

    # -- steps -------------------------------------------------------------- #
    def _build_language_step(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("1. Sprache auswählen"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Deutsch", "English"])
        v.addWidget(self.lang_combo)
        v.addStretch()
        return w

    def _build_connection_step(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("2. Home Assistant verbinden"))
        v.addWidget(QLabel("Adresse (z. B. http://homeassistant.local:8123)"))
        self.url_edit = QLineEdit()
        v.addWidget(self.url_edit)
        v.addWidget(QLabel("Long-Lived Access Token"))
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.Password)
        v.addWidget(self.token_edit)

        row = QHBoxLayout()
        self.test_btn = QPushButton("Verbindung testen")
        self.test_btn.clicked.connect(self._test_connection)
        self.status_label = QLabel("")
        row.addWidget(self.test_btn)
        row.addWidget(self.status_label, 1)
        v.addLayout(row)

        self.demo_btn = QPushButton("Ohne Home Assistant fortfahren (Demo-Modus)")
        self.demo_btn.clicked.connect(self._use_demo)
        v.addWidget(self.demo_btn)
        v.addStretch()
        return w

    def _build_summary_step(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("3. Fertig!"))
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        v.addWidget(self.summary_label)
        v.addStretch()
        return w

    # -- logic --------------------------------------------------------------- #
    def _test_connection(self) -> None:
        url = self.url_edit.text().strip()
        token = self.token_edit.text().strip()
        if not url or not token:
            self.status_label.setText("Bitte Adresse und Token eingeben")
            return
        client = HomeAssistantClient(url, token)
        ok, msg = client.test_connection()
        self.status_label.setText("\u2705 Verbunden" if ok else f"\u274C {msg}")
        if ok:
            self.result_data.update(ha_url=url, ha_token=token, demo_mode=False)

    def _use_demo(self) -> None:
        self.result_data.update(ha_url="", ha_token="", demo_mode=True)
        self._go_next()

    def _go_next(self) -> None:
        idx = self.stack.currentIndex()
        if idx == 0:
            self.result_data["language"] = "de" if self.lang_combo.currentText() == "Deutsch" else "en"
        elif idx == 1:
            if not self.result_data.get("demo_mode") and not self.result_data.get("ha_url"):
                url = self.url_edit.text().strip()
                token = self.token_edit.text().strip()
                if url and token:
                    self.result_data.update(ha_url=url, ha_token=token)
                else:
                    QMessageBox.information(self, "Hinweis", "Bitte Verbindung testen oder Demo-Modus wählen.")
                    return
        if idx == self.stack.count() - 1:
            self.summary_label.setText(
                "Konfiguration abgeschlossen. Das Panel startet jetzt mit einer Startseite, "
                "die du im Editor-Modus vollständig anpassen kannst."
            )
            self.finished.emit(self.result_data)
            return
        self.summary_label.setText(
            f"Sprache: {self.lang_combo.currentText()}\n"
            f"Modus: {'Demo' if self.result_data.get('demo_mode') else 'Home Assistant'}"
        )
        self.stack.setCurrentIndex(idx + 1)

    def _go_back(self) -> None:
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
