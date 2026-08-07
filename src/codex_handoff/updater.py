from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import BinaryIO
from urllib.request import Request, urlopen

from platformdirs import user_cache_dir


RELEASES_API = "https://api.github.com/repos/Raf4ik/codex-handoff/releases?per_page=10"
ASSET_NAMES = {
    "macos": "CodexHandoff-macOS-arm64.dmg",
    "windows": "CodexHandoff-Windows-x64-Setup.exe",
}
USER_AGENT = "Codex-Handoff-Updater"


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    tag: str
    version: str
    title: str
    notes: str
    asset_name: str
    asset_url: str
    sha256: str


def _version_key(value: str) -> tuple[int, int, int, int, int]:
    normalized = value.strip().lower().lstrip("v").replace("-beta.", "b").replace("-beta", "b")
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:b(\d+))?", normalized)
    if not match:
        raise UpdateError(f"Unsupported release version: {value}")
    major, minor, patch = (int(match.group(index)) for index in (1, 2, 3))
    beta = match.group(4)
    return major, minor, patch, 0 if beta is not None else 1, int(beta or 0)


def is_newer_version(candidate: str, current: str) -> bool:
    return _version_key(candidate) > _version_key(current)


def _default_open_url(url: str) -> BinaryIO:
    request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT})
    return urlopen(request, timeout=30)  # type: ignore[return-value]


class GitHubUpdater:
    def __init__(
        self,
        current_version: str,
        platform_key: str,
        *,
        open_url: Callable[[str], BinaryIO] = _default_open_url,
        download_dir: Path | None = None,
    ) -> None:
        if platform_key not in ASSET_NAMES:
            raise UpdateError(f"Updates are unsupported on platform: {platform_key}")
        self.current_version = current_version
        self.platform_key = platform_key
        self.open_url = open_url
        self.download_dir = download_dir or Path(user_cache_dir("Codex Handoff")) / "updates"

    @property
    def last_check_path(self) -> Path:
        return self.download_dir / "last-successful-check"

    def should_check(self, interval_seconds: int = 24 * 60 * 60) -> bool:
        try:
            age = time.time() - self.last_check_path.stat().st_mtime
        except OSError:
            return True
        return age >= interval_seconds

    def _record_successful_check(self) -> None:
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.last_check_path.touch()

    def _read(self, url: str) -> bytes:
        with self.open_url(url) as response:
            return response.read()

    def check(self) -> UpdateInfo | None:
        try:
            releases = json.loads(self._read(RELEASES_API).decode("utf-8"))
        except (OSError, ValueError, UnicodeError) as exc:
            raise UpdateError(f"Unable to check GitHub Releases: {exc}") from exc
        if not isinstance(releases, list):
            raise UpdateError("GitHub Releases returned an unexpected response")

        candidates: list[tuple[tuple[int, int, int, int, int], dict[str, object]]] = []
        for release in releases:
            if not isinstance(release, dict) or release.get("draft") is True:
                continue
            tag = str(release.get("tag_name") or "")
            try:
                key = _version_key(tag)
            except UpdateError:
                continue
            if key > _version_key(self.current_version):
                candidates.append((key, release))
        if not candidates:
            self._record_successful_check()
            return None

        _, release = max(candidates, key=lambda item: item[0])
        assets = release.get("assets")
        if not isinstance(assets, list):
            raise UpdateError("The release has no downloadable assets")
        by_name = {
            str(asset.get("name")): str(asset.get("browser_download_url"))
            for asset in assets
            if isinstance(asset, dict) and asset.get("name") and asset.get("browser_download_url")
        }
        asset_name = ASSET_NAMES[self.platform_key]
        if asset_name not in by_name or "SHA256SUMS" not in by_name:
            raise UpdateError(f"The release is missing {asset_name} or SHA256SUMS")
        checksums = self._read(by_name["SHA256SUMS"]).decode("utf-8")
        expected = _checksum_for(checksums, asset_name)
        self._record_successful_check()
        tag = str(release["tag_name"])
        return UpdateInfo(
            tag=tag,
            version=tag.lstrip("v"),
            title=str(release.get("name") or tag),
            notes=str(release.get("body") or ""),
            asset_name=asset_name,
            asset_url=by_name[asset_name],
            sha256=expected,
        )

    def download(self, update: UpdateInfo) -> Path:
        self.download_dir.mkdir(parents=True, exist_ok=True)
        destination = self.download_dir / update.asset_name
        temporary = destination.with_suffix(destination.suffix + ".part")
        digest = hashlib.sha256()
        try:
            with self.open_url(update.asset_url) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    digest.update(chunk)
                    output.write(chunk)
            if digest.hexdigest().lower() != update.sha256.lower():
                temporary.unlink(missing_ok=True)
                raise UpdateError("The downloaded update failed SHA-256 verification")
            temporary.replace(destination)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise UpdateError(f"Unable to download the update: {exc}") from exc
        return destination


