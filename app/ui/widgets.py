"""Widget Icons"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Card(QFrame):
    #rounded panel

    def __init__(self, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 18)
        self._layout.setSpacing(8)
        if title:
            heading = QLabel(title.upper())
            heading.setObjectName("cardTitle")
            self._layout.addWidget(heading)
            self._layout.addSpacing(2)

    def add(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        self._layout.addLayout(layout)


class Segmented(QWidget):
    #mutually exclusive buttons

    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str]], value: str, parent=None):
        super().__init__(parent)
        self.setObjectName("segmented")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for option_value, option_label in options:
            button = QPushButton(option_label)
            button.setObjectName("segment")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setProperty("value", option_value)
            if option_value == value:
                button.setChecked(True)
            self._group.addButton(button)
            layout.addWidget(button)

        self._group.buttonClicked.connect(
            lambda button: self.changed.emit(button.property("value"))
        )

    def value(self) -> str:
        button = self._group.checkedButton()
        return button.property("value") if button else ""


class SettingRow(QWidget):
    #label

    def __init__(self, label: str, control: QWidget, hint: str | None = None, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 7, 0, 7)
        layout.setSpacing(16)

        text = QVBoxLayout()
        text.setSpacing(1)
        text.addWidget(QLabel(label))
        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("muted")
            hint_label.setWordWrap(True)
            text.addWidget(hint_label)

        layout.addLayout(text, 1)
        layout.addWidget(control, 0, Qt.AlignRight | Qt.AlignVCenter)
