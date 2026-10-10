"""Offline tool apps: calculator, notes, timers, calendar, converter and more."""
from __future__ import annotations

import ast
import json
import operator
import random
from datetime import datetime, date
from pathlib import Path

from PySide6.QtCore import QDate, QPointF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QTextCharFormat
from PySide6.QtWidgets import (
    QApplication, QCalendarWidget, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QProgressBar, QPushButton, QSlider,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from app.apps.kit import AppContext, AppPage, big_button, card
from app.ui import design

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}


def calculate(expression: str) -> float:
    """Evaluate plain arithmetic safely (no names, calls or attributes)."""
    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError("Exponent zu groß")
            return _OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = walk(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        raise ValueError("Ungültiger Ausdruck")
    cleaned = expression.replace("×", "*").replace("÷", "/").replace(",", ".").replace("^", "**")
    return walk(ast.parse(cleaned, mode="eval"))


def format_number(value: float) -> str:
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.10g}".replace(".", ",")


def calculator(ctx: AppContext) -> QWidget:
    page = AppPage("Rechner")
    display = QLineEdit()
    display.setReadOnly(True)
    display.setAlignment(Qt.AlignmentFlag.AlignRight)
    display.setStyleSheet("font-size: 34px; font-weight: 700; min-height: 64px;")
    page.root.addWidget(display)
    grid = QGridLayout()
    grid.setSpacing(8)

    def press(key: str) -> None:
        if key == "C":
            display.clear()
        elif key == "⌫":
            display.setText(display.text()[:-1])
        elif key == "=":
            try:
                display.setText(format_number(calculate(display.text())))
            except (ValueError, SyntaxError, ZeroDivisionError, OverflowError):
                display.setText("Fehler")
        else:
            display.setText("" if display.text() == "Fehler" else display.text())
            display.setText(display.text() + key)

    keys = ["C", "(", ")", "÷", "7", "8", "9", "×", "4", "5", "6", "-", "1", "2", "3", "+", "0", ",", "⌫", "="]
    for index, key in enumerate(keys):
        variant = "primary" if key == "=" else ""
        button = big_button(key, lambda k=key: press(k), variant)
        button.setMinimumHeight(60)
        grid.addWidget(button, index // 4, index % 4)
    page.root.addLayout(grid, 1)
    return page


def notes(ctx: AppContext) -> QWidget:
    page = AppPage("Notizen")
    editor = QPlainTextEdit(ctx.load("text", ""))
    editor.setPlaceholderText("Notizen für die ganze Familie …")
    page.root.addWidget(editor, 1)
    timer = QTimer(page)
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: ctx.save("text", editor.toPlainText()))
    editor.textChanged.connect(lambda: timer.start(600))
    return page


class _Clock(QLabel):
    """Large monospace time label."""

    def __init__(self, size: int = 64):
        super().__init__("00:00.0")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"font-size: {size}px; font-weight: 800; font-family: 'DejaVu Sans Mono', monospace;")


def _clock_text(seconds: float, tenths: bool = False) -> str:
    seconds = max(0.0, seconds)
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    base = f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"
    return base + (f".{int((seconds % 1) * 10)}" if tenths else "")


