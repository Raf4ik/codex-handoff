# Codex Handoff Design

## Scope

The first release includes a shared Python core, CLI, PySide6 desktop GUI, a local reference provider, and Google Drive storage through the user's account. macOS and Windows packaging is documented but code signing is outside the first unsigned release.

## Safety Contract

Codex must be closed before baseline creation, push, pull, or restore. Every apply creates a local pre-apply backup. Snapshots and baselines are immutable ZIP artifacts with an embedded manifest and SHA-256 digest for every file, wrapped in an AES-256-GCM encrypted container before storage. A baseline is never pruned, updated, or deleted by the application.

Each device stores its own `last_applied_version`. A push is rejected when the remote head differs from that value, preventing a stale machine from overwriting a newer handoff. Pull is explicit and requires confirmation. Authentication tokens, machine-specific configuration, caches, locks, sockets, temporary files, SQLite databases, and active journals are excluded from the default portable profile. Sessions, archived sessions, attachments, session index, skills, plugins, rules, and `AGENTS.md` are included.

## Architecture

- `artifacts.py`: build, read, verify, preview, and apply immutable archives.
- `providers/base.py`: storage contract independent of filesystem or Google Drive.
- `providers/local.py`: reference provider and integration-test oracle.
- `providers/google_drive.py`: OAuth and Drive API implementation using `drive.file` scope.
- `service.py`: baseline, push, pull, restore, and device-state orchestration.
- `processes.py`: conservative Codex process detection on macOS and Windows.
- `config.py`: local configuration and credential paths.
- `gui/`: PySide6 UI; no synchronization logic lives in widgets.
- `cli.py`: automation and diagnostic interface over the same service.

## Google Drive Layout

The provider creates an app-owned `Codex Handoff` folder. Immutable artifacts use unique `.chandoff` names. `head.json` is the only mutable object. Publishing uploads and verifies the immutable artifact before updating `head.json`. The client reads the head again after update and stops on inconsistency.

Google Drive is not a transactional database, so simultaneous publication remains unsupported. The user-facing handoff protocol and stale-device check are mandatory. A later server backend can provide strict compare-and-swap without changing the core service interface.

## GUI

The first-run screen collects device name, Codex state path, provider, local storage path or Google OAuth client file, recovery key, and local workspace path. The main view shows Codex process state, current remote version, last applied version, protected baseline, and recent versions. It polls for updates every 30 seconds and displays a system notification without accepting anything automatically. Destructive actions always show a preview and confirmation. A confirmed operation waits while Codex is running and starts when the process closes; the user can cancel the waiting operation.

## Distribution

Development runs from Python 3.11+. The desktop build workflow provides `CodexHandoff-macOS-arm64.dmg` and `CodexHandoff-Windows-x64.exe`, with Python and Qt bundled. Unsigned builds may trigger operating-system warnings. See `docs/BUILDING.md`.
