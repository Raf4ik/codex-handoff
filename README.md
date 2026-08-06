# Codex Handoff

Secure, cross-platform Codex state sync, backup, restore, and handoff for macOS and Windows.

Codex Handoff is a free, open-source project. It is an independent community utility and is not affiliated with or endorsed by OpenAI. It includes a Python core, CLI, PySide6 desktop GUI, local reference storage, and Google Drive integration.

## What It Does

Codex Handoff moves a user-selected, versioned profile of local Codex state between machines through the user's own storage. The design is deliberately handoff-oriented: a machine creates an immutable snapshot after Codex is closed, and another machine explicitly previews and applies it after Codex is closed there too.

Every installation keeps a local backup before applying an update. Initial setup requires an immutable parent baseline before the first handoff. Normal sync and retention operations can never overwrite or delete that baseline.

Snapshots are encrypted locally with AES-256-GCM before storage. A recovery key must be copied securely to every participating device and is never uploaded to Google Drive.

## Current Status

The repository is under active development. Source-based GUI and CLI operation are implemented. GitHub Actions can produce an unsigned Apple Silicon `.dmg` and a standalone Windows x64 `.exe`; signed releases follow after real cross-platform and Google Drive validation.

## Planned Workflow

```text
init -> create immutable baseline -> push -> notify -> preview -> pull -> restore if needed
```

The protocol is bidirectional:

```text
macOS -> storage -> Windows
Windows -> storage -> macOS
```

The default safe profile copies sessions, archived sessions, attachments, session index, skills, plugins, rules, and `AGENTS.md`. It does not copy authentication tokens, machine-specific configuration, sockets, locks, caches, temporary files, or live databases and journals. Profiles explicitly define what is portable.

## Development

Requirements: Python 3.11 or newer.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
```

Run the desktop interface:

```bash
python -m codex_handoff gui
```

The first-run wizard supports a local folder or Google Drive. Google Drive requires a Desktop OAuth client JSON from Google Cloud Console; see [Google Drive setup](docs/GOOGLE_DRIVE.md). Credentials and refresh tokens must never be committed to this repository.

While the GUI is open, it checks for a new remote version every 30 seconds and shows a system notification. It never accepts an update without the user: the user previews and confirms it. If Codex is running, the confirmed operation waits and starts automatically after Codex exits; waiting can be cancelled.

### Desktop downloads

The **Desktop builds** GitHub Actions workflow produces `CodexHandoff-macOS-arm64.dmg` for M1-or-newer Macs and `CodexHandoff-Windows-x64.exe` for 64-bit Windows 10 or newer. Python is bundled into both artifacts and is not required on the user's computer. See [desktop builds](docs/BUILDING.md).

The current artifacts are unsigned. macOS Gatekeeper or Windows SmartScreen may warn on first launch. Signing without these warnings requires paid third-party developer certificates; it is not required to keep the project itself free and open source.

### Development limitations

- Live Google Drive authentication still requires an end-to-end test with real user OAuth credentials.
- Google Drive does not provide transactional compare-and-swap; simultaneous publication from two devices is unsupported. The stale-device guard and explicit handoff workflow remain mandatory.
- The default portable profile was checked against a current macOS Codex directory, but still needs validation against a real Windows installation and future Codex versions.
- Desktop artifacts are automated but must still pass the first real macOS-to-Windows handoff test before a stable release.

The same core is available through the CLI:

```bash
python -m codex_handoff --help
```

## Roadmap

- [x] Public repository and open-source license
- [x] Versioned local snapshots and immutable baseline
- [x] Bidirectional push/pull/handoff protocol
- [x] Restore preview and safe rollback
- [x] Google Drive provider with OAuth
- [x] macOS and Windows GUI source
- [x] Automated unsigned `.dmg` for Apple Silicon and standalone `.exe` for Windows 10+
- [ ] Signed installers and real macOS-to-Windows Google Drive release validation

## Русская версия

Codex Handoff — бесплатный открытый проект для безопасного переноса выбранного состояния Codex между macOS и Windows. Программа создаёт версионированные snapshots, сохраняет локальную резервную копию перед применением и создаёт неизменяемую родительскую копию при первом запуске. Направления macOS → Windows и Windows → macOS работают через общее хранилище пользователя.

Проект включает общее Python-ядро, CLI, графический интерфейс PySide6 и подключение Google Drive. GitHub Actions собирает неподписанные `CodexHandoff-macOS-arm64.dmg` и `CodexHandoff-Windows-x64.exe`; Python уже находится внутри этих файлов и пользователю не нужен. Токены авторизации, платформенные настройки, кеши, lock-файлы, базы SQLite и временные данные не синхронизируются по умолчанию.

## License

Apache License 2.0. See [LICENSE](LICENSE).
