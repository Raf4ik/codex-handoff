from pathlib import Path

from PySide6.QtWidgets import QApplication

from codex_handoff.gui.setup import SetupWizard


def test_setup_wizard_starts_with_platform_defaults(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    wizard = SetupWizard(tmp_path / "config.json")

    assert wizard.current_step == 0
    assert wizard.device_page.source.text().endswith(".codex")
    assert wizard.storage_page.provider.currentData() == "google_drive"
    assert wizard.review_page.autostart.isChecked()
    assert wizard.review_page.desktop_shortcut.isChecked()
    assert wizard.minimumWidth() >= 840
    wizard.close()
    assert app is not None


def test_local_provider_switches_visible_fields(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    wizard = SetupWizard(tmp_path / "config.json")

    wizard.storage_page.provider.setCurrentIndex(1)

    assert wizard.storage_page.local_folder_row.isEnabled()
    assert not wizard.storage_page.oauth_row.isEnabled()
    wizard.close()
    assert app is not None