def stopwatch_timer(ctx: AppContext) -> QWidget:
    page = AppPage("Timer & Stoppuhr")
    tabs = QTabWidget()
    page.root.addWidget(tabs, 1)

    watch = QWidget()
    watch_layout = QVBoxLayout(watch)
    watch_label, laps = _Clock(), QListWidget()
    state = {"start": 0.0, "elapsed": 0.0, "running": False}
    ticker = QTimer(watch)
    ticker.setInterval(100)

    def elapsed() -> float:
        return state["elapsed"] + (datetime.now().timestamp() - state["start"] if state["running"] else 0.0)

    ticker.timeout.connect(lambda: watch_label.setText(_clock_text(elapsed(), True)))

    def toggle() -> None:
        if state["running"]:
            state["elapsed"], state["running"] = elapsed(), False
            ticker.stop()
            start_button.setText("Weiter")
        else:
            state["start"], state["running"] = datetime.now().timestamp(), True
            ticker.start()
            start_button.setText("Stopp")

    def lap() -> None:
        if state["running"]:
            laps.insertItem(0, f"Runde {laps.count() + 1}   {_clock_text(elapsed(), True)}")

    def reset() -> None:
        state.update(start=0.0, elapsed=0.0, running=False)
        ticker.stop()
        watch_label.setText("00:00.0")
        start_button.setText("Start")
        laps.clear()

    start_button = big_button("Start", toggle, "primary")
    row = QHBoxLayout()
    for widget in (start_button, big_button("Runde", lap), big_button("Zurücksetzen", reset)):
        row.addWidget(widget)
    watch_layout.addWidget(watch_label)
    watch_layout.addLayout(row)
    watch_layout.addWidget(laps, 1)
    tabs.addTab(watch, "Stoppuhr")

    countdown = QWidget()
    count_layout = QVBoxLayout(countdown)
    count_label = _Clock()
    count_label.setText("05:00")
    status = {"left": 300.0, "end": 0.0, "running": False}
    count_ticker = QTimer(countdown)
    count_ticker.setInterval(200)

    def remaining() -> float:
        return status["end"] - datetime.now().timestamp() if status["running"] else status["left"]

    def tick() -> None:
        left = remaining()
        count_label.setText(_clock_text(left + 0.99))
        if left <= 0:
            status.update(running=False, left=0.0)
            count_ticker.stop()
            count_label.setText("Abgelaufen!")
            count_label.setStyleSheet(count_label.styleSheet() + f"color: {design._ACTIVE['accent']};")
            QApplication.beep()

    count_ticker.timeout.connect(tick)

    def set_minutes(minutes: float) -> None:
        status.update(left=minutes * 60, running=False)
        count_ticker.stop()
        count_label.setStyleSheet(count_label.styleSheet().split("color:")[0])
        count_label.setText(_clock_text(status["left"]))
        count_start.setText("Start")

    def add_minute() -> None:
        status["left"] = remaining() + 60
        if status["running"]:
            status["end"] += 60
        count_label.setText(_clock_text(status["left"] if not status["running"] else remaining() + 0.99))

    def count_toggle() -> None:
        if status["running"]:
            status.update(left=remaining(), running=False)
            count_ticker.stop()
            count_start.setText("Weiter")
        elif status["left"] > 0:
            status.update(end=datetime.now().timestamp() + status["left"], running=True)
            count_ticker.start()
            count_start.setText("Pause")

    presets = QHBoxLayout()
    for minutes in (1, 3, 5, 10, 15, 30):
        presets.addWidget(big_button(f"{minutes} min", lambda m=minutes: set_minutes(m)))
    count_start = big_button("Start", count_toggle, "primary")
    controls = QHBoxLayout()
    for widget in (count_start, big_button("+1 min", add_minute), big_button("Zurücksetzen", lambda: set_minutes(5))):
        controls.addWidget(widget)
    count_layout.addWidget(count_label, 1)
    count_layout.addLayout(presets)
    count_layout.addLayout(controls)
    tabs.addTab(countdown, "Timer")
    return page


