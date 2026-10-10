"""Small games for the touch display."""
from __future__ import annotations

import random

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QWidget

from app.apps.kit import AppContext, AppPage, big_button

_LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))


def winner(board: list[str]) -> str:
    for a, b, c in _LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return "=" if all(board) else ""


def computer_move(board: list[str]) -> int:
    """Win if possible, otherwise block, otherwise centre/random."""
    free = [i for i, cell in enumerate(board) if not cell]
    for mark in ("O", "X"):
        for index in free:
            trial = board[:]
            trial[index] = mark
            if winner(trial) == mark:
                return index
    return 4 if 4 in free else random.choice(free)


def tictactoe(ctx: AppContext) -> QWidget:
    page = AppPage("Tic-Tac-Toe")
    status = QLabel("Du bist X – du beginnst.")
    status.setStyleSheet("font-size: 20px; font-weight: 700;")
    grid = QGridLayout()
    board = [""] * 9
    buttons: list[QPushButton] = []
    score = {"X": 0, "O": 0, "=": 0}
    versus_human = {"on": False, "turn": "X"}

    def render() -> None:
        for index, button in enumerate(buttons):
            button.setText(board[index])

    def finish(result: str) -> None:
        score[result] += 1
        names = {"X": "X gewinnt!", "O": "O gewinnt!", "=": "Unentschieden."}
        status.setText(f"{names[result]}   X {score['X']} · O {score['O']} · Remis {score['=']}")
        for button in buttons:
            button.setEnabled(False)

    def play(index: int) -> None:
        if board[index]:
            return
        mark = versus_human["turn"] if versus_human["on"] else "X"
        board[index] = mark
        result = winner(board)
        if not result and not versus_human["on"]:
            board[computer_move(board)] = "O"
            result = winner(board)
        elif not result:
            versus_human["turn"] = "O" if mark == "X" else "X"
            status.setText(f"{versus_human['turn']} ist dran.")
        render()
        if result:
            finish(result)

    def new_game() -> None:
        board[:] = [""] * 9
        versus_human["turn"] = "X"
        for button in buttons:
            button.setEnabled(True)
        status.setText("Zwei Spieler: X beginnt." if versus_human["on"] else "Du bist X – du beginnst.")
        render()

    def toggle_mode() -> None:
        versus_human["on"] = not versus_human["on"]
        mode.setText("Gegen Computer spielen" if versus_human["on"] else "Zu zweit spielen")
        new_game()

    for index in range(9):
        button = QPushButton("")
        button.setMinimumSize(110, 110)
        button.setStyleSheet("font-size: 52px; font-weight: 800;")
        button.clicked.connect(lambda _c=False, i=index: play(i))
        buttons.append(button)
        grid.addWidget(button, index // 3, index % 3)
    mode = big_button("Zu zweit spielen", toggle_mode)
    row = QHBoxLayout()
    row.addWidget(big_button("Neues Spiel", new_game, "primary"))
    row.addWidget(mode)
    page.root.addWidget(status)
    page.root.addLayout(grid, 1)
    page.root.addLayout(row)
    return page


def memory(ctx: AppContext) -> QWidget:
    page = AppPage("Memory")
    symbols = ["🍎", "🚗", "🐶", "⭐", "🎈", "🌵", "🎵", "🧩"]
    status = QLabel()
    status.setStyleSheet("font-size: 20px; font-weight: 700;")
    grid = QGridLayout()
    state = {"cards": [], "open": [], "found": set(), "moves": 0, "lock": False}
    buttons: list[QPushButton] = []

    def new_game() -> None:
        deck = symbols * 2
        random.shuffle(deck)
        state.update(cards=deck, open=[], found=set(), moves=0, lock=False)
        for button in buttons:
            button.setText("?")
            button.setEnabled(True)
        status.setText(f"Beste Runde: {ctx.load('best', '–')} Züge")

    def hide_pair() -> None:
        for index in state["open"]:
            buttons[index].setText("?")
        state["open"], state["lock"] = [], False

    def flip(index: int) -> None:
        if state["lock"] or index in state["open"] or index in state["found"]:
            return
        buttons[index].setText(state["cards"][index])
        state["open"].append(index)
        if len(state["open"]) < 2:
            return
        state["moves"] += 1
        first, second = state["open"]
        if state["cards"][first] == state["cards"][second]:
            state["found"] |= {first, second}
            state["open"] = []
            if len(state["found"]) == len(state["cards"]):
                best = ctx.load("best")
                if best is None or state["moves"] < best:
                    ctx.save("best", state["moves"])
                status.setText(f"Geschafft in {state['moves']} Zügen! Beste Runde: {ctx.load('best')}")
        else:
            state["lock"] = True
            QTimer.singleShot(800, hide_pair)

    for index in range(16):
        button = QPushButton("?")
        button.setMinimumSize(100, 100)
        button.setStyleSheet("font-size: 40px;")
        button.clicked.connect(lambda _c=False, i=index: flip(i))
        buttons.append(button)
        grid.addWidget(button, index // 4, index % 4)
    page.root.addWidget(status)
    page.root.addLayout(grid, 1)
    page.root.addWidget(big_button("Neues Spiel", new_game, "primary"))
    new_game()
    return page
