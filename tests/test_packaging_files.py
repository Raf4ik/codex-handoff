from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_installer_is_per_user_and_creates_system_entries() -> None:
    script = (ROOT / "packaging" / "codex-handoff.iss").read_text(encoding="utf-8")

    assert "PrivilegesRequired=lowest" in script
    assert "{autodesktop}\\Codex Handoff" in script
    assert "{autoprograms}\\Codex Handoff" in script
    assert "CurrentVersion\\Run" in script
    assert "uninsdeletevalue" in script
    assert "CodexHandoff-Windows-x64-Setup" in script


def test_windows_workflow_builds_installer_not_portable_executable() -> None:
    workflow = (ROOT / ".github" / "workflows" / "desktop-build.yml").read_text(encoding="utf-8")

    assert "codex-handoff.iss" in workflow
    assert "--onedir" in workflow
    assert "--onefile" not in workflow
    assert "CodexHandoff-Windows-x64-Setup.exe" in workflow
    assert "Application files remain after uninstall" in workflow
    assert "Autostart entry remains after uninstall" in workflow


def test_macos_dmg_contains_applications_alias_and_icon() -> None:
    script = (ROOT / "packaging" / "macos-dmg.sh").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "desktop-build.yml").read_text(encoding="utf-8")

    assert 'ln -s /Applications "$stage/Applications"' in script
    assert '.VolumeIcon.icns' in script
    assert 'CodexHandoff.icns' in workflow
    assert '--icon build/icons/CodexHandoff.icns' in workflow
    assert 'test -L "$mount_point/Applications"' in workflow