def world_clock(ctx: AppContext) -> QWidget:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    page = AppPage("Weltuhr")
    zones = [("Berlin", "Europe/Berlin"), ("London", "Europe/London"), ("New York", "America/New_York"),
             ("Los Angeles", "America/Los_Angeles"), ("São Paulo", "America/Sao_Paulo"), ("Dubai", "Asia/Dubai"),
             ("Mumbai", "Asia/Kolkata"), ("Singapur", "Asia/Singapore"), ("Tokio", "Asia/Tokyo"),
             ("Sydney", "Australia/Sydney")]
    grid = QGridLayout()
    labels = []
    for index, (name, key) in enumerate(zones):
        try:
            zone = ZoneInfo(key)
        except ZoneInfoNotFoundError:
            continue
        frame, layout = card()
        title, clock = QLabel(name), QLabel()
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        clock.setStyleSheet("font-size: 34px; font-weight: 800;")
        layout.addWidget(title)
        layout.addWidget(clock)
        grid.addWidget(frame, len(labels) // 2, len(labels) % 2)
        labels.append((clock, zone))
    page.root.addLayout(grid, 1)
    if not labels:
        page.root.addWidget(QLabel("Zeitzonendaten sind nicht installiert (Paket tzdata)."))
    timer = QTimer(page)
    timer.timeout.connect(lambda: [c.setText(datetime.now(z).strftime("%H:%M   %a %d.%m.")) for c, z in labels])
    timer.start(1000)
    timer.timeout.emit()
    return page


def calendar_app(ctx: AppContext) -> QWidget:
    page = AppPage("Kalender")
    row = QHBoxLayout()
    calendar = QCalendarWidget()
    calendar.setGridVisible(True)
    calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
    data: dict = ctx.load("notes", {})
    editor = QPlainTextEdit()
    editor.setPlaceholderText("Notiz zu diesem Tag …")
    heading = QLabel()
    heading.setStyleSheet("font-size: 18px; font-weight: 700;")
    current = {"key": ""}

    def mark() -> None:
        for iso, text in data.items():
            fmt = QTextCharFormat()
            fmt.setFontWeight(900 if text.strip() else 400)
            fmt.setForeground(QColor(design._ACTIVE["accent"] if text.strip() else design._ACTIVE["text"]))
            parsed = date.fromisoformat(iso)
            calendar.setDateTextFormat(QDate(parsed.year, parsed.month, parsed.day), fmt)

    def save() -> None:
        if current["key"]:
            data[current["key"]] = editor.toPlainText()
            ctx.save("notes", {k: v for k, v in data.items() if v.strip()})
            mark()

    def select_day() -> None:
        selected = calendar.selectedDate()
        current["key"] = date(selected.year(), selected.month(), selected.day()).isoformat()
        heading.setText(selected.toString("dddd, d. MMMM yyyy"))
        editor.blockSignals(True)
        editor.setPlainText(data.get(current["key"], ""))
        editor.blockSignals(False)

    calendar.selectionChanged.connect(select_day)
    editor.textChanged.connect(save)
    side = QVBoxLayout()
    side.addWidget(heading)
    side.addWidget(editor, 1)
    row.addWidget(calendar, 3)
    row.addLayout(side, 2)
    page.root.addLayout(row, 1)
    select_day()
    mark()
    return page


_UNITS = {
    "Länge": {"mm": 0.001, "cm": 0.01, "m": 1, "km": 1000, "Zoll": 0.0254, "Fuß": 0.3048, "Meile": 1609.344},
    "Gewicht": {"g": 0.001, "kg": 1, "t": 1000, "Unze": 0.0283495, "Pfund": 0.453592},
    "Volumen": {"ml": 0.001, "l": 1, "m³": 1000, "Tasse": 0.2366, "Gallone (US)": 3.78541},
    "Geschwindigkeit": {"km/h": 1, "m/s": 3.6, "mph": 1.609344, "Knoten": 1.852},
    "Fläche": {"cm²": 0.0001, "m²": 1, "ha": 10000, "km²": 1e6, "Acre": 4046.856},
    "Temperatur": {"°C": 0, "°F": 0, "K": 0},
}


def convert(category: str, source: str, target: str, value: float) -> float:
    if category == "Temperatur":
        celsius = {"°C": value, "°F": (value - 32) * 5 / 9, "K": value - 273.15}[source]
        return {"°C": celsius, "°F": celsius * 9 / 5 + 32, "K": celsius + 273.15}[target]
    return value * _UNITS[category][source] / _UNITS[category][target]


def unit_converter(ctx: AppContext) -> QWidget:
    page = AppPage("Umrechner")
    category, source, target, value, result = QComboBox(), QComboBox(), QComboBox(), QLineEdit("1"), QLabel()
    result.setStyleSheet("font-size: 38px; font-weight: 800;")
    result.setAlignment(Qt.AlignmentFlag.AlignCenter)
    category.addItems(list(_UNITS))

    def fill() -> None:
        for box in (source, target):
            box.blockSignals(True)
            box.clear()
            box.addItems(list(_UNITS[category.currentText()]))
            box.blockSignals(False)
        target.setCurrentIndex(min(1, target.count() - 1))
        update()

    def update() -> None:
        try:
            amount = float(value.text().replace(",", "."))
            result.setText(f"{format_number(convert(category.currentText(), source.currentText(), target.currentText(), amount))} {target.currentText()}")
        except (ValueError, KeyError):
            result.setText("–")

    category.currentTextChanged.connect(fill)
    for widget in (source, target):
        widget.currentTextChanged.connect(update)
    value.textChanged.connect(update)
    for label, widget in (("Größe", category), ("Wert", value), ("Von", source), ("Nach", target)):
        page.root.addWidget(QLabel(label))
        page.root.addWidget(widget)
    page.root.addWidget(result, 1)
    fill()
    return page


def dice(ctx: AppContext) -> QWidget:
    page = AppPage("Würfel & Zufall")
    out = QLabel("Würfeln?")
    out.setAlignment(Qt.AlignmentFlag.AlignCenter)
    out.setWordWrap(True)
    out.setStyleSheet("font-size: 44px; font-weight: 800;")
    count = QSpinBox()
    count.setRange(1, 10)
    count.setPrefix("Anzahl: ")

    def roll(sides: int) -> None:
        rolls = [random.randint(1, sides) for _ in range(count.value())]
        out.setText(f"{' + '.join(map(str, rolls))} = {sum(rolls)}" if len(rolls) > 1 else str(rolls[0]))

    row = QHBoxLayout()
    for sides in (4, 6, 8, 10, 12, 20, 100):
        row.addWidget(big_button(f"W{sides}", lambda s=sides: roll(s)))
    other = QHBoxLayout()
    other.addWidget(big_button("Münze", lambda: out.setText(random.choice(["Kopf", "Zahl"]))))
    other.addWidget(big_button("Ja / Nein", lambda: out.setText(random.choice(["Ja", "Nein"]))))
    other.addWidget(big_button("Wer fängt an?", lambda: out.setText(f"Spieler {random.randint(1, count.value() + 1)}")))
    page.root.addWidget(count)
    page.root.addLayout(row)
    page.root.addLayout(other)
    page.root.addWidget(out, 1)
    return page


class _Canvas(QWidget):
    def __init__(self):
        super().__init__()
        self.strokes: list[tuple[QPainterPath, QColor, float]] = []
        self.color, self.width, self._path = QColor(design._ACTIVE["text"]), 6.0, None
        self.setMinimumHeight(260)

    def mousePressEvent(self, event) -> None:
        self._path = QPainterPath(QPointF(event.position()))
        self.strokes.append((self._path, QColor(self.color), self.width))

    def mouseMoveEvent(self, event) -> None:
        if self._path is not None:
            self._path.lineTo(QPointF(event.position()))
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        self._path = None

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(design._ACTIVE["surface"]))
        for path, color, width in self.strokes:
            painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(path)
        painter.end()


