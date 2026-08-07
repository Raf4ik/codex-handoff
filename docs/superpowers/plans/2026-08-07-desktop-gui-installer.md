# Desktop GUI and Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver `v0.2.0-beta.1` with the approved cross-platform dashboard, guided setup, app icon, lightweight monitoring, Windows installer, macOS DMG, desktop shortcuts, autostart, and GitHub Release documentation.

**Architecture:** Keep the encrypted synchronization core and provider interface, add backward-compatible platform metadata and preview details, and split the current GUI into focused PySide6 Widget modules. Add a lightweight remote-head monitor and isolated operating-system integration adapters, then package the same application as an Inno Setup installer on Windows and an application DMG on Apple Silicon macOS.

**Tech Stack:** Python 3.11+, PySide6 Widgets, Google Drive API, cryptography, platformdirs, PyInstaller, Pillow, Inno Setup, GitHub Actions, pytest.

---

## File Map

Create:

- `src/codex_handoff/assets/__init__.py` — packaged asset marker.
- `src/codex_handoff/assets/codex-handoff.svg` — approved scalable source icon.
- `src/codex_handoff/assets/codex-handoff.png` — runtime 1024px icon.
- `src/codex_handoff/gui/theme.py` — design tokens, stylesheet, and icon loader.
- `src/codex_handoff/gui/platform.py` — platform labels, paths, autostart, desktop shortcuts.
- `src/codex_handoff/gui/widgets.py` — status and action widgets.
- `src/codex_handoff/gui/setup.py` — four-step setup wizard.
- `src/codex_handoff/gui/main_window.py` — dashboard, navigation, tray behavior.
- `src/codex_handoff/monitor.py` — polling schedule and remote-head monitor.
- `packaging/build_icons.py` — generate PNG, ICO, and macOS iconset inputs.
- `packaging/codex-handoff.iss` — per-user Inno Setup definition.
- `packaging/macos-dmg.sh` — stage `.app`, Applications alias, and DMG.
- `tests/test_platform_integration.py` — platform-specific paths and integration calls.
- `tests/test_monitor.py` — polling and backoff.
- `tests/test_gui_dashboard.py` — dashboard states and tray lifecycle.
- `tests/test_setup_wizard.py` — wizard navigation and validation.
- `docs/RELEASE_NOTES_v0.2.0-beta.1.md` — bilingual prerelease notes.

Modify:

- `pyproject.toml` — version, package assets, Pillow packaging dependency.
- `src/codex_handoff/models.py` — optional source platform and removed preview entries.
- `src/codex_handoff/config.py` — backward-compatible desktop preferences.
- `src/codex_handoff/artifacts.py` — platform metadata and removed-file preview.
- `src/codex_handoff/service.py` — lightweight remote-head access.
- `src/codex_handoff/providers/google_drive.py` — direct named-file queries.
- `src/codex_handoff/gui/app.py` — startup and background launch routing.
- `src/codex_handoff/gui/__main__.py` — background argument support.
- `packaging/codex_handoff_gui.py` — packaged startup.
- `.github/workflows/desktop-build.yml` — icons, installer, DMG, smoke tests, checksums.
- `tests/test_artifacts.py`, `tests/test_config.py`, `tests/test_google_drive_provider.py`, `tests/test_gui_smoke.py`, `tests/test_gui_wait.py` — compatibility and regression coverage.
- `README.md`, `docs/BUILDING.md`, `PRIVACY.md` — installation, background behavior, release files.

## Task 1: Version and Approved Icon Assets

**Files:**

- Create: `src/codex_handoff/assets/__init__.py`
- Create: `src/codex_handoff/assets/codex-handoff.svg`
- Create: `src/codex_handoff/assets/codex-handoff.png`
- Create: `packaging/build_icons.py`
- Modify: `pyproject.toml`
- Test: `tests/test_gui_smoke.py`

- [ ] **Step 1: Write the failing asset test**

```python
from codex_handoff.gui.theme import app_icon_path


def test_packaged_runtime_icon_exists() -> None:
    icon = app_icon_path()
    assert icon.is_file()
    assert icon.name == "codex-handoff.png"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_gui_smoke.py::test_packaged_runtime_icon_exists -q`

Expected: FAIL because `codex_handoff.gui.theme` does not exist.

- [ ] **Step 3: Add the approved SVG and icon generation script**

