# Desktop GUI and Installer Design

Date: 2026-08-07

Status: approved in conversation

Target release: `v0.2.0-beta.1`

## Objective

Turn Codex Handoff's functional beta GUI and portable Windows executable into a polished cross-platform desktop application with:

- a professional synchronization dashboard built with PySide6 Widgets;
- a guided first-run setup flow;
- platform-aware labels, paths, icons, and system integration;
- lightweight background update monitoring;
- a real per-user Windows installer;
- a conventional macOS application disk image;
- the approved Codex Handoff icon throughout the application and installation experience.

The synchronization core, encrypted artifact format, Google Drive provider, local provider, baseline protection, and explicit-confirmation model remain the foundation.

## Product Principles

1. Synchronization is explicit. A remote update is never applied without preview and confirmation.
2. Safety is visible. Codex process state, storage connection, baseline protection, and update state appear before primary actions.
3. Platform conventions matter. Windows and macOS use their own labels, paths, shortcuts, and application integration.
4. Background monitoring is lightweight. The app checks one small remote-head record, not full version history, during routine polling.
5. Recovery remains separate from daily synchronization. Version restore and protected-baseline restore have a dedicated view.
6. The application remains a quiet work tool. The design uses compact information hierarchy, restrained surfaces, and no decorative marketing content.

## Technical Approach

Keep PySide6 Widgets and the existing Python core. Introduce a focused presentation layer instead of moving to QML or an embedded web frontend.

Recommended module boundaries:

- `gui/app.py`: application startup, first-run routing, and high-level window creation;
- `gui/theme.py`: color, typography, spacing, stylesheet, and asset loading;
- `gui/platform.py`: platform labels, default paths, autostart, desktop shortcut, and application-location checks;
- `gui/setup.py`: four-step setup wizard;
- `gui/main_window.py`: dashboard shell, navigation, and tray lifecycle;
- `gui/views/`: synchronization, history, recovery, and settings views;
- `gui/widgets.py`: reusable status, version-row, empty-state, and progress widgets;
- `monitor.py`: remote-head polling, backoff, and update signals.

The split is limited to the GUI and platform behavior being changed. Core synchronization operations remain in `HandoffService`.

## Visual System

The approved application icon defines the palette:

- charcoal `#17252A`: application chrome and navigation;
- teal `#50D6C7` / darker interactive teal: outgoing synchronization, connected, and healthy states;
- coral `#FF7A66`: incoming synchronization and attention actions;
- gold `#F4C95D`: protected baseline and recovery state;
- neutral white and cool gray surfaces for dense operational content.

The interface uses the operating system's default UI font. Spacing follows an 8-pixel grid. Controls use a maximum 7-pixel radius. Focus, disabled, hover, pressed, error, and busy states remain visually distinct with accessible contrast.

The icon is packaged as:

- source SVG for maintenance;
- multi-resolution PNG files;
- multi-resolution Windows `.ico`;
- macOS `.icns`;
- a menu-bar-safe macOS tray variant where needed.

The primary icon appears in the app window, taskbar or Dock, tray or menu bar, Windows shortcuts, Start menu, installer, uninstaller, `.exe`, `.app`, and DMG presentation.

## Platform Adaptation

The GUI must not hardcode one platform's terminology or example paths.

| Concept | Windows | macOS |
| --- | --- | --- |
| Local device label | `This PC` | `This Mac` |
| Default Codex path | `C:\Users\<name>\.codex` | `/Users/<name>/.codex` |
| App data | `%LOCALAPPDATA%\Codex Handoff` | `~/Library/Application Support/Codex Handoff` |
| App icon container | `.ico` | `.icns` |
| Background location | system tray | menu bar / Dock |
| Desktop entry | Windows `.lnk` | Finder alias |
| Autostart | per-user Run entry | per-user LaunchAgent |

The current platform is detected from Python. The remote version stores an optional platform identifier for new snapshots. Older snapshots without this value remain readable and display a neutral device icon.

## Main Window

The selected design is a desktop operations dashboard.

### Shell

