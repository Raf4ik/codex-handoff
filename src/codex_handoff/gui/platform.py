from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import plistlib
import subprocess
import sys

from ..config import default_workspace


AUTOSTART_NAME = "Codex Handoff"
WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
MACOS_AGENT_NAME = "com.codexhandoff.desktop.plist"


class PlatformIntegrationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PlatformInfo:
    key: str
    local_label: str
    display_name: str
    codex_dir: Path
    app_data_dir: Path


def detected_platform_key() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "other"


def current_platform(key: str | None = None, home: Path | None = None) -> PlatformInfo:
    current = key or detected_platform_key()
    user_home = home or Path.home()
    labels = {
        "windows": ("This PC", "Windows PC"),
        "macos": ("This Mac", "Mac"),
    }
    local_label, display_name = labels.get(current, ("This device", "Device"))
    return PlatformInfo(current, local_label, display_name, user_home / ".codex", default_workspace())


def application_path() -> Path:
    executable = Path(sys.executable).resolve()
    if sys.platform == "darwin":
        for parent in executable.parents:
            if parent.suffix == ".app":
                return parent
    return executable


def _run_command(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Operating-system integration failed"
        raise PlatformIntegrationError(message)


def set_autostart(
    enabled: bool,
    executable: Path,
    *,
    platform_key: str | None = None,
    launch_agent: Path | None = None,
) -> None:
    current = platform_key or detected_platform_key()
    if current == "windows":
        _set_windows_autostart(enabled, executable)
    elif current == "macos":
        _set_macos_autostart(enabled, launch_agent)


def _set_windows_autostart(enabled: bool, executable: Path) -> None:
    try:
        import winreg
    except ImportError as exc:
        raise PlatformIntegrationError("Windows registry support is unavailable") from exc
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, f'"{executable}" --background')
            else:
                try:
                    winreg.DeleteValue(key, AUTOSTART_NAME)
                except FileNotFoundError:
                    pass
    except OSError as exc:
        raise PlatformIntegrationError(f"Unable to update Windows autostart: {exc}") from exc


def _set_macos_autostart(enabled: bool, destination: Path | None = None) -> None:
    target = destination or Path.home() / "Library" / "LaunchAgents" / MACOS_AGENT_NAME
    if not enabled:
        target.unlink(missing_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": "com.codexhandoff.desktop",
        "ProgramArguments": ["/usr/bin/open", "-gj", "-a", "Codex Handoff", "--args", "--background"],
        "RunAtLoad": True,
    }
    temporary = target.with_suffix(".tmp")
    with temporary.open("wb") as stream:
        plistlib.dump(payload, stream)
    temporary.replace(target)


def create_desktop_shortcut(
    executable: Path,
    *,
    platform_key: str | None = None,
    desktop_dir: Path | None = None,
) -> Path:
    current = platform_key or detected_platform_key()
    if current == "windows":
        return _create_windows_shortcut(executable, desktop_dir)
    if current == "macos":
        return _create_macos_alias(executable, desktop_dir)
    raise PlatformIntegrationError("Desktop shortcuts are unsupported on this platform")


def _create_windows_shortcut(executable: Path, desktop_dir: Path | None = None) -> Path:
    desktop = desktop_dir or Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    shortcut = desktop / "Codex Handoff.lnk"
    script = (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$shortcut = $shell.CreateShortcut('{_powershell_quote(shortcut)}'); "
        f"$shortcut.TargetPath = '{_powershell_quote(executable)}'; "
        f"$shortcut.WorkingDirectory = '{_powershell_quote(executable.parent)}'; "
        f"$shortcut.IconLocation = '{_powershell_quote(executable)},0'; "
        "$shortcut.Save()"
    )
    _run_command(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])
    return shortcut


def _powershell_quote(path: Path) -> str:
    return str(path).replace("'", "''")


def _create_macos_alias(application: Path, desktop_dir: Path | None = None) -> Path:
    resolved = application.resolve(strict=False)
    if str(resolved).startswith("/Volumes/"):
        raise PlatformIntegrationError("Move Codex Handoff to Applications before creating its desktop alias")
    desktop = desktop_dir or Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    alias_path = desktop / "Codex Handoff"
    if alias_path.exists():
        return alias_path
    script = (
        "on run argv\n"
        "tell application \"Finder\" to make new alias file at desktop to POSIX file (item 1 of argv) "
        "with properties {name:\"Codex Handoff\"}\n"
        "end run"
    )
    _run_command(["osascript", "-e", script, str(resolved)])
    return alias_path
