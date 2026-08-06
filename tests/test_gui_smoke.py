from pathlib import Path

from PySide6.QtWidgets import QApplication

from codex_handoff.gui.app import SetupDialog


def test_setup_dialog_constructs(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    dialog = SetupDialog(tmp_path / "config.json")
    assert dialog.windowTitle() == "Codex Handoff Setup"
    dialog.close()
    assert app is not None