- Charcoal top bar with app icon, product name, current device, provider, and settings action.
- Left navigation with Synchronization, Version history, Recovery, and Settings.
- Main area with stable dimensions and no nested cards.
- Window state is remembered per user.

### Synchronization View

The first row shows three status blocks:

- Codex process: closed, running, or unavailable;
- storage: connected, connecting, offline, or error;
- protected baseline: protected or not created.

The route section shows local platform, configured provider, and latest remote source. Labels adapt to `This PC` or `This Mac`.

Primary actions:

- `Sync to cloud` publishes this device's encrypted version;
- `Sync from cloud` previews and applies the current remote version;
- `Preview update` is available only when a remote update exists;
- `Refresh` performs an immediate status and history refresh.

Recent versions appear in a compact table with version, source, platform, timestamp, and a menu for restore or details.

### Visible States

The main view explicitly represents:

- Connecting;
- Up to date;
- Update available;
- Waiting for Codex;
- Synchronizing;
- Offline;
- Error.

Long operations display their current stage and keep cancellation available while waiting for Codex. Controls do not resize when labels or progress change.

## Setup Wizard

Replace the single long setup form with four steps.

### Step 1: This Device

- Detect platform and hostname.
- Show platform label and default Codex path.
- Allow editing the device name and Codex directory.
- Hide workspace and diagnostic paths under Advanced settings.

### Step 2: Storage

- Google Drive is the default provider.
- Local folder remains available for testing or user-managed shared storage.
- Google Drive selection requests the Desktop OAuth JSON and tests authorization before completion.
- Provider-specific fields are shown only for the selected provider.

### Step 3: Recovery Key

- `Create new key` is the primary action for the first device.
- `Use existing key` connects another device.
- Existing baseline discovery changes the recommended action to `Use existing key`.
- Key loss and non-upload behavior are stated next to the choice, without exposing key contents.

### Step 4: Review

- Validate Codex path, workspace, provider connection, and recovery key.
- Offer `Create protected baseline` when storage has none.
- Offer `Connect to protected baseline` when one exists.
- Enable `Start with system` by default.
- Enable `Create desktop shortcut` by default.

On macOS, desktop shortcut creation occurs only after the app is outside a mounted DMG. If it is launched from `/Volumes`, the wizard tells the user to move it to `Applications` first. The resulting desktop item is a Finder alias, not a second application copy.

The same settings remain editable from the Settings view.

## Preview and Confirmation

An incoming update preview shows:

- version ID;
- source device and platform;
- creation time;
- counts and expandable lists for added, changed, removed, and unchanged files.

Removed files must be shown because applying a snapshot removes portable-profile files absent from that snapshot.

The confirmation states that Codex must be closed and that a local encrypted backup will be created. If Codex is running after confirmation, the operation enters `Waiting for Codex`, shows a cancellable banner, and starts automatically after Codex exits.

## Background Monitoring

Autostart is enabled by default and can be disabled in Settings.

Normal monitoring behavior:

1. Start minimized to the tray or menu bar when launched by the operating system.
2. Query only the remote `head.json` record every 60 seconds.
3. Fetch version history only when the head changes, the window opens, or the user refreshes.
4. Pause polling while another provider operation is active.
5. On network errors, retry after 2, 5, and then 15 minutes.
6. Reset to 60 seconds after a successful request or manual refresh.
7. Notify only once for each unseen remote version.

Closing the main window hides it while monitoring remains enabled. The first close displays a short system notification explaining that Codex Handoff is still running. `Quit` in the tray menu fully exits. The tray menu also provides Show, Sync to cloud, Sync from cloud, Check now, and Quit.

Routine background polling must use a provider method that locates only `head.json`; the Google Drive provider must not list the whole app folder three times per cycle.

## Error Handling

- Offline and OAuth refresh failures preserve the last known state and show a retry action.
- A stale device receives a direct `Sync from cloud first` action; no force-publish control is added.
- Integrity, decryption, and unsafe-path failures stop before apply and identify the failed stage.
- Failed apply operations retain the local backup and attempt automatic rollback.
- Autostart or shortcut creation failure does not invalidate synchronization setup; the user gets a specific warning and a retry action in Settings.
- Unsupported application location on macOS blocks desktop-alias creation but not the rest of setup.

