# Desktop Builds

Codex Handoff bundles Python, Qt, and its runtime dependencies. End users install a normal platform package and do not install Python separately.

## Release Artifacts

The **Desktop builds** GitHub Actions workflow produces exactly these public release files:

- `CodexHandoff-macOS-arm64.dmg` for Apple Silicon Macs (M1 or newer);
- `CodexHandoff-Windows-x64-Setup.exe` for 64-bit Windows 10 or newer;
- `SHA256SUMS` containing SHA-256 checksums for both downloads.

The Windows artifact is a per-user Inno Setup installer, not a portable executable. It installs under `%LOCALAPPDATA%\Programs\Codex Handoff`, creates Start menu and Desktop shortcuts, registers optional current-user autostart, and provides `unins000.exe` plus a Windows Settings uninstall entry. The default installer tasks enable the Desktop shortcut and autostart. Uninstall removes the installed application and OS integration but retains user configuration, keys, and backups.

The macOS DMG contains `CodexHandoff.app` and an `Applications` alias. Drag the app to Applications before launching it. The first-run wizard can then create a Finder alias on the user's Desktop. It refuses to create an alias that points into a mounted `/Volumes/...` DMG because that target disappears after ejecting the image.

## GitHub Actions

Run **Desktop builds** manually from the Actions tab to test both platform packages. Pushing a version tag such as `v0.2.0-beta.4` builds the same artifacts, performs platform smoke tests, generates `SHA256SUMS`, and publishes a GitHub prerelease using the bilingual release notes in the repository.

The macOS job verifies the Apple Silicon runner architecture, app icon metadata, app startup, and mounted DMG contents. The Windows job silently installs the Setup package, verifies the executable, shortcuts, autostart registry value, and uninstaller, starts the installed application, updates that running installation in place, launches the updated copy, uninstalls it, and verifies cleanup.

Installed builds use the public GitHub Releases API for low-frequency update checks. Packages are selected by platform and verified with the release `SHA256SUMS`. Windows reuses the Inno Setup App ID and installation directory. macOS uses a detached replacement helper with a temporary rollback bundle. Both download and installation remain user-confirmed actions.

## Local macOS Build

Run on an Apple Silicon Mac with Python 3.11 or newer:

```bash
python -m venv .venv
.venv/bin/python -m pip install '.[packaging]'
.venv/bin/python packaging/build_icons.py
iconutil -c icns build/icons/CodexHandoff.iconset \
  -o build/icons/CodexHandoff.icns
.venv/bin/python -m PyInstaller --noconfirm --clean --windowed \
  --name CodexHandoff \
  --osx-bundle-identifier com.codexhandoff.desktop \
  --icon build/icons/CodexHandoff.icns \
  --collect-data codex_handoff \
  --collect-submodules googleapiclient \
  --collect-submodules google_auth_oauthlib \
  packaging/codex_handoff_gui.py
packaging/macos-dmg.sh
```

The outputs are `dist/CodexHandoff.app` and `dist/CodexHandoff-macOS-arm64.dmg`.

## Local Windows Build

Run in 64-bit Windows with Python 3.11 or newer and Inno Setup 6 installed:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install ".[packaging]"
.venv\Scripts\python.exe packaging\build_icons.py
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed `
  --name CodexHandoff `
  --onedir `
  --icon build\icons\codex-handoff.ico `
  --version-file packaging\windows-version-info.txt `
  --collect-data codex_handoff `
  --collect-submodules googleapiclient `
  --collect-submodules google_auth_oauthlib `
  packaging\codex_handoff_gui.py
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" packaging\codex-handoff.iss
```

The output is `dist\CodexHandoff-Windows-x64-Setup.exe`. A portable executable is intentionally not published.

## Signing

The public workflow creates unsigned artifacts. They are functional, but macOS Gatekeeper and Windows SmartScreen may warn on first launch. Removing these warnings for general distribution requires an Apple Developer Program membership with Developer ID signing and notarization, plus a Windows Authenticode code-signing certificate. Those paid credentials are not included in this free open-source project.

Unsigned package testing is still meaningful, but the beta should not be called stable until a person completes a real Windows install/uninstall, macOS drag-install/Desktop alias check, and a real Google Drive two-device cycle for at least one supported OS pairing.
