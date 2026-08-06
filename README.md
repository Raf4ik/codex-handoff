# Codex Handoff

Secure, cross-platform Codex state sync, backup, restore, and handoff for macOS and Windows.

Codex Handoff is a free, open-source project. It is an independent community utility and is not affiliated with or endorsed by OpenAI. It includes a Python core, CLI, PySide6 desktop GUI, local reference storage, and Google Drive integration.

## What It Does

Codex Handoff moves a user-selected, versioned profile of local Codex state between machines through the user's own storage. The design is deliberately handoff-oriented: a machine creates an immutable snapshot after Codex is closed, and another machine explicitly previews and applies it after Codex is closed there too.

Every installation keeps a local backup before applying an update. The first run creates an immutable parent baseline. Normal sync and retention operations can never overwrite or delete that baseline.

Snapshots are encrypted locally with AES-256-GCM before storage. A recovery key must be copied securely to every participating device and is never uploaded to Google Drive.

## Current Status

The repository is under active development. Source-based GUI and CLI operation are implemented first. Packaged and signed `.dmg`/`.exe` releases follow after cross-platform validation.

## Planned Workflow

```text
init -> create immutable baseline -> push -> notify -> preview -> pull -> restore if needed
```

The protocol is bidirectional:

```text
macOS -> storage -> Windows
Windows -> storage -> macOS
```

It does not copy authentication tokens, sockets, locks, caches, temporary files, or live database journals by default. Profiles explicitly define what is portable.

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
- [ ] Packaged `.dmg` for Apple Silicon and `.exe` installer for Windows 10+

## Русская версия

Codex Handoff — бесплатный открытый проект для безопасного переноса выбранного состояния Codex между macOS и Windows. Программа создаёт версионированные snapshots, сохраняет локальную резервную копию перед применением и создаёт неизменяемую родительскую копию при первом запуске. Направления macOS → Windows и Windows → macOS работают через общее хранилище пользователя.

Проект включает общее Python-ядро, CLI, графический интерфейс PySide6 и подключение Google Drive. Файлы `.dmg` и `.exe` будут добавлены после кроссплатформенной проверки. Токены авторизации, кеши, lock-файлы и временные данные не синхронизируются по умолчанию.

## License

Apache License 2.0. See [LICENSE](LICENSE).
