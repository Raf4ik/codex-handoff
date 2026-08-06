# Codex Handoff Implementation Plan

1. Build and verify immutable snapshot artifacts and protected baselines.
2. Add per-device state, pre-apply backups, preview, pull, restore, and stale-device push rejection.
3. Define the provider contract and implement its local reference backend.
4. Implement Google Drive OAuth, app folder discovery, resumable artifact upload, download, and head updates.
5. Build the PySide6 setup and main windows over the service API.
6. Expose the same operations in the CLI.
7. Add unit, integration, macOS, and Windows CI coverage and packaging documentation.
