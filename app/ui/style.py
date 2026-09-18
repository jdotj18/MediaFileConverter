"""Program stylesheet"""

BG = "#f4f5f8"
SURFACE = "#ffffff"
FIELD = "#edeff3"
FIELD_HI = "#e3e6ec"
TEXT = "#1a1d23"
MUTED = "#6b7280"
LINE = "#e6e9ee"
ACCENT = "#2f5fd0"
ACCENT_HI = "#2650b4"
ACCENT_SOFT = "#e9eefb"
OK = "#1e7d5a"
DANGER = "#c2413f"

STYLESHEET = f"""
QWidget {{
    color: {TEXT};
    font-family: "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
    font-size: 13px;
}}
QMainWindow, QDialog {{
    background: {BG};
}}
QWidget#page {{
    background: {BG};
}}
QLabel {{
    background: transparent;
}}

QLabel#heading {{
    font-size: 15px;
    font-weight: 600;
}}
QLabel#dropTitle {{
    font-size: 17px;
    font-weight: 600;
}}
QLabel#muted {{
    color: {MUTED};
    font-size: 12px;
}}
QLabel#cardTitle {{
    color: {MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#error {{
    color: {DANGER};
}}
QLabel#thumbnail {{
    border-radius: 8px;
}}

QFrame#card {{
    background: {SURFACE};
    border: 0;
    border-radius: 12px;
}}
QFrame#dropZone {{
    background: {SURFACE};
    border: 2px dashed #d6dae3;
    border-radius: 14px;
}}
QFrame#dropZone[active="true"] {{
    border-color: {ACCENT};
    background: {ACCENT_SOFT};
}}

QTabWidget::pane {{
    background: {BG};
    border: 0;
}}
QTabBar {{
    background: {BG};
}}
QTabBar::tab {{
    background: transparent;
    color: {MUTED};
    padding: 10px 2px;
    margin-right: 24px;
    border: 0;
    border-bottom: 2px solid transparent;
    font-size: 14px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    color: {TEXT};
}}

QPushButton {{
    background: {FIELD};
    border: 0;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {FIELD_HI};
}}
QPushButton:disabled {{
    background: #f0f2f5;
    color: #a8aeba;
}}
QPushButton#primary {{
    background: {ACCENT};
    color: #ffffff;
}}
QPushButton#primary:hover {{
    background: {ACCENT_HI};
}}
QPushButton#primary:disabled {{
    background: #c5cfe8;
    color: #ffffff;
}}
QPushButton#danger {{
    background: transparent;
    color: {DANGER};
}}
QPushButton#danger:hover {{
    background: #fbecec;
}}
QPushButton#link {{
    background: transparent;
    color: {ACCENT};
    padding: 3px 4px;
    font-weight: 600;
}}
QPushButton#link:hover {{
    color: {ACCENT_HI};
}}
QPushButton#iconButton {{
    background: transparent;
    color: #9aa1ad;
    padding: 4px;
    font-size: 15px;
}}
QPushButton#iconButton:hover {{
    color: {DANGER};
}}

QWidget#segmented {{
    background: {FIELD};
    border-radius: 9px;
}}
QPushButton#segment {{
    background: transparent;
    color: {MUTED};
    border-radius: 7px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#segment:checked {{
    background: {SURFACE};
    color: {ACCENT};
}}
QPushButton#segment:hover:!checked {{
    color: {TEXT};
}}

QComboBox, QLineEdit, QSpinBox {{
    background: {FIELD};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: {ACCENT};
    selection-color: #ffffff;
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{
    background: {SURFACE};
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{
    border: 0;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT};
    outline: 0;
}}

QCheckBox {{
    background: transparent;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid #ccd2dc;
    border-radius: 5px;
    background: {SURFACE};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {FIELD_HI};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {SURFACE};
    border: 1px solid #c8ced9;
    width: 16px;
    height: 16px;
    margin: -7px 0;
    border-radius: 9px;
}}

QProgressBar {{
    background: {FIELD};
    border: 0;
    border-radius: 7px;
    height: 20px;
    text-align: center;
    font-size: 11px;
    font-weight: 600;
    color: {MUTED};
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 7px;
}}
QProgressBar#done::chunk {{
    background: {OK};
}}
QProgressBar#failed {{
    color: {DANGER};
}}

QTableWidget {{
    background: {SURFACE};
    border: 0;
    border-radius: 12px;
    gridline-color: transparent;
    outline: 0;
}}
QTableWidget::item {{
    padding: 10px;
    border: 0;
    border-bottom: 1px solid #f2f4f7;
}}
QHeaderView {{
    background: transparent;
}}
QHeaderView::section {{
    background: {SURFACE};
    color: {MUTED};
    border: 0;
    border-bottom: 1px solid {LINE};
    padding: 12px 10px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QTableCornerButton::section {{
    background: {SURFACE};
    border: 0;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px 4px 0;
}}
QScrollBar::handle:vertical {{
    background: #d4d9e2;
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: #c0c7d3;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0 4px 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background: #d4d9e2;
    border-radius: 4px;
    min-width: 32px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

QToolTip {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {LINE};
    padding: 6px 8px;
}}
"""
