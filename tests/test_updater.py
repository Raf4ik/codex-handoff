from __future__ import annotations

import hashlib
from io import BytesIO
import json
from pathlib import Path

import pytest

from codex_handoff.updater import (
    GitHubUpdater,
    RELEASES_API,
    UpdateError,
    is_newer_version,
    launch_update,
)


def test_beta_versions_are_compared_numerically() -> None:
    assert is_newer_version("v0.2.0-beta.3", "0.2.0b2")
    assert not is_newer_version("v0.2.0-beta.2", "0.2.0b2")
    assert is_newer_version("v0.2.0", "0.2.0b3")


def test_release_check_selects_platform_asset_and_checksum(tmp_path: Path) -> None:
    package = b"windows installer"
    checksum = hashlib.sha256(package).hexdigest()
    releases = [
        {
            "tag_name": "v0.2.0-beta.3",
            "name": "Beta 3",
            "body": "Russian localization and updates",
            "draft": False,
            "assets": [
                {"name": "CodexHandoff-Windows-x64-Setup.exe", "browser_download_url": "asset"},
                {"name": "SHA256SUMS", "browser_download_url": "checksums"},
            ],
        }
    ]
    responses = {
        RELEASES_API: json.dumps(releases).encode(),
        "checksums": f"{checksum}  CodexHandoff-Windows-x64-Setup.exe\n".encode(),
        "asset": package,
    }
    updater = GitHubUpdater(
        "0.2.0b2",
        "windows",
        open_url=lambda url: BytesIO(responses[url]),
        download_dir=tmp_path,
    )

    update = updater.check()

    assert update is not None
    assert update.version == "0.2.0-beta.3"
    assert updater.should_check() is False
    assert updater.download(update).read_bytes() == package


def test_download_rejects_checksum_mismatch(tmp_path: Path) -> None:
    releases = [
        {
            "tag_name": "v0.2.0-beta.3",
            "draft": False,
            "assets": [
                {"name": "CodexHandoff-macOS-arm64.dmg", "browser_download_url": "asset"},
                {"name": "SHA256SUMS", "browser_download_url": "checksums"},
            ],
        }
    ]
    responses = {
        RELEASES_API: json.dumps(releases).encode(),
        "checksums": f"{'0' * 64}  CodexHandoff-macOS-arm64.dmg\n".encode(),
        "asset": b"corrupt",
    }
    updater = GitHubUpdater(
        "0.2.0b2",
        "macos",
        open_url=lambda url: BytesIO(responses[url]),
        download_dir=tmp_path,
    )

    update = updater.check()
    assert update is not None
    with pytest.raises(UpdateError, match="SHA-256"):
        updater.download(update)

    assert not (tmp_path / "CodexHandoff-macOS-arm64.dmg").exists()


def test_windows_update_runs_installer_in_place(tmp_path: Path) -> None:
    package = tmp_path / "CodexHandoff-Windows-x64-Setup.exe"
    package.write_bytes(b"setup")
    calls: list[tuple[list[str], dict[str, object]]] = []

    launch_update(
        package,
        "windows",
        application=tmp_path / "CodexHandoff.exe",
        popen=lambda command, **kwargs: calls.append((command, kwargs)),  # type: ignore[arg-type]
    )

    assert calls[0][0][0] == str(package)
    assert "/CLOSEAPPLICATIONS" in calls[0][0]
    assert "/RESTARTAPPLICATIONS" in calls[0][0]


def test_macos_update_creates_detached_replacement_helper(tmp_path: Path) -> None:
    package = tmp_path / "CodexHandoff-macOS-arm64.dmg"
    package.write_bytes(b"dmg")
    application = tmp_path / "Applications" / "CodexHandoff.app"
    application.mkdir(parents=True)
    calls: list[tuple[list[str], dict[str, object]]] = []

    launch_update(
        package,
        "macos",
        application=application,
        process_id=123,
        popen=lambda command, **kwargs: calls.append((command, kwargs)),  # type: ignore[arg-type]
    )

    helper = package.parent / "install-macos-update.sh"
    assert helper.is_file()
    assert "/usr/bin/ditto" in helper.read_text(encoding="utf-8")
    assert calls[0][0][:2] == ["/bin/sh", str(helper)]
    assert calls[0][0][2] == "123"
    assert calls[0][1]["start_new_session"] is True