## Windows Distribution

The release provides one Windows artifact so users cannot confuse a portable executable with an installer.

`CodexHandoff-Windows-x64-Setup.exe` is the recommended download. Inno Setup packages a PyInstaller onedir application and:

- installs per user under `%LOCALAPPDATA%\Programs\Codex Handoff` without administrator privileges;
- embeds application name, version, publisher, and the approved icon;
- creates Start menu and uninstall entries;
- creates a desktop shortcut by default;
- enables per-user autostart by default;
- optionally launches Codex Handoff after installation;
- supports clean uninstall while retaining user snapshots, keys, and configuration unless the user explicitly chooses data removal in a future feature.

## macOS Distribution

`CodexHandoff-macOS-arm64.dmg` contains:

- `CodexHandoff.app` with the approved `.icns` icon;
- an `Applications` alias for drag-to-install;
- a styled volume presentation sized for the app-to-Applications flow.

The first-run wizard creates the Desktop Finder alias by default after confirming that the application is not running from the mounted DMG. Autostart uses a per-user LaunchAgent and starts the app in background mode.

The beta remains unsigned, so Gatekeeper may warn on first launch. Documentation must keep the unsigned-build instructions explicit.

## Compatibility and Data Model

New platform metadata is optional when reading manifests and heads. Existing `v0.1.0-beta.1` baseline and version artifacts remain readable.

Configuration gains backward-compatible defaults for:

- monitoring enabled;
- 60-second polling interval;
- autostart enabled;
- minimize to tray enabled;
- close-notification acknowledgement.

No existing recovery key or encrypted artifact format is invalidated.

## Testing

### Unit and Integration Tests

- platform labels and default paths for Windows and macOS;
- backward-compatible configuration and manifest loading;
- added, changed, removed, and unchanged preview lists;
- monitor timing, pause, backoff, reset, and duplicate-notification behavior;
- tray close, show, and quit lifecycle;
- autostart and desktop-shortcut adapters with mocked operating-system calls;
- existing encrypted local-provider end-to-end synchronization flow.

### GUI Tests

- wizard navigation, validation, conditional provider fields, and review state;
- dashboard status rendering for every declared state;
- stable layouts at minimum and default window sizes;
- offscreen screenshots for setup and dashboard on CI;
- icon loading and non-null window/tray icons.

### Packaging Tests

- Windows installer compilation with Inno Setup;
- silent installer smoke test in a disposable CI user environment;
- installed executable, Start menu entry, desktop shortcut, autostart entry, and uninstaller existence;
- macOS `.app` launch smoke test and bundle icon validation;
- DMG contents include `.app` and Applications alias;
- SHA-256 checksums for all release files.

Physical Windows and Apple Silicon macOS validation remains required before marking the release stable.

## Release Plan

Publish a new prerelease `v0.2.0-beta.1`; do not replace or mutate the previous beta binaries.

Release assets:

- `CodexHandoff-Windows-x64-Setup.exe`;
- `CodexHandoff-macOS-arm64.dmg`;
- `SHA256SUMS`.

The release notes state clearly that the Windows file is an installer, explain the desktop shortcut and autostart behavior, and note that both builds remain unsigned.

## Acceptance Criteria

The design is complete when:

1. The chosen dashboard and four-step setup wizard are implemented with platform-aware labels and paths.
2. The approved icon appears in all application, shortcut, installer, and package locations described above.
3. Windows installation creates working desktop and Start menu shortcuts, autostart, and uninstall support.
4. macOS installation provides drag-to-Applications and creates a working Desktop Finder alias after first-run approval.
5. Background monitoring performs one lightweight head query per interval and uses documented backoff.
6. Update preview reports removed files before confirmation.
7. Existing beta artifacts and configuration remain readable.
8. Automated tests and packaging smoke checks pass on GitHub Actions.
9. The new unsigned artifacts are attached to `v0.2.0-beta.1` as a GitHub prerelease.