def _checksum_for(contents: str, asset_name: str) -> str:
    for line in contents.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == asset_name:
            checksum = parts[0].lower()
            if re.fullmatch(r"[0-9a-f]{64}", checksum):
                return checksum
    raise UpdateError(f"SHA256SUMS has no valid checksum for {asset_name}")


def launch_update(
    package: Path,
    platform_key: str,
    *,
    application: Path,
    process_id: int | None = None,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> None:
    if not package.is_file():
        raise UpdateError(f"Update package not found: {package}")
    if platform_key == "windows":
        popen(
            [
                str(package),
                "/SILENT",
                "/CURRENTUSER",
                "/CLOSEAPPLICATIONS",
                "/NORESTARTAPPLICATIONS",
                "/UPDATE=1",
            ],
            close_fds=True,
        )
        return
    if platform_key != "macos":
        raise UpdateError(f"Updates are unsupported on platform: {platform_key}")
    if application.suffix != ".app" or not application.is_dir():
        raise UpdateError("Install Codex Handoff in Applications before using automatic updates")
    if not os.access(application.parent, os.W_OK):
        raise UpdateError("The Applications folder is not writable by the current user")

    helper = package.parent / "install-macos-update.sh"
    helper.write_text(MACOS_UPDATE_HELPER, encoding="utf-8")
    helper.chmod(0o700)
    popen(
        [
            "/bin/sh",
            str(helper),
            str(process_id or os.getpid()),
            str(package),
            str(application),
        ],
        close_fds=True,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


MACOS_UPDATE_HELPER = """#!/bin/sh
set -eu
app_pid="$1"
dmg_path="$2"
target_app="$3"
mount_dir="$(mktemp -d /tmp/codex-handoff-update.XXXXXX)"
backup_app="${target_app}.previous"

while kill -0 "$app_pid" 2>/dev/null; do
  sleep 1
done

cleanup() {
  /usr/bin/hdiutil detach "$mount_dir" >/dev/null 2>&1 || true
  /bin/rmdir "$mount_dir" >/dev/null 2>&1 || true
}
trap cleanup EXIT

/usr/bin/hdiutil attach "$dmg_path" -nobrowse -readonly -mountpoint "$mount_dir" >/dev/null
source_app="$mount_dir/CodexHandoff.app"
test -d "$source_app"
/bin/rm -rf "$backup_app"
/bin/mv "$target_app" "$backup_app"
if /usr/bin/ditto "$source_app" "$target_app"; then
  /bin/rm -rf "$backup_app"
  /usr/bin/open "$target_app"
else
  /bin/rm -rf "$target_app"
  /bin/mv "$backup_app" "$target_app"
  /usr/bin/open "$target_app"
  exit 1
fi
"""


def current_process_id() -> int:
    return os.getpid()


def is_packaged_application() -> bool:
    return bool(getattr(sys, "frozen", False))