def paint(ctx: AppContext) -> QWidget:
    page = AppPage("Zeichenbrett")
    canvas = _Canvas()
    palette = QHBoxLayout()
    for name, color in (("Text", design._ACTIVE["text"]), ("Rot", "#E5484D"), ("Orange", "#F5A524"),
                        ("Grün", "#30A46C"), ("Blau", "#3E8BFF"), ("Lila", "#8E4EC6")):
        button = QPushButton(name)
        button.clicked.connect(lambda _c=False, c=color: setattr(canvas, "color", QColor(c)))
        palette.addWidget(button)
    palette.addWidget(big_button("Radierer", lambda: setattr(canvas, "color", QColor(design._ACTIVE["surface"]))))
    width = QSlider(Qt.Orientation.Horizontal)
    width.setRange(2, 36)
    width.setValue(6)
    width.valueChanged.connect(lambda v: setattr(canvas, "width", float(v)))
    actions = QHBoxLayout()
    actions.addWidget(big_button("Rückgängig", lambda: (canvas.strokes.pop() if canvas.strokes else None, canvas.update())))
    actions.addWidget(big_button("Alles löschen", lambda: (canvas.strokes.clear(), canvas.update())))
    page.root.addLayout(palette)
    page.root.addWidget(width)
    page.root.addWidget(canvas, 1)
    page.root.addLayout(actions)
    return page


