from pathlib import Path
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from codex_handoff.config import AppConfig, load_config, save_config
from codex_handoff.crypto import generate_recovery_key
from codex_handoff.gui.app import MainWindow, SetupDialog
from codex_handoff.gui.theme import app_icon_path, load_app_icon


def test_app_icon_path_resolves_packaged_png() -> None:
    icon_path = app_icon_path()

    assert icon_path.exists()
    assert icon_path.name == "codex-handoff.png"


def test_load_app_icon_returns_non_null_icon() -> None:
    app = QApplication.instance() or QApplication([])

    assert not load_app_icon().isNull()
    assert app is not None


def test_setup_dialog_constructs(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    dialog = SetupDialog(tmp_path / "config.json")
    assert dialog.windowTitle() == "Codex Handoff Setup"
    assert dialog.provider.currentData() == "google_drive"
    assert dialog.secrets_row.isEnabled()
    assert not dialog.storage_row.isEnabled()
    dialog.close()
    assert app is not None


def test_setup_dialog_loads_existing_settings(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    config_path = tmp_path / "config.json"
    config = AppConfig(
        device_id="windows-laptop",
        source_dir=tmp_path / "codex",
        workspace_dir=tmp_path / "workspace",
        provider="local",
        local_storage_dir=tmp_path / "storage",
        encryption_key_file=tmp_path / "recovery.key",
    )
    save_config(config, config_path)
    dialog = SetupDialog(config_path)
    assert dialog.device.text() == "windows-laptop"
    assert dialog.provider.currentData() == "local"
    assert dialog.storage_row.isEnabled()
    assert not dialog.secrets_row.isEnabled()
    dialog.close()
    assert app is not None


def test_main_window_keeps_background_workers_alive(tmp_path: Path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "codex"
    (source / "sessions").mkdir(parents=True)
    key = generate_recovery_key(tmp_path / "recovery.key")
    config_path = tmp_path / "config.json"
    save_config(
        AppConfig(
            device_id="macbook",
            source_dir=source,
            workspace_dir=tmp_path / "workspace",
            provider="local",
            local_storage_dir=tmp_path / "storage",
            encryption_key_file=key,
        ),
        config_path,
    )
    monkeypatch.setattr("codex_handoff.service.is_codex_running", lambda: False)

    window = MainWindow(config_path)
    deadline = time.monotonic() + 3
    while not window.device_label.text() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)

    assert window.service is not None
    assert window.device_label.text() == "macbook"
    assert window.route.local_title.text() in {"This PC", "This Mac", "This device"}
    assert window.statusBar().currentMessage() == "Ready"
    assert window.windowFlags() & Qt.WindowType.WindowMinimizeButtonHint
    window.close()
    window.pool.waitForDone(1000)


def test_new_device_dashboard_requires_baseline_initialization(tmp_path: Path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "codex"
    (source / "sessions").mkdir(parents=True)
    key = generate_recovery_key(tmp_path / "recovery.key")
    config_path = tmp_path / "config.json"
    save_config(
        AppConfig(
            device_id="new-macbook",
            source_dir=source,
            workspace_dir=tmp_path / "workspace",
            provider="local",
            local_storage_dir=tmp_path / "storage",
            encryption_key_file=key,
        ),
        config_path,
    )
    monkeypatch.setattr("codex_handoff.service.is_codex_running", lambda: False)
    window = MainWindow(config_path)
    window.pool.waitForDone(3000)

    window._show_status(
        (
            {
                "device_id": "new-macbook",
                "baseline_id": "baseline-1",
                "last_applied_version": None,
                "remote_head": None,
                "remote_source": None,
                "update_available": False,
                "requires_initial_sync": True,
                "can_publish": False,
                "codex_running": False,
            },
            [],
        )
    )

    assert not window.push_button.isEnabled()
    assert window.pull_button.isEnabled()
    assert window.pull_button.text() == "Initialize from baseline"
    assert "new device" in window.operation_banner.message.text().lower()
    window.close()
    window.pool.waitForDone(1000)


def test_russian_dashboard_and_live_language_switch(tmp_path: Path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "codex"
    (source / "sessions").mkdir(parents=True)
    key = generate_recovery_key(tmp_path / "recovery.key")
    config_path = tmp_path / "config.json"
    save_config(
        AppConfig(
            device_id="macbook",
            source_dir=source,
            workspace_dir=tmp_path / "workspace",
            provider="local",
            local_storage_dir=tmp_path / "storage",
            encryption_key_file=key,
        ),
        config_path,
    )
    monkeypatch.setattr("codex_handoff.service.is_codex_running", lambda: False)
    window = MainWindow(config_path)
    window.pool.waitForDone(3000)

    window.language_combo.setCurrentIndex(window.language_combo.findData("ru"))
    window.pool.waitForDone(3000)
    deadline = time.monotonic() + 3
    while window.statusBar().currentMessage() != "Готово" and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)

    assert load_config(config_path).language == "ru"
    assert window.nav_buttons[0].text() == "Синхронизация"
    assert window.refresh_button.text() == "Обновить"
    assert window.statusBar().currentMessage() == "Готово"
    assert window.route.local_title.text() in {"Этот компьютер", "Этот Mac", "Это устройство"}
    window.close()
    window.pool.waitForDone(1000)
