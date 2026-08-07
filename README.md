# Codex Handoff

Secure bidirectional synchronization of Codex state between two macOS and/or Windows computers, with encrypted backup and restore.

Codex Handoff is a free, open-source desktop application. It synchronizes selected Codex data between two computers through storage owned by the user. The two endpoints can be macOS and Windows, Windows and Windows, or macOS and macOS. The current implementation supports Google Drive and a local folder.

Codex Handoff is an independent community project and is not affiliated with or endorsed by OpenAI.

## Supported Pairings

One configured synchronization space connects exactly two active computers. The computers may use any supported combination:

| Direction | Example |
| --- | --- |
| macOS → Windows | MacBook to a Windows laptop or desktop |
| Windows → macOS | Windows laptop or desktop back to a Mac |
| Windows → Windows | Windows laptop to a replacement Windows PC |
| macOS → macOS | One MacBook to a new MacBook |

The arrows describe the current publish direction; the same pair can synchronize back in the opposite direction. This is multi-platform synchronization for a two-device pair, not a three-way merge service. Before publishing, the active computer must apply the latest version from the other computer.

## Screenshots

### Synchronization Dashboard

![Codex Handoff synchronization dashboard](docs/images/dashboard.png)

### First-Time Setup

![Codex Handoff first-time setup wizard](docs/images/setup-wizard.png)

### Russian Settings and Updates

![Codex Handoff Russian settings and application updates](docs/images/settings-russian.png)

## Why It Exists

Codex stores useful working state locally. Copying its entire data directory between computers is unsafe: it can include authentication data, machine-specific settings, caches, locks, temporary files, and databases that may still be in use.

Codex Handoff uses a controlled synchronization process instead:

- only an explicit portable profile is included;
- Codex must be closed before state is captured or applied;
- every published state is a separate immutable version;
- snapshots are encrypted on the device before upload;
- the receiving device previews an update and asks for confirmation;
- a local backup is created before an update or restore is applied;
- the original protected baseline cannot be replaced by normal synchronization.

This is near-real-time, user-controlled synchronization rather than silent live file mirroring. The desktop application checks the small cloud head record every 60 seconds and notifies the user about a new version. On connection failures it backs off to 2, 5, and then 15 minutes, so background monitoring remains lightweight. It never applies a remote update without confirmation.

## How Synchronization Works

```mermaid
flowchart LR
    A["Codex state on device A"] --> B["Portable profile filter"]
    B --> C["Versioned snapshot and SHA-256 manifest"]
    C --> D["AES-256-GCM encryption"]
    D --> E["User's Google Drive or local folder"]
    E --> F["Update detection on device B"]
    F --> G["Preview and user confirmation"]
    G --> H["Local pre-apply backup"]
    H --> I["Integrity verification and staged apply"]
    I --> J["Codex state on device B"]
```

The same path works in reverse. After device B applies the latest cloud version, it can publish its own newer version. Device A then detects, previews, and applies that update. The pairing is not tied to a particular operating-system combination: replace a Windows laptop with a Windows desktop, replace a MacBook with another Mac, or pair macOS with Windows using the same process.

Each device records the last version it applied. Before publishing, Codex Handoff compares that value with the current cloud version. If the device is stale, publication stops and the user must synchronize from the cloud first. This prevents an older device from unknowingly replacing the newest synchronization state.

## First-Time Setup

### 1. Prepare Google Drive

Create Desktop OAuth credentials in Google Cloud, enable the Google Drive API, and download the client JSON. Detailed instructions are in [Google Drive setup](docs/GOOGLE_DRIVE.md).

Codex Handoff requests the limited `drive.file` scope. It can access files created or explicitly opened by this application, not the user's entire Google Drive.

### 2. Configure the first device

On first launch, select:

- English or Russian as the interface language; English is the default;
- a unique device name;
- the local Codex state directory, normally `~/.codex`;
- the application's local workspace;
- Google Drive or a local-folder provider;
- the Google Desktop OAuth JSON when Google Drive is selected;
- a recovery-key file.

Choose **Create new** for the recovery key on the first device. Keep a separate offline copy. The key is required to decrypt every protected baseline and synchronization version; it is never uploaded to Google Drive and cannot be recovered by the project maintainers.

### 3. Create the protected baseline

