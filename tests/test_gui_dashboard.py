from PySide6.QtWidgets import QApplication

from codex_handoff.gui.main_window import UpdatePreviewDialog
from codex_handoff.gui.widgets import ActionButton, StatusBlock, StatusTone, SyncRoute
from codex_handoff.models import ApplyPreview


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