Copy the approved SVG geometry into `src/codex_handoff/assets/codex-handoff.svg`. Implement `packaging/build_icons.py` with these stable outputs:

```python
from pathlib import Path
import sys

from PIL import Image
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "codex_handoff" / "assets"


def render(size: int, destination: Path) -> None:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    QSvgRenderer(str(ASSETS / "codex-handoff.svg")).render(
        painter, QRectF(0, 0, size, size)
    )
    painter.end()
    if not image.save(str(destination)):
        raise RuntimeError(f"Unable to write {destination}")


def main() -> int:
    output = ROOT / "build" / "icons"
    output.mkdir(parents=True, exist_ok=True)
    render(1024, ASSETS / "codex-handoff.png")
    for size in (16, 24, 32, 48, 64, 128, 256):
        path = output / f"icon-{size}.png"
        render(size, path)
    source = Image.open(ASSETS / "codex-handoff.png").convert("RGBA")
    source.save(
        output / "codex-handoff.ico",
        format="ICO",
        sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Package assets and expose the runtime path**

Add Pillow to `[project.optional-dependencies].packaging`, add `pytest-qt>=4.4` to the development dependencies, include `assets/*.png` and `assets/*.svg` as package data, set version to `0.2.0b1`, and create `theme.app_icon_path()` using `importlib.resources.files("codex_handoff.assets")`.

- [ ] **Step 5: Generate assets and rerun the test**

Run: `.venv/bin/python packaging/build_icons.py && QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_gui_smoke.py::test_packaged_runtime_icon_exists -q`

Expected: PASS and `file build/icons/codex-handoff.ico` reports a Windows icon.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml packaging/build_icons.py src/codex_handoff/assets src/codex_handoff/gui/theme.py tests/test_gui_smoke.py
git commit -m "feat: add branded application assets"
```

## Task 2: Backward-Compatible Platform Metadata and Preview

**Files:**

- Modify: `src/codex_handoff/models.py`
- Modify: `src/codex_handoff/artifacts.py`
- Modify: `src/codex_handoff/service.py`
- Modify: `src/codex_handoff/providers/google_drive.py`
- Modify: `src/codex_handoff/providers/local.py`
- Test: `tests/test_artifacts.py`
- Test: `tests/test_handoff_flow.py`

- [ ] **Step 1: Add failing compatibility and removed-file tests**

```python
def test_preview_reports_portable_file_removed_by_apply(tmp_path: Path) -> None:
    target = tmp_path / "target"
    (target / "sessions").mkdir(parents=True)
    (target / "sessions" / "removed.json").write_text("old")
    source = tmp_path / "source"
    (source / "sessions").mkdir(parents=True)
    artifact = tmp_path / "version.zip"
    build_artifact(source, artifact, version_id="v1", parent_version=None, device_id="mac")
    preview = preview_artifact(artifact, target)
    assert preview.removed == ("sessions/removed.json",)


def test_old_manifest_without_source_platform_is_readable(old_manifest_zip: Path) -> None:
    manifest = read_manifest(old_manifest_zip)
    assert manifest.source_platform is None
```

- [ ] **Step 2: Verify both tests fail**

Run: `.venv/bin/python -m pytest tests/test_artifacts.py -q`

Expected: FAIL because `ApplyPreview.removed` and `SnapshotManifest.source_platform` are absent.

- [ ] **Step 3: Extend models with defaults**

```python
@dataclass(frozen=True, slots=True)
class SnapshotManifest:
    version_id: str
    parent_version: str | None
    source_device: str
    profile: str
    created_at: str
    files: tuple[FileEntry, ...] = field(default_factory=tuple)
    source_platform: str | None = None


@dataclass(frozen=True, slots=True)
class RemoteHead:
    version_id: str
    parent_version: str | None
    source_device: str
    created_at: str
    source_platform: str | None = None


@dataclass(frozen=True, slots=True)
class ApplyPreview:
    version_id: str
    source_device: str
    added: tuple[str, ...]
    changed: tuple[str, ...]
    unchanged: tuple[str, ...]
    removed: tuple[str, ...] = field(default_factory=tuple)
```

- [ ] **Step 4: Populate platform metadata and removed paths**

Use `platform.system().lower()` when building new manifests. In `preview_artifact`, compute current portable paths minus manifest paths and return the sorted result as `removed`. Read optional JSON fields with `.get("source_platform")` in every provider and artifact parser.

- [ ] **Step 5: Run artifact and synchronization tests**

Run: `.venv/bin/python -m pytest tests/test_artifacts.py tests/test_handoff_flow.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/codex_handoff/models.py src/codex_handoff/artifacts.py src/codex_handoff/service.py src/codex_handoff/providers tests/test_artifacts.py tests/test_handoff_flow.py
git commit -m "feat: add platform metadata and complete previews"
```

## Task 3: Desktop Preferences and Platform Integration

**Files:**

- Create: `src/codex_handoff/gui/platform.py`
- Modify: `src/codex_handoff/config.py`
- Test: `tests/test_config.py`
- Create: `tests/test_platform_integration.py`

- [ ] **Step 1: Write failing configuration and platform tests**

```python
def test_old_config_gets_desktop_defaults(config_json: Path) -> None:
    config = load_config(config_json)
    assert config.monitoring_enabled is True
    assert config.poll_interval_seconds == 60
    assert config.autostart_enabled is True
    assert config.minimize_to_tray is True


def test_windows_platform_info(monkeypatch) -> None:
    monkeypatch.setattr(platform_module.sys, "platform", "win32")
    info = platform_module.current_platform()
    assert info.local_label == "This PC"
    assert info.codex_dir.name == ".codex"


def test_macos_desktop_shortcut_rejects_mounted_dmg(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(platform_module.sys, "platform", "darwin")
    with pytest.raises(PlatformIntegrationError, match="Applications"):
        platform_module.create_desktop_shortcut(Path("/Volumes/CodexHandoff/CodexHandoff.app"))
```

- [ ] **Step 2: Run tests and verify failure**

Run: `.venv/bin/python -m pytest tests/test_config.py tests/test_platform_integration.py -q`

Expected: FAIL because preference fields and platform adapters do not exist.

- [ ] **Step 3: Add backward-compatible preferences**

Append defaulted fields to `AppConfig`:

```python
monitoring_enabled: bool = True
poll_interval_seconds: int = 60
autostart_enabled: bool = True
minimize_to_tray: bool = True
close_notice_seen: bool = False
```

Load them with `raw.get(...)`, validate the interval is at least 30 seconds, and persist them through existing `asdict` serialization.

- [ ] **Step 4: Implement isolated operating-system adapters**

Define the platform value and public dispatch functions as follows, then keep registry, plist, PowerShell, and AppleScript details in private helpers so tests can mock them independently:

```python
@dataclass(frozen=True, slots=True)
class PlatformInfo:
    key: str
    local_label: str
    display_name: str
    codex_dir: Path
    app_data_dir: Path


def current_platform() -> PlatformInfo:
    if sys.platform.startswith("win"):
        return PlatformInfo("windows", "This PC", "Windows PC", Path.home() / ".codex", default_workspace())
    if sys.platform == "darwin":
        return PlatformInfo("macos", "This Mac", "Mac", Path.home() / ".codex", default_workspace())
    return PlatformInfo("other", "This device", platform.system(), Path.home() / ".codex", default_workspace())


def set_autostart(enabled: bool, executable: Path) -> None:
    if sys.platform.startswith("win"):
        _set_windows_autostart(enabled, executable)
    elif sys.platform == "darwin":
        _set_macos_autostart(enabled)


def create_desktop_shortcut(executable: Path) -> Path:
    if sys.platform.startswith("win"):
        return _create_windows_shortcut(executable)
    if sys.platform == "darwin":
        return _create_macos_alias(executable)
    raise PlatformIntegrationError("Desktop shortcuts are unsupported on this platform")
```

Use `winreg.HKEY_CURRENT_USER` and a quoted `--background` command on Windows. Use `~/Library/LaunchAgents/com.codexhandoff.desktop.plist` with `/usr/bin/open -gj -a "Codex Handoff"` on macOS. Use PowerShell `WScript.Shell.CreateShortcut` for Windows `.lnk`; use Finder through `osascript` for the macOS alias after rejecting `/Volumes/...` paths.

- [ ] **Step 5: Run focused tests**

Run: `.venv/bin/python -m pytest tests/test_config.py tests/test_platform_integration.py -q`

Expected: PASS with OS writes mocked.

- [ ] **Step 6: Commit**

```bash
git add src/codex_handoff/config.py src/codex_handoff/gui/platform.py tests/test_config.py tests/test_platform_integration.py
git commit -m "feat: add desktop platform integration"
```

## Task 4: Efficient Remote-Head Monitoring

**Files:**

- Create: `src/codex_handoff/monitor.py`
- Modify: `src/codex_handoff/service.py`
- Modify: `src/codex_handoff/providers/google_drive.py`
- Test: `tests/test_google_drive_provider.py`
- Create: `tests/test_monitor.py`

- [ ] **Step 1: Write failing direct-query and backoff tests**

```python
def test_success_resets_poll_schedule() -> None:
    schedule = PollSchedule(normal_seconds=60)
    assert schedule.failure() == 120
    assert schedule.failure() == 300
    assert schedule.failure() == 900
    assert schedule.success() == 60


def test_background_head_check_does_not_list_version_history(provider) -> None:
    provider.read_head()
    provider.service.files().list.assert_called_once()
    query = provider.service.files().list.call_args.kwargs["q"]
    assert "name='head.json'" in query
```

- [ ] **Step 2: Verify failures**

Run: `.venv/bin/python -m pytest tests/test_monitor.py tests/test_google_drive_provider.py -q`

Expected: FAIL because `PollSchedule` is absent and Google Drive lists the whole folder.

- [ ] **Step 3: Implement deterministic schedule**

```python
class PollSchedule:
    def __init__(self, normal_seconds: int = 60) -> None:
        self.normal_seconds = normal_seconds
        self._failures = 0

    def success(self) -> int:
        self._failures = 0
        return self.normal_seconds

    def failure(self) -> int:
        delays = (120, 300, 900)
        delay = delays[min(self._failures, len(delays) - 1)]
        self._failures += 1
        return delay
```

Add `HandoffService.remote_head()` and a Qt `RemoteHeadMonitor` that emits `head_changed`, `offline`, and `recovered`, pauses during operations, and schedules its next single-shot timer from `PollSchedule`.

- [ ] **Step 4: Query Google Drive by exact name**

Add `_find_named_file(name)` with a Drive query containing parent, escaped name, and `trashed=false`. Make `_head_file()` use it. Keep full folder enumeration only for baseline and history operations.

- [ ] **Step 5: Run focused tests**

Run: `.venv/bin/python -m pytest tests/test_monitor.py tests/test_google_drive_provider.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/codex_handoff/monitor.py src/codex_handoff/service.py src/codex_handoff/providers/google_drive.py tests/test_monitor.py tests/test_google_drive_provider.py
git commit -m "feat: add lightweight update monitoring"
```

## Task 5: Theme and Reusable Dashboard Widgets

**Files:**

- Modify: `src/codex_handoff/gui/theme.py`
- Create: `src/codex_handoff/gui/widgets.py`
- Test: `tests/test_gui_dashboard.py`

- [ ] **Step 1: Write failing widget-state tests**

```python
def test_status_widget_exposes_semantic_state(qapp) -> None:
    widget = StatusBlock("Codex process")
    widget.set_state("Closed · ready", StatusTone.SUCCESS)
    assert widget.property("tone") == "success"
    assert widget.value_label.text() == "Closed · ready"


def test_action_button_has_stable_height(qapp) -> None:
    button = ActionButton("Sync to cloud", tone="primary")
    assert button.minimumHeight() == button.maximumHeight() == 40
```

- [ ] **Step 2: Verify failure**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_gui_dashboard.py -q`

Expected: FAIL because dashboard widgets do not exist.

- [ ] **Step 3: Implement design tokens and stylesheet**

Define `CHARCOAL`, `TEAL`, `CORAL`, `GOLD`, neutral colors, 8-pixel spacing helpers, `load_app_icon()`, and a single Qt stylesheet covering focus, hover, pressed, disabled, error, tables, navigation, dialogs, and tooltips. Use 7px or smaller radii.

- [ ] **Step 4: Implement focused widgets**

Create `StatusTone(Enum)`, `StatusBlock`, `ActionButton`, `NavigationButton`, `SyncRoute`, `VersionTable`, and `OperationBanner`. Use fixed control heights and word-wrapped dynamic text so status changes cannot shift the layout.

- [ ] **Step 5: Run widget tests**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_gui_dashboard.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/codex_handoff/gui/theme.py src/codex_handoff/gui/widgets.py tests/test_gui_dashboard.py
git commit -m "feat: add desktop visual system"
```

## Task 6: Four-Step Setup Wizard

**Files:**

- Create: `src/codex_handoff/gui/setup.py`
- Modify: `src/codex_handoff/gui/app.py`
- Replace: `tests/test_gui_smoke.py`
- Create: `tests/test_setup_wizard.py`

- [ ] **Step 1: Write failing wizard navigation tests**

```python
def test_setup_wizard_starts_with_platform_defaults(qapp, tmp_path: Path) -> None:
    wizard = SetupWizard(tmp_path / "config.json")
    assert wizard.current_step == 0
    assert wizard.device_page.source.text().endswith(".codex")
    assert wizard.storage_page.provider.currentData() == "google_drive"
    assert wizard.review_page.autostart.isChecked()
    assert wizard.review_page.desktop_shortcut.isChecked()


def test_local_provider_hides_google_credentials(qapp, tmp_path: Path) -> None:
    wizard = SetupWizard(tmp_path / "config.json")
    wizard.storage_page.provider.setCurrentIndex(1)
    assert wizard.storage_page.local_folder_row.isVisibleTo(wizard.storage_page)
    assert not wizard.storage_page.oauth_row.isVisibleTo(wizard.storage_page)
```

- [ ] **Step 2: Verify failure**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_setup_wizard.py -q`

Expected: FAIL because `SetupWizard` does not exist.

- [ ] **Step 3: Build wizard pages and navigation**

Implement `DevicePage`, `StoragePage`, `RecoveryPage`, `ReviewPage`, and `SetupWizard`. Keep existing field attribute names where practical for compatibility, validate only the current step on Continue, and perform provider connection validation in a worker so the UI never blocks.

- [ ] **Step 4: Apply platform integration at completion**

Save configuration first. Then call `set_autostart` and `create_desktop_shortcut` according to checked options. Surface an integration failure as a non-fatal warning with a Settings retry path. Create or connect to the baseline only after provider and key validation.

- [ ] **Step 5: Run wizard and legacy GUI tests**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_setup_wizard.py tests/test_gui_smoke.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/codex_handoff/gui/setup.py src/codex_handoff/gui/app.py tests/test_setup_wizard.py tests/test_gui_smoke.py
git commit -m "feat: add guided desktop setup"
```

## Task 7: Dashboard, Preview, and Tray Lifecycle

**Files:**

- Create: `src/codex_handoff/gui/main_window.py`
- Modify: `src/codex_handoff/gui/app.py`
- Modify: `src/codex_handoff/gui/__main__.py`
- Modify: `packaging/codex_handoff_gui.py`
- Test: `tests/test_gui_dashboard.py`
- Modify: `tests/test_gui_wait.py`

- [ ] **Step 1: Write failing dashboard and close tests**

```python
def test_dashboard_uses_platform_label(window) -> None:
    assert window.sync_view.local_device_title.text() in {"This PC", "This Mac"}


def test_update_preview_includes_removed_files(window, preview) -> None:
    preview = replace(preview, removed=("sessions/old.json",))
    dialog = window.build_preview_dialog(preview)
    assert dialog.removed_count.text() == "1"


def test_close_hides_to_tray_when_monitoring(window, qtbot) -> None:
    window.config = replace(window.config, monitoring_enabled=True, minimize_to_tray=True)
    window.close()
    assert not window.isVisible()
    assert QApplication.instance().closingDown() is False
```

- [ ] **Step 2: Verify failure**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_gui_dashboard.py tests/test_gui_wait.py -q`

Expected: FAIL because the dashboard and tray lifecycle are absent.

- [ ] **Step 3: Implement the dashboard views**

Build `MainWindow` with fixed sidebar navigation and stacked Synchronization, Version history, Recovery, and Settings views. Map service status to the declared semantic states. Use `current_platform()` for local labels and optional remote platform metadata for the other device.

- [ ] **Step 4: Implement complete preview and operation feedback**

Replace the count-only message box with a modal containing Added, Changed, Removed, and Unchanged tabs. Keep explicit confirmation. Show `OperationBanner` for waiting, syncing, offline, and errors. Pause the monitor while workers run and resume it on success or failure.

- [ ] **Step 5: Implement tray lifecycle and background launch**

Set `QApplication.setQuitOnLastWindowClosed(False)`. Add tray actions Show, Sync to cloud, Sync from cloud, Check now, and Quit. Override `closeEvent` to hide when enabled and show the one-time notification. Parse `--background` so OS autostart creates the window without showing it.

- [ ] **Step 6: Run all GUI tests and capture offscreen previews**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_gui_dashboard.py tests/test_gui_wait.py tests/test_setup_wizard.py tests/test_gui_smoke.py -q`

Expected: PASS and both setup/dashboard screenshot helpers produce nonblank PNGs with their expected dimensions.

- [ ] **Step 7: Commit**

```bash
git add src/codex_handoff/gui packaging/codex_handoff_gui.py tests/test_gui_dashboard.py tests/test_gui_wait.py tests/test_setup_wizard.py tests/test_gui_smoke.py
git commit -m "feat: build synchronization dashboard"
```

## Task 8: Windows Installer

**Files:**

- Create: `packaging/codex-handoff.iss`
- Modify: `.github/workflows/desktop-build.yml`
- Modify: `docs/BUILDING.md`

- [ ] **Step 1: Define the per-user Inno Setup package**

Use these required directives and entries:

```ini
[Setup]
AppId={{6E2688C5-5C79-4E71-AF94-1BA8D615A37D}
AppName=Codex Handoff
AppVersion=0.2.0-beta.1
DefaultDirName={localappdata}\Programs\Codex Handoff
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=build\icons\codex-handoff.ico
UninstallDisplayIcon={app}\CodexHandoff.exe
OutputBaseFilename=CodexHandoff-Windows-x64-Setup

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: checkedonce
Name: "autostart"; Description: "Start Codex Handoff with Windows"; Flags: checkedonce

[Icons]
Name: "{autoprograms}\Codex Handoff"; Filename: "{app}\CodexHandoff.exe"
Name: "{autodesktop}\Codex Handoff"; Filename: "{app}\CodexHandoff.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Codex Handoff"; ValueData: "\"{app}\CodexHandoff.exe\" --background"; Tasks: autostart; Flags: uninsdeletevalue
```

- [ ] **Step 2: Build PyInstaller onedir and compile installer in CI**

Use `--icon build/icons/codex-handoff.ico`, version metadata, and collected Google modules. Compile with `iscc packaging/codex-handoff.iss`. Do not publish a one-file portable executable.

- [ ] **Step 3: Add silent installer smoke checks**

Install with `/VERYSILENT /CURRENTUSER /TASKS="desktopicon,autostart"`, assert the installed executable, desktop `.lnk`, Start menu `.lnk`, Run registry value, and uninstaller exist, launch the app with `--background`, then invoke the uninstaller silently.

- [ ] **Step 4: Document Windows installation**

Update BUILDING and README to say that the `.exe` is a real per-user installer, what it creates, how to uninstall it, and that user data is retained.

- [ ] **Step 5: Commit**

```bash
git add packaging/codex-handoff.iss .github/workflows/desktop-build.yml docs/BUILDING.md README.md
git commit -m "feat: add Windows desktop installer"
```

## Task 9: macOS App, DMG, Desktop Alias, and Icons

**Files:**

- Create: `packaging/macos-dmg.sh`
- Modify: `packaging/build_icons.py`
- Modify: `.github/workflows/desktop-build.yml`
- Modify: `docs/BUILDING.md`

- [ ] **Step 1: Generate the full macOS iconset**

Extend `build_icons.py` to emit `icon_16x16.png`, `icon_16x16@2x.png`, through `icon_512x512@2x.png` in `build/icons/CodexHandoff.iconset`. On macOS run:

```bash
iconutil -c icns build/icons/CodexHandoff.iconset -o build/icons/CodexHandoff.icns
```

- [ ] **Step 2: Use the `.icns` in PyInstaller**

Build the app with `--icon build/icons/CodexHandoff.icns`, bundle identifier `com.codexhandoff.desktop`, and version `0.2.0-beta.1`. Assert `Contents/Resources/CodexHandoff.icns` and the bundle icon metadata exist.

- [ ] **Step 3: Build a conventional DMG**

Implement `packaging/macos-dmg.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
stage="dist/dmg-stage"
rm -rf "$stage"
mkdir -p "$stage"
cp -R dist/CodexHandoff.app "$stage/CodexHandoff.app"
ln -s /Applications "$stage/Applications"
hdiutil create -volname "Codex Handoff" -srcfolder "$stage" \
  -ov -format UDZO dist/CodexHandoff-macOS-arm64.dmg
```

- [ ] **Step 4: Verify DMG contents and application launch**

Mount the DMG in CI, assert `CodexHandoff.app` and `Applications` exist, unmount, and run the app binary with `--background` long enough to confirm the process starts without an immediate crash.

- [ ] **Step 5: Document desktop alias behavior**

Explain that the first-run checked option creates a Finder alias on the Desktop only after the app is moved from the DMG to Applications. State the unsigned Gatekeeper limitation.

- [ ] **Step 6: Commit**

```bash
git add packaging/build_icons.py packaging/macos-dmg.sh .github/workflows/desktop-build.yml docs/BUILDING.md README.md
git commit -m "feat: package branded macOS application"
```

## Task 10: Full Validation and Release Documentation

**Files:**

- Create: `docs/RELEASE_NOTES_v0.2.0-beta.1.md`
- Modify: `README.md`
- Modify: `PRIVACY.md`
- Modify: `.github/workflows/desktop-build.yml`

- [ ] **Step 1: Write bilingual release notes**

Include English first and Russian second. Cover the dashboard, setup wizard, platform-aware paths, icon integration, Windows installation, macOS desktop alias, autostart, 60-second lightweight monitoring, complete update preview, backward compatibility, unsigned-build warnings, and the remaining physical Google Drive validation requirement.

- [ ] **Step 2: Make tagged release output deterministic**

Have the release job download only `CodexHandoff-Windows-x64-Setup.exe` and `CodexHandoff-macOS-arm64.dmg`, generate `SHA256SUMS`, and pass `body_path: docs/RELEASE_NOTES_v0.2.0-beta.1.md` plus `prerelease: true` to `softprops/action-gh-release`.

- [ ] **Step 3: Run the complete local suite**

Run:

```bash
git diff --check
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/python -m build
```

Expected: all tests pass, source and wheel builds succeed, and no whitespace errors appear.

- [ ] **Step 4: Inspect the rendered GUI locally**

Render setup and dashboard at 1280×800 and 1024×700 offscreen. Inspect both images for nonblank content, clipped paths, overlapping labels, disabled-state contrast, stable buttons, and the approved icon. Fix and repeat until both pass visual review.

- [ ] **Step 5: Commit release documentation**

```bash
git add README.md PRIVACY.md docs/RELEASE_NOTES_v0.2.0-beta.1.md .github/workflows/desktop-build.yml
git commit -m "docs: prepare v0.2.0 beta release"
```

## Task 11: Publish and Verify `v0.2.0-beta.1`

**Files:** none beyond the committed implementation.

- [ ] **Step 1: Push the implementation branch and open a pull request**

```bash
git push -u origin codex/gui-installer-design
gh pr create --draft --base main --head codex/gui-installer-design \
  --title "[codex] Build desktop GUI and installers" \
  --body-file docs/RELEASE_NOTES_v0.2.0-beta.1.md
```

The PR body must summarize behavior, safety changes, platform packaging, tests, and unsigned beta limitations.

- [ ] **Step 2: Wait for all macOS and Windows checks**

Run: `gh pr checks --watch --interval 10`

Expected: every Python 3.11/3.12 CI job and packaging job passes.

- [ ] **Step 3: Mark ready and merge**

Run:

```bash
gh pr ready
gh pr merge --squash
git switch main
git pull --ff-only origin main
```

Expected: `main` contains the merged implementation and the worktree is clean.

- [ ] **Step 4: Tag without replacing the previous beta**

```bash
git tag -a v0.2.0-beta.1 -m "Codex Handoff v0.2.0 Beta 1"
git push origin v0.2.0-beta.1
```

- [ ] **Step 5: Wait for release builds and verify assets**

Run:

```bash
release_run_id="$(gh run list --repo Raf4ik/codex-handoff --workflow 'Desktop builds' \
  --branch v0.2.0-beta.1 --limit 1 --json databaseId --jq '.[0].databaseId')"
gh run watch "$release_run_id" --repo Raf4ik/codex-handoff --exit-status
gh release view v0.2.0-beta.1 --repo Raf4ik/codex-handoff --json isPrerelease,body,assets,url
```

Expected:

- prerelease is `true`;
- release body contains both English and Russian sections;
- exactly `CodexHandoff-Windows-x64-Setup.exe`, `CodexHandoff-macOS-arm64.dmg`, and `SHA256SUMS` are attached;
- no portable executable is attached.

- [ ] **Step 6: Report residual validation honestly**

State that automated packaging and smoke tests passed. Do not call the release stable until a person completes a physical Windows install/uninstall, macOS drag-install/Desktop alias check, and a real Google Drive Mac-to-Windows-to-Mac synchronization cycle.