Close Codex and select **Create baseline**. The application captures the portable profile, creates a manifest, encrypts the artifact, and uploads the first protected copy.

Only one baseline can exist in the configured storage. Normal publish, synchronization, retention, and restore operations do not overwrite or delete it. The GUI can restore this baseline later.

### 4. Connect the second device

Install Codex Handoff on the second computer and configure it with:

- the same Google account;
- Desktop OAuth credentials from the same Google Cloud project;
- a secure copy of the same recovery key;
- a different device name;
- that computer's local Codex state directory.

The second device discovers the protected baseline and published versions in the shared application folder. It first downloads and applies the latest version, or restores the protected baseline when no version has been published yet. Until that first initialization succeeds, publishing is disabled so a new computer cannot overwrite the shared state with its empty or unrelated local files.

The encrypted baseline is cached in the application data directory on both devices. It remains available for recovery on either computer even if the cloud connection is temporarily unavailable.

### Pairing flow inside the application

1. On the first computer, choose the Codex directory, storage provider, and recovery key, then create the protected baseline.
2. On the second or replacement computer, use the same storage, Google account, OAuth JSON, and recovery key. Give it a different device name.
3. The dashboard detects whether this is a new pair member. If a current version exists, it offers a preview before applying it. If only the baseline exists, it offers **Initialize from baseline**.
4. The **Sync to cloud** action remains disabled until initialization succeeds. This prevents an empty or unrelated new profile from replacing the pair's state.
5. After initialization, work on either computer, close Codex, publish, and apply the update on the other computer. Each device keeps its own encrypted local baseline copy.

### Replace a computer

1. Install Codex Handoff on the replacement computer.
2. Use the same Google account or shared folder, the same OAuth project, and the same recovery key.
3. Give the replacement computer its own device name, such as `Windows desktop` or `New MacBook`.
4. Choose **Sync from cloud** to apply the latest published version. If the pair has only a baseline, choose **Initialize from baseline**.
5. Continue working normally. The replacement computer can publish after initialization; the old computer remains unchanged until it is used again.

Only two computers should publish to the same configured storage pair. When switching between them, always apply the latest update before publishing. Simultaneous publication is rejected rather than merged automatically.

## Normal Workflow

### Publish changes from either computer

1. Finish work and close Codex on the active computer.
2. Select **Sync to cloud** in Codex Handoff.
3. Confirm publication.
4. The application filters the portable data, creates a versioned snapshot and manifest, encrypts the snapshot, uploads it, and updates the cloud pointer only after the artifact is available.

If Codex is still running after confirmation, Codex Handoff asks the user to close it, waits, and continues automatically when the process exits. Waiting can be cancelled.

### Apply changes on the other computer

1. Leave Codex Handoff running in the notification area or menu bar. It checks for an update every 60 seconds and can display a system notification.
2. Select **Sync from cloud**.
3. Review the source device and the complete Added, Changed, Removed, and Unchanged file lists.
4. Confirm the update and close Codex if it is running.
5. The application downloads and decrypts the snapshot, verifies its manifest and SHA-256 hashes, creates a local encrypted backup, stages the files, and applies the version.

### Synchronize back to the first computer

The process is identical in the opposite direction. After the second computer has applied the latest version, close Codex there and select **Sync to cloud**. The first computer detects the newer version and applies it through **Sync from cloud** after preview and confirmation.

## What Is Synchronized

The built-in `safe` profile is an allowlist. It currently includes:

| Included | Purpose |
| --- | --- |
| `sessions/` | Active Codex session data |
| `archived_sessions/` | Archived session data |
| `attachments/` | Session attachments |
| `session_index.jsonl` | Portable session index |
| `skills/` | User-installed skills |
| `plugins/` | User-installed plugins |
| `rules/` | User rules |
| `AGENTS.md` | User instructions |

The profile excludes symlinks and files matching lock, temporary, log, cache, SQLite, database, WAL, or shared-memory patterns. Authentication tokens and machine-specific configuration are not part of the allowlist.

The project does not blindly synchronize the entire `.codex` directory. This reduces the risk of copying credentials, active databases, process locks, or platform-specific state between operating systems.

## Protection and Recovery

### Protected baseline

