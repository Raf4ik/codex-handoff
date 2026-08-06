from pathlib import Path

from codex_handoff.config import AppConfig


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
