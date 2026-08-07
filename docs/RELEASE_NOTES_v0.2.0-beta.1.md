# Codex Handoff v0.2.0 Beta 1

## English

Codex Handoff is a free, open-source desktop application for secure, bidirectional synchronization of selected Codex state between macOS and Windows through storage owned by the user. This beta replaces the early utility-style interface and portable Windows build with a complete desktop workflow and platform installers.

### Highlights

- New PySide6 dashboard with platform-aware labels, synchronization status, version history, recovery, and settings views.
- Four-step first-run wizard for device paths, Google Drive or local storage, recovery key, autostart, and Desktop shortcut setup.
- Bidirectional macOS-to-Windows and Windows-to-macOS synchronization through Google Drive or a selected shared folder.
- Immutable encrypted parent baseline, in-app baseline restore, version restore, encrypted pre-apply backups, and rollback after an apply failure.
- Complete update preview with Added, Changed, Removed, and Unchanged path lists before confirmation.
- Lightweight remote-head monitoring every 60 seconds with 2, 5, and 15-minute backoff after network failures.
- Background tray/menu-bar mode and current-user autostart, enabled by default during setup.
- Approved Codex Handoff icon in the GUI, tray/Dock, application bundles, installer, shortcuts, and DMG.
- Backward-compatible platform metadata so new builds identify Mac and Windows sources while older snapshots remain readable.

### Installation

`CodexHandoff-Windows-x64-Setup.exe` is a real per-user installer for 64-bit Windows 10 or newer. It installs under the current user's local application directory, creates Start menu and Desktop shortcuts, enables background startup by default, and registers a normal uninstaller. Uninstalling removes the application and OS integration while retaining user configuration, recovery material, and backups.

`CodexHandoff-macOS-arm64.dmg` supports Apple Silicon Macs (M1 or newer). Open the DMG, drag `CodexHandoff.app` to Applications, and launch the installed copy. The first-run wizard can create a Finder alias on the Desktop after the application is in Applications.

Python and Qt are already bundled. Verify downloads with `SHA256SUMS`.

### Beta Notes

The builds are unsigned. macOS Gatekeeper and Windows SmartScreen may warn on first launch. Removing those warnings requires paid Apple Developer ID/notarization and Windows Authenticode credentials, which are not included in this free project.

Automated tests cover the synchronization core, Google Drive provider behavior, GUI, platform integration, installers, startup, and uninstall cleanup. A physical Windows install/uninstall, macOS drag-install/Desktop alias check, and real Google Drive Mac-to-Windows-to-Mac cycle are still required before this release can be called stable. Users currently provide their own Google Desktop OAuth JSON and must preserve an offline copy of the recovery key.

## Русский

Codex Handoff — бесплатное приложение с открытым исходным кодом для безопасной двусторонней синхронизации выбранных данных Codex между macOS и Windows через хранилище пользователя. В этой бета-версии ранняя утилитарная оболочка и portable-сборка Windows заменены полноценным рабочим интерфейсом и установщиками для обеих платформ.

### Главное

- Новый интерфейс PySide6 со статусами синхронизации, историей версий, восстановлением, настройками и подписями, зависящими от платформы.
- Четырёхшаговый мастер первого запуска для путей устройства, Google Drive или локальной папки, ключа восстановления, автозапуска и ярлыка на рабочем столе.
- Двусторонняя синхронизация macOS -> Windows и Windows -> macOS через Google Drive либо выбранную общую папку.
- Неизменяемая зашифрованная родительская копия, восстановление baseline и отдельных версий из приложения, локальная зашифрованная копия перед применением и автоматический откат при ошибке.
- Полный предварительный просмотр добавляемых, изменяемых, удаляемых и неизменённых файлов до подтверждения.
- Облегчённая проверка указателя актуальной версии каждые 60 секунд с интервалами 2, 5 и 15 минут после сетевых ошибок.
- Фоновая работа через область уведомлений Windows или строку меню macOS и автозапуск пользователя, включённый по умолчанию при настройке.
- Утверждённая иконка в GUI, tray/Dock, приложениях, установщике, ярлыках и DMG.
- Обратно совместимые сведения о платформе: новые версии показывают источник Mac или Windows, старые снимки продолжают читаться.

### Установка

`CodexHandoff-Windows-x64-Setup.exe` — полноценный установщик для текущего пользователя 64-разрядной Windows 10 или более новой версии. Он устанавливает приложение в локальный каталог пользователя, создаёт ярлыки в меню «Пуск» и на рабочем столе, по умолчанию включает фоновый автозапуск и добавляет штатное удаление. При удалении очищаются программа и системная интеграция, а пользовательские настройки, ключи и резервные копии сохраняются.

`CodexHandoff-macOS-arm64.dmg` предназначен для Mac с Apple Silicon, начиная с M1. Откройте DMG, перенесите `CodexHandoff.app` в Applications и запускайте установленную копию. После этого мастер первого запуска сможет создать псевдоним Finder на рабочем столе.

Python и Qt уже встроены. Для проверки загрузок используйте `SHA256SUMS`.

### Ограничения бета-версии

Сборки пока не подписаны, поэтому macOS Gatekeeper и Windows SmartScreen могут показать предупреждение при первом запуске. Для устранения предупреждений нужны платные Apple Developer ID/notarization и сертификат Windows Authenticode; в бесплатный проект эти реквизиты не входят.

Автоматические тесты проверяют ядро синхронизации, провайдер Google Drive, GUI, системную интеграцию, установку, запуск и удаление. До стабильного релиза всё ещё нужна ручная проверка установки и удаления на физическом компьютере с Windows, переноса приложения и создания псевдонима на рабочем столе macOS, а также полного реального цикла Google Drive Mac -> Windows -> Mac. Сейчас пользователь предоставляет собственный Google Desktop OAuth JSON и обязан хранить отдельную офлайн-копию ключа восстановления.
