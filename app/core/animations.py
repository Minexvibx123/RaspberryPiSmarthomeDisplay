"""Central, one-shot widget animations designed for low-power touch panels."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QSequentialAnimationGroup
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


ANIMATION_NAMES = ["none", "fade", "slide", "pulse", "bounce", "shake", "glow"]


class AnimationEngine:
    """Runs at most one short animation per widget and releases it afterwards."""

    def __init__(self) -> None:
        self._running: dict[QWidget, object] = {}

    def play(self, widget: QWidget, name: str, speed: float = 1.0) -> None:
        if name not in ANIMATION_NAMES or name == "none" or not widget.isVisible():
            return
        self.stop(widget)
        duration = max(100, min(1500, int(280 / max(0.1, speed))))
        if name == "fade":
            self._play_fade(widget, duration)
            return

        original = widget.geometry()
        if name == "slide":
            start = original.translated(-max(16, original.width() // 8), 0)
            animation = self._geometry_animation(widget, start, original, duration)
        elif name == "pulse":
            amount = max(4, min(16, original.width() // 12, original.height() // 12))
            expanded = original.adjusted(-amount, -amount, amount, amount)
            animation = self._geometry_sequence(widget, [original, expanded, original], duration)
        elif name == "bounce":
            lowered = original.translated(0, max(8, original.height() // 8))
            animation = self._geometry_sequence(widget, [original, lowered, original], duration)
        elif name == "shake":
            amount = max(6, min(18, original.width() // 10))
            animation = self._geometry_sequence(
                widget,
                [original, original.translated(-amount, 0), original.translated(amount, 0), original],
                duration,
            )
        else:  # glow
            self._play_glow(widget, duration)
            return
        self._start(widget, animation, original)

    def stop(self, widget: QWidget) -> None:
        animation = self._running.pop(widget, None)
        if animation is not None:
            animation.stop()

    @staticmethod
    def _geometry_animation(widget: QWidget, start: QRect, end: QRect, duration: int) -> QPropertyAnimation:
        animation = QPropertyAnimation(widget, b"geometry")
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        return animation

    def _geometry_sequence(self, widget: QWidget, values: list[QRect], duration: int) -> QSequentialAnimationGroup:
        group = QSequentialAnimationGroup()
        step_duration = max(70, duration // (len(values) - 1))
        for start, end in zip(values, values[1:]):
            group.addAnimation(self._geometry_animation(widget, start, end, step_duration))
        return group

    def _play_fade(self, widget: QWidget, duration: int) -> None:
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setDuration(duration)

        def restore_style() -> None:
            widget.setGraphicsEffect(None)
            apply_style = getattr(widget, "apply_style", None)
            if callable(apply_style):
                apply_style()

        self._start(widget, animation, None, restore_style)

    def _play_glow(self, widget: QWidget, duration: int) -> None:
        effect = widget.graphicsEffect()
        if effect is None or not hasattr(effect, "blurRadius"):
            return
        original_blur = effect.blurRadius()
        animation = QPropertyAnimation(effect, b"blurRadius")
        animation.setStartValue(original_blur)
        animation.setKeyValueAt(0.5, original_blur + 16)
        animation.setEndValue(original_blur)
        animation.setDuration(duration)
        self._start(widget, animation, None)

    def _start(self, widget: QWidget, animation, restore_geometry: QRect | None, on_finished=None) -> None:
        self._running[widget] = animation

        def finished() -> None:
            if restore_geometry is not None:
                widget.setGeometry(restore_geometry)
            if on_finished is not None:
                on_finished()
            self._running.pop(widget, None)
            animation.deleteLater()

        animation.finished.connect(finished)
        animation.start()


animation_engine = AnimationEngine()