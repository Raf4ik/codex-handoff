from pathlib import Path

import pytest

from codex_handoff.config import AppConfig
from codex_handoff.crypto import generate_recovery_key
from codex_handoff.exceptions import BaselineExistsError, HandoffError, StaleDeviceError
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


def test_new_device_cannot_publish_before_initializing_from_cloud(tmp_path: Path) -> None:
    original = HandoffService(make_config(tmp_path, "original-mac"), LocalProvider(tmp_path / "remote"))
    replacement = HandoffService(make_config(tmp_path, "new-mac"), LocalProvider(tmp_path / "remote"))
    original.create_baseline()

    with pytest.raises(HandoffError, match="new device"):
        replacement.push()

    assert replacement.list_versions() == []


def test_new_device_status_explains_required_initial_sync(tmp_path: Path) -> None:
    original = HandoffService(make_config(tmp_path, "original"), LocalProvider(tmp_path / "remote"))
    replacement = HandoffService(make_config(tmp_path, "replacement"), LocalProvider(tmp_path / "remote"))
    baseline = original.create_baseline()

    before = replacement.status()
    replacement.restore(baseline.version_id)
    after = replacement.status()

    assert before["requires_initial_sync"] is True
    assert before["can_publish"] is False
    assert after["requires_initial_sync"] is False
    assert after["can_publish"] is True


def test_new_device_can_restore_baseline_then_publish(tmp_path: Path) -> None:
    original = HandoffService(make_config(tmp_path, "old-windows-pc"), LocalProvider(tmp_path / "remote"))
    replacement_config = make_config(tmp_path, "new-windows-pc")
    replacement = HandoffService(replacement_config, LocalProvider(tmp_path / "remote"))
    baseline = original.create_baseline()

    replacement.restore(baseline.version_id)
    restored = (replacement_config.source_dir / "sessions/current.json").read_text(encoding="utf-8")
    published = replacement.push()

    assert restored == "initial-old-windows-pc"
    assert published.source_device == "new-windows-pc"
    assert published.parent_version is None


@pytest.mark.parametrize(
    ("first_platform", "second_platform"),
    (("Darwin", "Windows"), ("Windows", "Windows"), ("Darwin", "Darwin")),
)
def test_any_two_supported_devices_can_sync_both_directions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    first_platform: str,
    second_platform: str,
) -> None:
    first_config = make_config(tmp_path, "first-device")
    second_config = make_config(tmp_path, "second-device")
    first = HandoffService(first_config, LocalProvider(tmp_path / "remote"))
    second = HandoffService(second_config, LocalProvider(tmp_path / "remote"))

    monkeypatch.setattr("codex_handoff.artifacts.platform.system", lambda: first_platform)
    first.create_baseline()
    first_file = first_config.source_dir / "sessions/current.json"
    first_file.write_text("work-from-first", encoding="utf-8")
    first_version = first.push()

    second.pull()
    second_file = second_config.source_dir / "sessions/current.json"
    assert second_file.read_text(encoding="utf-8") == "work-from-first"
    monkeypatch.setattr("codex_handoff.artifacts.platform.system", lambda: second_platform)
    second_file.write_text("work-from-second", encoding="utf-8")
    second_version = second.push()

    first.pull()

    expected_platforms = {"Darwin": "macos", "Windows": "windows"}
    assert first_version.source_platform == expected_platforms[first_platform]
    assert second_version.source_platform == expected_platforms[second_platform]
    assert first_file.read_text(encoding="utf-8") == "work-from-second"
    assert first.status()["last_applied_version"] == second_version.version_id


def test_protected_baseline_is_cached_on_both_devices(tmp_path: Path) -> None:
    first_config = make_config(tmp_path, "first-device")
    second_config = make_config(tmp_path, "second-device")
    first = HandoffService(first_config, LocalProvider(tmp_path / "remote"))
    second = HandoffService(second_config, LocalProvider(tmp_path / "remote"))

    baseline = first.create_baseline()
    first.push()
    second.pull()

    first_copy = first_config.workspace_dir / "baselines" / f"{baseline.version_id}.chandoff"
    second_copy = second_config.workspace_dir / "baselines" / f"{baseline.version_id}.chandoff"
    assert first_copy.is_file()
    assert second_copy.is_file()
    assert first_copy.read_bytes() == second_copy.read_bytes()
    assert first.status()["local_baseline_available"] is True
    assert second.status()["local_baseline_available"] is True


def test_each_device_can_restore_its_local_baseline_copy_without_remote_artifact(tmp_path: Path) -> None:
    first_config = make_config(tmp_path, "first-device")
    second_config = make_config(tmp_path, "second-device")
    provider = LocalProvider(tmp_path / "remote")
    first = HandoffService(first_config, provider)
    second = HandoffService(second_config, provider)
    baseline = first.create_baseline()
    first.push()
    second.pull()
    (tmp_path / "remote" / "baselines" / f"{baseline.version_id}.chandoff").unlink()
    (tmp_path / "remote" / "baselines" / f"{baseline.version_id}.json").unlink()

    for service, config in ((first, first_config), (second, second_config)):
        current = config.source_dir / "sessions/current.json"
        current.write_text("damaged", encoding="utf-8")
        service.restore(baseline.version_id)
        assert current.read_text(encoding="utf-8") == "initial-first-device"


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


def test_restored_baseline_can_be_published_as_new_head(tmp_path: Path) -> None:
    config = make_config(tmp_path, "mac")
    service = HandoffService(config, LocalProvider(tmp_path / "remote"))
    baseline = service.create_baseline()
    file = config.source_dir / "sessions/current.json"
    original = file.read_text(encoding="utf-8")
    file.write_text("new work", encoding="utf-8")
    previous = service.push()

    service.restore(baseline.version_id)
    restored = service.push()

    assert file.read_text(encoding="utf-8") == original
    assert restored.parent_version == previous.version_id
    assert service.status()["remote_head"] == restored.version_id
