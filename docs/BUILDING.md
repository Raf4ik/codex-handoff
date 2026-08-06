# Desktop Builds

Codex Handoff bundles Python, Qt, and its dependencies. End users do not install Python.

## GitHub Actions

Run the **Desktop builds** workflow manually from the Actions tab. It produces:

- `CodexHandoff-macOS-arm64.dmg` for Apple Silicon Macs (M1 or newer).
- `CodexHandoff-Windows-x64.exe` for 64-bit Windows 10 or newer.

Pushing a tag such as `v0.1.0` runs the same builds and attaches both files to a GitHub Release.

## Local macOS Build

Run on an Apple Silicon Mac with Python 3.11 or newer:

```bash
python -m venv .venv
.venv/bin/python -m pip install '.[packaging]'
.venv/bin/python -m PyInstaller --noconfirm --clean --windowed \
  --name CodexHandoff \
  --osx-bundle-identifier com.codexhandoff.desktop \
  --collect-submodules googleapiclient \
  --collect-submodules google_auth_oauthlib \
  packaging/codex_handoff_gui.py
hdiutil create -volname CodexHandoff -srcfolder dist/CodexHandoff.app \
  -ov -format UDZO dist/CodexHandoff-macOS-arm64.dmg
```

## Signing

The public workflow creates unsigned artifacts. They are functional, but macOS Gatekeeper and Windows SmartScreen may warn on first launch. Removing these warnings for general distribution requires an Apple Developer Program membership with Developer ID notarization and a Windows Authenticode code-signing certificate. Those credentials are not included in the repository.
