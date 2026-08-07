from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox, QWidget

from codex_handoff.gui.i18n import text
from codex_handoff.gui.main_window import ApplicationUpdateDialog, MainWindow, UpdatePreviewDialog
from codex_handoff.gui.widgets import ActionButton, StatusBlock, StatusTone, SyncRoute
from codex_handoff.models import ApplyPreview
from codex_handoff.updater import UpdateInfo


def test_status_widget_exposes_semantic_state() -> None:
    app = QApplication.instance() or QApplication([])
    widget = StatusBlock("Codex process")

    widget.set_state("Closed - ready", StatusTone.SUCCESS)

    assert widget.property("tone") == "success"
    assert widget.value_label.text() == "Closed - ready"
    widget.close()
    assert app is not None


def test_action_button_has_stable_height() -> None:
    app = QApplication.instance() or QApplication([])
    button = ActionButton("Sync to cloud", tone="primary")

    assert button.minimumHeight() == button.maximumHeight() == 40
    assert button.property("tone") == "primary"
    button.close()
    assert app is not None


def test_sync_route_uses_platform_specific_local_label() -> None:
    app = QApplication.instance() or QApplication([])
    route = SyncRoute()

    route.set_route("This PC", "DESKTOP-01", "Google Drive", "MacBook", "macos")

    assert route.local_title.text() == "This PC"
    assert route.local_detail.text() == "DESKTOP-01"
    assert route.remote_title.text() == "macOS"
    assert route.remote_detail.text() == "MacBook"
    route.close()
    assert app is not None


def test_update_preview_displays_removed_files_before_apply() -> None:
    app = QApplication.instance() or QApplication([])
    preview = ApplyPreview(
        "version-1",
        "Windows PC",
        ("sessions/new.json",),
        ("AGENTS.md",),
        (),
        ("sessions/old.json",),
        "windows",
        "2026-08-07T00:00:00Z",
    )

    dialog = UpdatePreviewDialog(preview)

    assert dialog.added_count.text() == "1"
    assert dialog.changed_count.text() == "1"
    assert dialog.removed_count.text() == "1"
    dialog.close()
    assert app is not None


def test_application_update_asks_before_download() -> None:
    app = QApplication.instance() or QApplication([])
    update = UpdateInfo(
        "v0.2.0-beta.3",
        "0.2.0-beta.3",
        "Beta 3",
        "Release notes",
        "CodexHandoff-macOS-arm64.dmg",
        "https://example.invalid/update.dmg",
        "0" * 64,
    )

    dialog = ApplicationUpdateDialog(update, "0.2.0-beta.2", language="ru")

    button_box = dialog.findChild(QDialogButtonBox)
    assert button_box is not None
    assert button_box.button(QDialogButtonBox.StandardButton.Apply).text() == "Скачать обновление"
    dialog.close()
    assert app is not None


def test_installation_requires_second_confirmation(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])

    class WindowDouble(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.installed: list[object] = []

        def _t(self, key: str, **values: object) -> str:
            return text("en", key, **values)

        def _install_update(self, package: object) -> None:
            self.installed.append(package)

        def statusBar(self):
            return type("Status", (), {"showMessage": lambda self, _message: None})()

    window = WindowDouble()
    package = object()
    monkeypatch.setattr(QMessageBox, "exec", lambda _dialog: QMessageBox.StandardButton.Cancel)
    MainWindow._confirm_install_update(window, package)
    assert window.installed == []

    monkeypatch.setattr(QMessageBox, "exec", lambda _dialog: QMessageBox.StandardButton.Apply)
    MainWindow._confirm_install_update(window, package)
    assert window.installed == [package]
    window.close()
    assert app is not None


def test_silent_update_result_from_rebuilt_interface_is_ignored() -> None:
    class WindowDouble:
        def __init__(self) -> None:
            self.ui_generation = 2
            self.workers: set[object] = set()
            self.results: list[object] = []

        def _update_checked(self, result: object, *, manual: bool) -> None:
            self.results.append((result, manual))

    window = WindowDouble()
    worker = object()
    window.workers.add(worker)

    MainWindow._silent_update_check_completed(window, worker, object(), generation=1)

    assert worker not in window.workers
    assert window.results == []
