from atexit import register
from contextlib import ExitStack
from importlib.resources import as_file, files
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication


_RESOURCE_CONTEXTS = ExitStack()
register(_RESOURCE_CONTEXTS.close)

CHARCOAL = "#17252A"
CHARCOAL_LIGHT = "#24373D"
TEAL = "#19988D"
TEAL_BRIGHT = "#50D6C7"
CORAL = "#E96755"
GOLD = "#C69012"
SURFACE = "#F4F6F5"
WHITE = "#FFFFFF"
TEXT = "#1D2C31"
MUTED = "#65757A"
BORDER = "#D8E0DE"
ERROR = "#B93F36"


def app_icon_path() -> Path:
    resource = files("codex_handoff.assets").joinpath("codex-handoff.png")
    try:
        return Path(resource)
    except TypeError:
        return _RESOURCE_CONTEXTS.enter_context(as_file(resource))


def load_app_icon() -> QIcon:
    return QIcon(str(app_icon_path()))


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)


STYLESHEET = f"""
QWidget {{
    color: {TEXT};
    font-size: 13px;
}}
QMainWindow, QDialog, QStackedWidget {{ background: {SURFACE}; }}
QToolTip {{
    color: {WHITE}; background: {CHARCOAL}; border: 1px solid {CHARCOAL_LIGHT};
    padding: 6px; border-radius: 4px;
}}
QLabel[role="heading"] {{ font-size: 22px; font-weight: 700; }}
QLabel[role="subtitle"] {{ color: {MUTED}; }}
QLineEdit, QComboBox {{
    min-height: 38px; padding: 0 10px; background: {WHITE};
    border: 1px solid {BORDER}; border-radius: 6px;
}}
QLineEdit:focus, QComboBox:focus {{ border: 2px solid {TEAL}; }}
QPushButton {{
    min-height: 38px; padding: 0 14px; background: #E8EEEC;
    border: 1px solid transparent; border-radius: 6px; font-weight: 600;
}}
QPushButton:hover {{ background: #DDE6E3; }}
QPushButton:pressed {{ background: #CFDCDA; }}
QPushButton:focus {{ border: 2px solid {TEAL}; }}
QPushButton:disabled {{ color: #95A19F; background: #EDF0EF; }}
QPushButton[tone="primary"] {{ color: {WHITE}; background: {TEAL}; }}
QPushButton[tone="primary"]:hover {{ background: #137F76; }}
QPushButton[tone="incoming"] {{ color: {WHITE}; background: {CORAL}; }}
QPushButton[tone="incoming"]:hover {{ background: #D55747; }}
QPushButton[tone="danger"] {{ color: {WHITE}; background: {ERROR}; }}
QPushButton[nav="true"] {{
    color: #AAB9BC; background: transparent; text-align: left; padding-left: 14px;
}}
QPushButton[nav="true"]:checked {{ color: {WHITE}; background: #304247; }}
QFrame[card="true"] {{ background: {WHITE}; border: 1px solid {BORDER}; border-radius: 7px; }}
QFrame[tone="success"] {{ border-left: 4px solid {TEAL}; }}
QFrame[tone="warning"] {{ border-left: 4px solid {GOLD}; }}
QFrame[tone="error"] {{ border-left: 4px solid {ERROR}; }}
QFrame[tone="neutral"] {{ border-left: 4px solid #7C8D91; }}
QTableWidget {{
    background: {WHITE}; alternate-background-color: #F8FAF9;
    border: 1px solid {BORDER}; border-radius: 6px; gridline-color: #E8ECEB;
    selection-background-color: #DDF3EF; selection-color: {TEXT};
}}
QHeaderView::section {{
    background: #F1F4F3; color: {MUTED}; border: 0; border-bottom: 1px solid {BORDER};
    padding: 8px; font-size: 11px; font-weight: 700;
}}
QProgressBar {{ border: 0; background: #E0E7E5; height: 5px; border-radius: 2px; }}
QProgressBar::chunk {{ background: {TEAL}; border-radius: 2px; }}
QFrame#setupRail {{ background: {CHARCOAL}; border: 0; }}
QLabel#setupBrand {{ color: {WHITE}; font-size: 17px; font-weight: 700; }}
QLabel#setupPrivacy {{ color: #829599; font-size: 11px; }}
QLabel[step="pending"] {{ color: #718489; }}
QLabel[step="active"] {{ color: {WHITE}; background: #304247; border-radius: 6px; font-weight: 700; }}
QLabel[step="done"] {{ color: #94D8D1; }}
QLabel#eyebrow {{ color: {TEAL}; font-size: 11px; font-weight: 800; }}
QLabel#platformBadge {{
    background: #E5F3F0; color: #176F68; border: 1px solid #CCE3DF;
    border-radius: 6px; padding: 12px; font-weight: 700;
}}
QLabel#warningNote {{
    background: #FFF6DA; color: #725A17; border-left: 4px solid {GOLD};
    padding: 12px; border-radius: 4px;
}}
QLabel#reviewSummary {{
    background: {WHITE}; border: 1px solid {BORDER}; border-radius: 6px;
    padding: 16px; line-height: 1.5;
}}
"""
