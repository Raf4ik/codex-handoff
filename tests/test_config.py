from pathlib import Path

from codex_handoff.config import AppConfig, load_config, save_config


def config(tmp_path: Path, client_secrets: Path) -> AppConfig:
    return AppConfig(
        device_id="device",
        source_dir=tmp_path / "codex",
        workspace_dir=tmp_path / "workspace",
        provider="google_drive",
        google_client_secrets=client_secrets,
        encryption_key_file=tmp_path / "recovery.key",
    )


def test_google_token_path_is_bound_to_oauth_client(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    copy = tmp_path / "copy.json"
    first.write_text('{"client_id":"first"}', encoding="utf-8")
    second.write_text('{"client_id":"second"}', encoding="utf-8")
    copy.write_bytes(first.read_bytes())

    first_path = config(tmp_path, first).token_path
    assert first_path == config(tmp_path, copy).token_path
    assert first_path != config(tmp_path, second).token_path


def test_saved_legacy_fields_load_desktop_defaults(tmp_path: Path) -> None:
    source = tmp_path / "codex"
    source.mkdir()
    key = tmp_path / "recovery.key"
    key.write_bytes(b"x")
    config_path = tmp_path / "config.json"
    save_config(
        AppConfig(
            device_id="device",
            source_dir=source,
            workspace_dir=tmp_path / "workspace",
            provider="local",
            local_storage_dir=tmp_path / "storage",
            encryption_key_file=key,
        ),
        config_path,
    )

    loaded = load_config(config_path)

    assert loaded.monitoring_enabled is True
    assert loaded.language == "en"
    assert loaded.poll_interval_seconds == 60
    assert loaded.autostart_enabled is True
    assert loaded.minimize_to_tray is True
    assert loaded.close_notice_seen is False


def test_language_round_trips_in_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    expected = AppConfig(
        device_id="device",
        source_dir=tmp_path / "codex",
        workspace_dir=tmp_path / "workspace",
        language="ru",
    )

    save_config(expected, config_path)

    assert load_config(config_path).language == "ru"
