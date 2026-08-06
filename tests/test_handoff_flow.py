from pathlib import Path

import pytest

from codex_handoff.config import AppConfig
from codex_handoff.crypto import generate_recovery_key
from codex_handoff.exceptions import BaselineExistsError, StaleDeviceError
from codex_handoff.providers.local import LocalProvider
from codex_handoff.service import HandoffService


def make_config(root: Path, device: str) -> AppConfig:
    source = root / device / "codex"
    source.mkdir(parents=True)
    (source / "sessions").mkdir()
    (source / "sessions" / "current.json").write_text(f"initial-{device}", encoding="utf-8")
    recovery_key = root / "recovery.key"
    if not recovery_key.exists():
        generate_recovery_key(recovery_key)
    return AppConfig(
        device_id=device,
        source_dir=source,
        workspace_dir=root / device / "workspace",
        provider="local",
        local_storage_dir=root / "remote",
        encryption_key_file=recovery_key,
    )


@pytest.fixture(autouse=True)
def codex_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("codex_handoff.service.is_codex_running", lambda: False)


def test_bidirectional_mac_windows_handoff_and_stale_protection(tmp_path: Path) -> None:
    mac_config = make_config(tmp_path, "mac")
    windows_config = make_config(tmp_path, "windows")
    mac = HandoffService(mac_config, LocalProvider(tmp_path / "remote"))
    windows = HandoffService(windows_config, LocalProvider(tmp_path / "remote"))

    baseline = mac.create_baseline()
    assert baseline.version_id.startswith("baseline-")
    with pytest.raises(BaselineExistsError):
        windows.create_baseline()

    (mac_config.source_dir / "sessions/current.json").write_text("work-from-mac", encoding="utf-8")
    mac_version = mac.push()
    preview = windows.preview_pull()
    assert preview is not None and preview.version_id == mac_version.version_id
    windows.pull()
    assert (windows_config.source_dir / "sessions/current.json").read_text() == "work-from-mac"

    (windows_config.source_dir / "sessions/current.json").write_text("work-from-windows", encoding="utf-8")
    windows_version = windows.push()
    with pytest.raises(StaleDeviceError):
        mac.push()
    mac.pull()
    assert (mac_config.source_dir / "sessions/current.json").read_text() == "work-from-windows"
    assert mac.status()["last_applied_version"] == windows_version.version_id


def test_pull_creates_pre_apply_backup(tmp_path: Path) -> None:
    mac_config = make_config(tmp_path, "mac")
    windows_config = make_config(tmp_path, "windows")
    mac = HandoffService(mac_config, LocalProvider(tmp_path / "remote"))
    windows = HandoffService(windows_config, LocalProvider(tmp_path / "remote"))
    mac.create_baseline()
    mac.push()
    windows.pull()
    assert list((windows_config.workspace_dir / "backups").glob("backup-*.chandoff"))


def test_protected_baseline_can_be_restored(tmp_path: Path) -> None:
    config = make_config(tmp_path, "mac")
    service = HandoffService(config, LocalProvider(tmp_path / "remote"))
    baseline = service.create_baseline()
    file = config.source_dir / "sessions/current.json"
    original = file.read_text(encoding="utf-8")
    file.write_text("broken", encoding="utf-8")
    service.restore(baseline.version_id)
    assert file.read_text(encoding="utf-8") == original