def lists(ctx: AppContext) -> QWidget:
    page = AppPage("Listen")
    tabs = QTabWidget()
    data: dict = ctx.load("lists", {"Einkaufen": [], "Aufgaben": []})
    widgets: dict[str, QListWidget] = {}

    def save() -> None:
        ctx.save("lists", {name: [[box.item(i).text(), box.item(i).checkState() == Qt.CheckState.Checked]
                                  for i in range(box.count())] for name, box in widgets.items()})

    def add_item(box: QListWidget, text: str, done: bool = False) -> None:
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if done else Qt.CheckState.Unchecked)
        box.addItem(item)

    for name, entries in data.items():
        tab = QWidget()
        layout = QVBoxLayout(tab)
        box, entry = QListWidget(), QLineEdit()
        entry.setPlaceholderText("Neuer Eintrag – mit Enter hinzufügen")
        for text, done in entries:
            add_item(box, text, done)
        widgets[name] = box

        def submit(b=box, e=entry) -> None:
            if e.text().strip():
                add_item(b, e.text().strip())
                e.clear()
                save()

        def clear_done(b=box) -> None:
            for index in reversed(range(b.count())):
                if b.item(index).checkState() == Qt.CheckState.Checked:
                    b.takeItem(index)
            save()

        entry.returnPressed.connect(submit)
        box.itemChanged.connect(lambda _item: save())
        buttons = QHBoxLayout()
        buttons.addWidget(big_button("Hinzufügen", submit, "primary"))
        buttons.addWidget(big_button("Erledigte löschen", clear_done))
        layout.addWidget(entry)
        layout.addLayout(buttons)
        layout.addWidget(box, 1)
        tabs.addTab(tab, name)
    page.root.addWidget(tabs, 1)
    return page


def pomodoro(ctx: AppContext) -> QWidget:
    page = AppPage("Fokus-Timer")
    phases = [("Fokus", 25 * 60), ("Kurze Pause", 5 * 60), ("Fokus", 25 * 60), ("Kurze Pause", 5 * 60),
              ("Fokus", 25 * 60), ("Kurze Pause", 5 * 60), ("Fokus", 25 * 60), ("Lange Pause", 15 * 60)]
    state = {"index": 0, "left": float(phases[0][1]), "end": 0.0, "running": False}
    title, clock, bar = QLabel(), _Clock(86), QProgressBar()
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet("font-size: 24px; font-weight: 700;")
    done = QLabel(f"Heute abgeschlossen: {ctx.load('done', 0)} Fokus-Runden")
    done.setAlignment(Qt.AlignmentFlag.AlignCenter)
    timer = QTimer(page)
    timer.setInterval(250)

    def show() -> None:
        name, total = phases[state["index"]]
        left = state["end"] - datetime.now().timestamp() if state["running"] else state["left"]
        title.setText(name)
        clock.setText(_clock_text(left + 0.99))
        bar.setRange(0, total)
        bar.setValue(int(total - max(0, left)))

    def next_phase() -> None:
        if phases[state["index"]][0] == "Fokus":
            ctx.save("done", ctx.load("done", 0) + 1)
            done.setText(f"Heute abgeschlossen: {ctx.load('done', 0)} Fokus-Runden")
        state["index"] = (state["index"] + 1) % len(phases)
        state["left"] = float(phases[state["index"]][1])
        state["end"] = datetime.now().timestamp() + state["left"]
        QApplication.beep()
        show()

    def tick() -> None:
        if state["end"] - datetime.now().timestamp() <= 0:
            next_phase()
        show()

    def toggle() -> None:
        if state["running"]:
            state["left"] = state["end"] - datetime.now().timestamp()
            state["running"] = False
            timer.stop()
            start.setText("Weiter")
        else:
            state["end"] = datetime.now().timestamp() + state["left"]
            state["running"] = True
            timer.start()
            start.setText("Pause")

    def reset() -> None:
        state.update(index=0, left=float(phases[0][1]), running=False)
        timer.stop()
        start.setText("Start")
        show()

    timer.timeout.connect(tick)
    start = big_button("Start", toggle, "primary")
    row = QHBoxLayout()
    for widget in (start, big_button("Überspringen", next_phase), big_button("Zurücksetzen", reset)):
        row.addWidget(widget)
    for widget in (title, clock, bar, done):
        page.root.addWidget(widget)
    page.root.addLayout(row)
    page.root.addStretch(1)
    show()
    return page


