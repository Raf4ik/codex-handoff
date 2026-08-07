# Codex Handoff v0.2.0 Beta 4

## English

Beta 4 hardens the Windows in-app update path introduced in Beta 3.

### Included synchronization workflow

- One configured pair contains exactly two active devices and supports macOS → Windows, Windows → macOS, Windows → Windows, and macOS → macOS.
- Synchronization is bidirectional and user-controlled through Google Drive: Codex must be closed before publishing, applying, or restoring data.
- Each device keeps its own protected parent baseline. The application never overwrites that baseline and creates a local encrypted backup before applying or restoring data.
- English remains the default interface language; Russian can be selected during setup or later in Settings.

### Windows update reliability

- A successful in-app update now relaunches the newly installed Windows application explicitly.
- The installer uses the existing App ID and installation directory, so the previous version is replaced rather than duplicated.
- The packaging workflow verifies the complete sequence: install, launch, update the running copy in place, automatic relaunch, and uninstall cleanup.
- Configuration, recovery keys, protected baselines, synchronization versions, and local backups remain outside the installation directory.

### Update consent

- Background checks download only public release metadata and run at most once every 24 hours after a successful check.
- Downloading an installer requires explicit user confirmation.
- Installation requires a separate confirmation after SHA-256 verification.
- Beta 3 can discover Beta 4 through its built-in updater. Beta 2 and older versions require one manual installation of the current release.

The builds remain unsigned beta artifacts. macOS Gatekeeper and Windows SmartScreen may warn on first launch. Keep an offline copy of the recovery key.

## Русский

Beta 4 повышает надёжность встроенного обновления Windows, появившегося в Beta 3.

### Реализованный процесс синхронизации

- Одна настроенная связка включает ровно два активных устройства и поддерживает macOS → Windows, Windows → macOS, Windows → Windows и macOS → macOS.
- Двусторонняя синхронизация через Google Drive выполняется только под контролем пользователя: перед публикацией, применением или восстановлением данных Codex должен быть закрыт.
- На каждом устройстве хранится собственная защищённая родительская копия. Приложение никогда её не перезаписывает и создаёт локальную зашифрованную резервную копию перед применением или восстановлением данных.
- Английский остаётся основным языком интерфейса; русский можно выбрать при настройке или позже в разделе «Настройки».

### Надёжность обновления Windows

- После успешного обновления установщик явно запускает новую версию приложения Windows.
- Используются прежние App ID и каталог установки, поэтому новая версия заменяет старую, а не создаёт вторую копию.
- Сценарий сборки проверяет полный путь: установку, запуск, обновление работающей копии поверх текущей, автоматический перезапуск и очистку после удаления.
- Конфигурация, ключи восстановления, защищённые родительские копии, версии синхронизации и локальные резервные копии остаются вне каталога установки.

### Согласие на обновление

- Фоновая проверка получает только общедоступные метаданные релиза и после успешного запроса выполняется не чаще одного раза в 24 часа.
- Для скачивания установщика требуется явное согласие пользователя.
- После проверки SHA-256 приложение отдельно спрашивает разрешение на установку.
- Beta 3 может найти Beta 4 через встроенный механизм обновления. Для Beta 2 и более старых версий текущий релиз нужно один раз установить вручную.

Сборки остаются неподписанными и тестовыми. При первом запуске macOS Gatekeeper и Windows SmartScreen могут показать предупреждение. Отдельную офлайн-копию ключа восстановления нужно хранить в безопасном месте.
