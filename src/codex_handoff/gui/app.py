from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication, QDialog

from ..config import default_config_path
from .main_window import MainWindow
from .setup import SetupDialog, SetupWizard
from .theme import apply_theme, load_app_icon


def launch_gui(config_path: Path | None = None, *, background: bool | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Codex Handoff")
    app.setApplicationDisplayName("Codex Handoff")
    app.setWindowIcon(load_app_icon())
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    path = config_path or default_config_path()
    if not path.is_file():
        dialog = SetupWizard(path)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return 1
    window = MainWindow(path)
    launch_in_background = "--background" in sys.argv if background is None else background
    if not launch_in_background:
        window.show()
    return app.exec()


__all__ = ["MainWindow", "SetupDialog", "SetupWizard", "launch_gui"]