The baseline is the first known-good parent copy. It is stored as an immutable encrypted artifact and cannot be recreated over an existing baseline through the normal application flow. Select **Restore baseline** in the GUI to return the portable profile to that initial state.

### Version history

Every publication receives a unique version ID, parent version, source-device ID, UTC timestamp, file list, file sizes, and SHA-256 hashes. Published snapshot artifacts are never edited in place. The GUI lists available versions and can restore a selected one.

### Pre-apply backup and rollback

Before applying a cloud version or restoring an older version, the receiving device creates a local encrypted backup of its current portable state. If applying the requested artifact fails, Codex Handoff attempts to roll back automatically from that backup.

### Encryption and integrity

- snapshot contents are encrypted locally with AES-256-GCM;
- the recovery key stays on the user's devices;
- each file is checked against the SHA-256 digest stored in the manifest;
- archive paths are validated before extraction;
- files are prepared in a staging directory before replacement;
- the mutable cloud pointer is updated only after the immutable artifact is uploaded.

Google Drive can see the application folder, encrypted object names, version identifiers, timestamps, and limited metadata. It cannot read snapshot contents without the recovery key. See [Privacy](PRIVACY.md) and [Security](SECURITY.md).

## Implemented Features

- shared Python synchronization core for macOS and Windows;
- two-device pairing for macOS → Windows, Windows → macOS, Windows → Windows, and macOS → macOS;
- PySide6 desktop GUI and command-line interface;
- first-run configuration wizard;
- English interface by default with a complete Russian option in setup and Settings;
- Google Drive OAuth and resumable uploads;
- local-folder provider for development, testing, or user-managed shared storage;
- bidirectional versioned synchronization;
- lightweight 60-second update polling with 2/5/15-minute failure backoff;
- tray/background mode, operating-system autostart, and system notifications;
- complete Added, Changed, Removed, and Unchanged preview with explicit confirmation;
- detection of a running Codex process and cancellable waiting;
- immutable protected baseline and in-app baseline restore;
- remote version history and selected-version restore;
- encrypted local backup before apply or restore;
- automatic rollback after an apply failure;
- stale-device and concurrent-update checks;
- cryptographic integrity and archive-path verification;
- automated tests for snapshots, encryption, providers, process detection, GUI behavior, and the end-to-end local synchronization flow;
- branded GitHub Actions builds: a DMG for Apple Silicon macOS and a per-user Setup installer for 64-bit Windows.
- consent-based in-app update checks with SHA-256 verification and in-place installation.

## Storage Model

Codex Handoff writes an application-owned `Codex Handoff` folder to Google Drive. It contains:

- one protected `baseline-*.chandoff` artifact;
- immutable `version-*.chandoff` synchronization artifacts;
- a small mutable `head.json` pointer to the newest published version.

Files with the `.chandoff` extension are encrypted containers. The application keeps configuration, the Google refresh token, device state, downloaded artifacts, staging data, and pre-apply backups in operating-system-specific per-user application directories outside the synchronized Codex profile.

The repository contains a provider interface, so another storage backend can be added without changing the snapshot, encryption, verification, or apply logic.

## Desktop Downloads

