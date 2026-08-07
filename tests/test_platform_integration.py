from pathlib import Path

import pytest

from codex_handoff.gui import platform as platform_module


def test_platform_labels_and_codex_paths(tmp_path: Path) -> None:
    windows = platform_module.current_platform("windows", tmp_path)
    macos = platform_module.current_platform("macos", tmp_path)

    assert windows.local_label == "This PC"
    assert windows.display_name == "Windows PC"
    assert windows.codex_dir == tmp_path / ".codex"
    assert macos.local_label == "This Mac"
    assert macos.display_name == "Mac"
    assert macos.codex_dir == tmp_path / ".codex"


@pytest.mark.parametrize(
    "application",
    (
        Path("/Volumes/Codex Handoff/CodexHandoff.app"),
        Path(r"\Volumes\Codex Handoff\CodexHandoff.app"),
    ),
)
def test_macos_desktop_alias_rejects_app_on_mounted_dmg(application: Path) -> None:
    with pytest.raises(platform_module.PlatformIntegrationError, match="Applications"):
        platform_module.create_desktop_shortcut(
            application,
            platform_key="macos",
        )


def test_windows_shortcut_uses_desktop_and_app_icon(tmp_path: Path, monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(platform_module, "_run_command", lambda command: calls.append(command))

    shortcut = platform_module.create_desktop_shortcut(
        tmp_path / "CodexHandoff.exe",
        platform_key="windows",
        desktop_dir=tmp_path / "Desktop",
    )

    assert shortcut == tmp_path / "Desktop" / "Codex Handoff.lnk"
    assert "IconLocation" in calls[0][-1]
    assert str(tmp_path / "CodexHandoff.exe") in calls[0][-1]


def test_macos_autostart_writes_and_removes_launch_agent(tmp_path: Path) -> None:
    agent = tmp_path / "com.codexhandoff.desktop.plist"
    platform_module.set_autostart(True, Path("/Applications/CodexHandoff.app"), platform_key="macos", launch_agent=agent)
    assert agent.is_file()
    assert b"Codex Handoff" in agent.read_bytes()

    platform_module.set_autostart(False, Path("/Applications/CodexHandoff.app"), platform_key="macos", launch_agent=agent)
    assert not agent.exists()
