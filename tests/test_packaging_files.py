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
    assert "VersionInfoVersion=0.2.0.3" in script
    assert "VersionInfoProductVersion=0.2.0.3" in script
    assert "VersionInfoProductVersion={#MyAppVersion}" not in script


def test_windows_workflow_builds_installer_not_portable_executable() -> None:
    workflow = (ROOT / ".github" / "workflows" / "desktop-build.yml").read_text(encoding="utf-8")

    assert "codex-handoff.iss" in workflow
    assert "--onedir" in workflow
    assert "--onefile" not in workflow
    assert "CodexHandoff-Windows-x64-Setup.exe" in workflow
    assert "Application files remain after uninstall" in workflow
    assert "Autostart entry remains after uninstall" in workflow
    assert "$runProperties.'Codex Handoff'" in workflow
    assert "Get-ItemPropertyValue `" not in workflow
    assert "$runProperties = Get-ItemProperty `" in workflow


def test_macos_dmg_contains_applications_alias_and_icon() -> None:
    script = (ROOT / "packaging" / "macos-dmg.sh").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "desktop-build.yml").read_text(encoding="utf-8")

    assert 'ln -s /Applications "$stage/Applications"' in script
    assert '.VolumeIcon.icns' in script
    assert 'CodexHandoff.icns' in workflow
    assert '--icon build/icons/CodexHandoff.icns' in workflow
    assert 'test -L "$mount_point/Applications"' in workflow
    assert "for attempt in 1 2 3" in script
    assert 'rm -f "$destination"' in script


def test_tagged_release_contains_only_installers_and_checksums() -> None:
    workflow = (ROOT / ".github" / "workflows" / "desktop-build.yml").read_text(encoding="utf-8")

    assert "body_path: docs/RELEASE_NOTES_v0.2.0-beta.3.md" in workflow
    assert "In-place update did not close the running application" in workflow
    assert "prerelease: true" in workflow
    assert "release-assets/CodexHandoff-macOS-arm64.dmg" in workflow
    assert "release-assets/CodexHandoff-Windows-x64-Setup.exe" in workflow
    assert "release-assets/SHA256SUMS" in workflow
    assert "generate_release_notes" not in workflow