The [GitHub Releases](https://github.com/Raf4ik/codex-handoff/releases) page provides two unsigned beta installers and a checksum file:

- `CodexHandoff-macOS-arm64.dmg` for Apple Silicon Macs, M1 or newer;
- `CodexHandoff-Windows-x64-Setup.exe` for 64-bit Windows 10 or newer;
- `SHA256SUMS` for download verification.

Python, Qt, and the required libraries are bundled into both downloads. End users do not install Python separately.

On Windows, run the Setup executable. It installs Codex Handoff for the current user, creates Start menu and Desktop shortcuts, enables background startup by default, and registers an uninstaller in Windows Settings. Uninstalling removes the application, shortcuts, and autostart entry while retaining user configuration, recovery material, and backups.

On macOS, open the DMG and drag `CodexHandoff.app` to the `Applications` alias. Launch the installed copy from Applications. During first-run setup, the enabled Desktop shortcut option creates a Finder alias named `Codex Handoff` on the Desktop. The alias is intentionally created only after the application has been moved out of the mounted DMG.

Starting with Beta 3, the installed application checks GitHub Releases shortly after launch and then once every 24 hours. A successful-check timestamp prevents repeated application launches from creating extra requests. A normal check is one small metadata request and consumes no CPU between checks. A newer package is downloaded only after confirmation, verified against the release `SHA256SUMS`, and installed only after a second confirmation. Windows Setup replaces the existing installation in place. On macOS, a detached helper keeps a temporary rollback copy while replacing the installed app. User configuration, recovery material, baselines, versions, and backups are stored outside the application and remain unchanged. Beta 2 must be upgraded to Beta 3 manually once because the older binary does not contain the updater.

The builds are currently unsigned. macOS Gatekeeper or Windows SmartScreen may display a warning on first launch. Removing these warnings requires Apple Developer ID notarization and a Windows Authenticode certificate; those paid credentials are not included in this free open-source project. See [desktop builds](docs/BUILDING.md).

## Run from Source

Requirements: Python 3.11 or newer.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
```

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

Start the desktop interface:

```bash
python -m codex_handoff gui
```

The same core is available through the CLI:

```bash
python -m codex_handoff --help
```

Available commands are `gui`, `status`, `baseline`, `push`, `pull`, `versions`, and `restore`.

## Current Beta Limitations

- Users currently provide their own Google Desktop OAuth JSON. A project-wide verified Google consent screen is not bundled yet.
- Live Google Drive authentication and a full physical two-device cycle still require release-level validation with real user credentials.
- Google Drive does not provide transactional compare-and-swap. Simultaneous publication from two devices is unsupported; finish synchronization on one device before publishing from another.
- Background monitoring runs as the user's tray/menu-bar application, not as a privileged system service. Closing the main window keeps it running when monitoring is enabled; Quit stops it.
- The preview lists affected paths and categories, but it does not render a line-by-line content diff.
- The portable profile has been checked against a current macOS Codex directory but still needs validation against real Windows installations, replacement-computer onboarding, and future Codex versions.
- The `.dmg` and `.exe` builds are unsigned beta artifacts.

These limitations are why the current release is marked as a prerelease rather than stable.

## Project Status

- [x] Public repository and Apache-2.0 license
- [x] Versioned local snapshots and protected baseline
- [x] Bidirectional synchronization with explicit confirmation
- [x] Google Drive and local-folder providers
- [x] Restore preview, pre-apply backup, and rollback
- [x] macOS and Windows GUI source
- [x] Automated unsigned `.dmg` and Windows Setup installer with shortcuts, autostart, and uninstall
- [ ] Real Google Drive two-device validation for every supported operating-system pairing
- [ ] Verified project-wide Google OAuth distribution flow
- [ ] Signed and notarized stable installers

## Русская версия

Codex Handoff — бесплатное приложение с открытым исходным кодом для безопасной двусторонней синхронизации выбранного состояния Codex между двумя компьютерами. Поддерживаются все четыре направления: macOS → Windows, Windows → macOS, Windows → Windows и macOS → macOS. Программа не копирует каталог `.codex` целиком: она собирает только разрешённые для синхронизации данные, создаёт отдельную версию, шифрует её на устройстве и публикует в Google Drive пользователя либо в выбранную локальную папку.

Синхронизация работает в обоих направлениях:

```text
macOS -> Google Drive -> Windows
Windows -> Google Drive -> macOS
Windows -> Google Drive -> Windows
macOS -> Google Drive -> macOS
```

Это контролируемая синхронизация, а не незаметное фоновое зеркалирование файлов. Приложение раз в 60 секунд проверяет небольшой указатель актуальной версии в облаке и сообщает об обновлении. При ошибках сети интервал увеличивается до 2, 5 и 15 минут, поэтому фоновый мониторинг не создаёт постоянной заметной нагрузки. Полученное обновление применяется только после предварительного просмотра и явного подтверждения пользователя.

### Полный путь синхронизации

1. На первом устройстве пользователь настраивает Google Drive, создаёт ключ восстановления и закрывает Codex.
2. Codex Handoff создаёт неизменяемую исходную родительскую копию — защищённый baseline.
3. После работы в Codex пользователь закрывает его и нажимает **Sync to cloud**.
4. Программа выбирает только данные безопасного профиля, создаёт снимок с манифестом и SHA-256-хешами, шифрует его с помощью AES-256-GCM и загружает как новую неизменяемую версию.
5. Приложение на втором устройстве обнаруживает обновление и показывает уведомление. Если это новый компьютер и обычных версий ещё нет, оно предлагает инициализировать его из защищённой родительской копии.
6. Пользователь нажимает **Sync from cloud**, видит источник и списки добавленных, изменённых, удаляемых и неизменённых файлов, затем подтверждает применение.
7. Если Codex запущен, приложение ждёт его закрытия. Ожидание можно отменить.
8. Перед применением создаётся локальная зашифрованная резервная копия текущего состояния.
9. Загруженный снимок расшифровывается, проверяется и применяется через временный каталог.
10. После работы на втором устройстве тот же процесс выполняется в обратном направлении. При замене ноутбука или MacBook новый компьютер проходит эту же первичную инициализацию с тем же ключом восстановления.

Если устройство не получило последнюю облачную версию, оно не сможет опубликовать поверх неё старое состояние: защита от устаревшего устройства потребует сначала выполнить синхронизацию из облака.

### Что входит в синхронизацию

По умолчанию включены `sessions`, `archived_sessions`, `attachments`, `session_index.jsonl`, `skills`, `plugins`, `rules` и `AGENTS.md`.

Не синхронизируются токены авторизации, платформенные настройки, символические ссылки, кеши, lock-файлы, журналы, временные файлы, базы SQLite и их активные WAL/SHM-файлы. Такой разрешительный список уменьшает риск попадания в облако секретов и несовместимого машинного состояния.

### Резервные копии и восстановление

- Исходный baseline создаётся один раз и не может быть затёрт обычной синхронизацией.
- Зашифрованная копия baseline хранится в общем хранилище и отдельно в каталоге данных каждого из двух устройств.
- В GUI можно восстановить защищённый baseline или выбранную опубликованную версию.
- Перед любым применением или восстановлением создаётся локальная зашифрованная резервная копия.
- При ошибке применения программа пытается автоматически вернуть предыдущее локальное состояние.
- Потерянный ключ восстановления вернуть невозможно, поэтому его отдельную копию нужно хранить в безопасном месте.

### Что уже реализовано

Проект включает общее Python-ядро, CLI, графический интерфейс PySide6, мастер первого запуска, Google Drive OAuth, локальное тестовое хранилище, шифрование AES-256-GCM, проверку целостности, историю версий, уведомления, подтверждение обновлений, ожидание закрытия Codex, защиту от устаревшей публикации, восстановление, работу в области уведомлений, автозапуск и автоматические тесты. Английский остаётся основным языком интерфейса, русский можно выбрать при первом запуске или в настройках.

GitHub Actions собирает неподписанные `CodexHandoff-macOS-arm64.dmg` и `CodexHandoff-Windows-x64-Setup.exe`. Python уже встроен в обе сборки и отдельно пользователю не нужен. Windows Setup устанавливает программу для текущего пользователя, создаёт ярлыки на рабочем столе и в меню «Пуск», включает автозапуск по умолчанию и добавляет штатное удаление. На macOS пользователь переносит приложение из DMG в Applications, после чего мастер первого запуска создаёт псевдоним Finder на рабочем столе. Поскольку сборки пока не подписаны, macOS Gatekeeper и Windows SmartScreen могут показать предупреждение при первом запуске.

Начиная с Beta 3, приложение проверяет GitHub Releases вскоре после запуска, а затем раз в 24 часа. Отметка последней успешной проверки исключает лишние запросы при частых перезапусках. Между проверками отдельный фоновый цикл не работает. Скачивание новой версии начинается только после согласия пользователя; после проверки SHA-256 программа отдельно спрашивает разрешение на установку. В Windows новая версия устанавливается поверх существующей копии. В macOS helper временно сохраняет старую `.app`, заменяет её новой и возвращает предыдущую копию при сбое. Beta 2 нужно один раз обновить вручную до Beta 3; следующие версии можно будет устанавливать из приложения.

Проект находится на стадии beta. Перед стабильным релизом ещё нужна проверка полного цикла через реальный Google Drive на физических компьютерах. В одну связку входят два устройства; одновременная публикация с них не поддерживается. Сначала примените последнюю версию на одном компьютере, затем публикуйте изменения со второго.

## License

Apache License 2.0. See [LICENSE](LICENSE).