def cleaning(ctx: AppContext) -> QWidget:
    page = AppPage("Display reinigen / Taschenlampe")
    surface = QFrame()
    surface.setMinimumHeight(260)

    def paint_color(color: str) -> None:
        surface.setStyleSheet(f"background-color: {color}; border-radius: 16px;")

    paint_color("#000000")
    row = QHBoxLayout()
    for name, color in (("Schwarz", "#000000"), ("Weiß", "#FFFFFF"), ("Warmweiß", "#FFD9A0"),
                        ("Rot", "#FF2A2A"), ("Grün", "#18C45A"), ("Blau", "#2A5BFF")):
        row.addWidget(big_button(name, lambda c=color: paint_color(c)))
    page.root.addLayout(row)
    page.root.addWidget(surface, 1)
    return page


def photo_frame(ctx: AppContext) -> QWidget:
    page = AppPage("Fotorahmen")
    image, caption = QLabel("Wähle einen Ordner mit Bildern."), QLabel()
    image.setAlignment(Qt.AlignmentFlag.AlignCenter)
    image.setMinimumHeight(260)
    caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
    state = {"files": [], "index": 0}
    timer = QTimer(page)
    timer.setInterval(int(ctx.load("seconds", 8)) * 1000)

    def load_folder(folder: str) -> None:
        extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
        root = Path(folder)
        files = sorted(p for p in root.iterdir() if p.suffix.lower() in extensions)[:500] if root.is_dir() else []
        state.update(files=files, index=0)
        show()

    def show() -> None:
        files = state["files"]
        if not files:
            image.setText("Keine Bilder im Ordner gefunden.")
            caption.clear()
            return
        pixmap = QPixmap(str(files[state["index"] % len(files)]))
        image.setPixmap(pixmap.scaled(image.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation))
        caption.setText(f"{files[state['index'] % len(files)].name}  ({state['index'] % len(files) + 1}/{len(files)})")

    def step(delta: int = 1) -> None:
        if state["files"]:
            state["index"] = (state["index"] + delta) % len(state["files"])
            show()

    def choose() -> None:
        folder = QFileDialog.getExistingDirectory(page, "Bilderordner wählen", ctx.load("folder", str(Path.home())))
        if folder:
            ctx.save("folder", folder)
            load_folder(folder)

    timer.timeout.connect(step)
    row = QHBoxLayout()
    for widget in (big_button("◀", lambda: step(-1)), big_button("Ordner …", choose), big_button("▶", step)):
        row.addWidget(widget)
    page.root.addWidget(image, 1)
    page.root.addWidget(caption)
    page.root.addLayout(row)
    if ctx.load("folder"):
        load_folder(ctx.load("folder"))
    page.showEvent = lambda event: (timer.start(), QWidget.showEvent(page, event))
    page.hideEvent = lambda event: (timer.stop(), QWidget.hideEvent(page, event))
    return page


def counters(ctx: AppContext) -> QWidget:
    page = AppPage("Zähler")
    data: dict = ctx.load("counters", {"Zähler 1": 0})
    grid = QGridLayout()
    page.root.addLayout(grid)
    page.root.addStretch(1)

    def rebuild() -> None:
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for row, (name, value) in enumerate(data.items()):
            label = QLabel(f"{name}: {value}")
            label.setStyleSheet("font-size: 22px; font-weight: 700;")
            grid.addWidget(label, row, 0)
            for column, (text, delta) in enumerate((("−", -1), ("+", 1)), start=1):
                grid.addWidget(big_button(text, lambda n=name, d=delta: change(n, d)), row, column)
            grid.addWidget(big_button("Null", lambda n=name: change(n, None)), row, 3)
            grid.addWidget(big_button("✕", lambda n=name: remove(n)), row, 4)

    def change(name: str, delta) -> None:
        data[name] = 0 if delta is None else data[name] + delta
        ctx.save("counters", data)
        rebuild()

    def remove(name: str) -> None:
        data.pop(name, None)
        ctx.save("counters", data)
        rebuild()

    def add() -> None:
        name = entry.text().strip() or f"Zähler {len(data) + 1}"
        data.setdefault(name, 0)
        entry.clear()
        ctx.save("counters", data)
        rebuild()

    entry = QLineEdit()
    entry.setPlaceholderText("Name des neuen Zählers")
    entry.returnPressed.connect(add)
    page.root.addWidget(entry)
    page.root.addWidget(big_button("Zähler hinzufügen", add, "primary"))
    rebuild()
    return page
