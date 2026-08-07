# Codex Handoff v0.2.0 Beta 3

## English

Beta 3 adds a complete Russian interface and consent-based in-app updates while keeping English as the default language.

### Language support

- English remains the default interface language.
- Russian can be selected on the first setup step or later in **Settings**.
- Language changes apply immediately and persist for future launches.
- The setup wizard, dashboard, statuses, update previews, recovery controls, notifications, tray menu, confirmations, and error dialogs are localized.

### Application updates

- Installed applications check GitHub Releases shortly after launch and then once every 24 hours. A successful-check timestamp suppresses duplicate checks after repeated launches. No polling loop runs between checks.
- A normal check downloads only a small release metadata response. The checksum and installer are requested only when a newer version exists.
- Downloading requires explicit user confirmation.
- After download and SHA-256 verification, installation requires a second explicit confirmation.
- Windows Setup updates the existing installation in place using the same App ID and install directory.
- The macOS helper closes the application, keeps a temporary rollback copy, replaces `CodexHandoff.app`, and restores the previous copy if replacement fails.
- Configuration, recovery keys, protected baselines, synchronization versions, and local backups remain outside the application installation and are not replaced.
- Update packages reuse the same cache filenames, so later updates replace earlier downloads instead of accumulating installers.

### Existing installations

Beta 2 does not yet contain the updater. Install Beta 3 manually once. Updates released after Beta 3 can then be discovered and installed from inside the application.

The builds remain unsigned beta artifacts. macOS Gatekeeper and Windows SmartScreen may warn on first launch. Keep an offline copy of the recovery key.

## Русский

В Beta 3 появился полный русский интерфейс и обновление приложения с явным согласием пользователя. Английский остаётся основным языком.

### Поддержка языков

- Английский выбран по умолчанию.
- Русский можно выбрать на первом шаге настройки или позже в разделе **Настройки**.
- Язык меняется сразу и сохраняется для следующих запусков.
- Переведены мастер настройки, панель синхронизации, статусы, проверка обновлений данных, восстановление, уведомления, меню в области уведомлений, подтверждения и сообщения об ошибках.

### Обновление приложения

- Установленное приложение проверяет GitHub Releases вскоре после запуска, а затем раз в 24 часа. Отметка последней успешной проверки исключает повторные запросы при частых запусках. Между проверками фоновый цикл не работает.
- Обычная проверка загружает только небольшой ответ с метаданными релизов. Контрольная сумма и установщик запрашиваются только при появлении новой версии.
- Для скачивания нужно отдельное согласие пользователя.
- После скачивания и проверки SHA-256 приложение отдельно спрашивает разрешение на установку.
- В Windows Setup обновляет существующую установку в той же папке с тем же App ID.
- В macOS helper закрывает приложение, сохраняет временную копию для отката, заменяет `CodexHandoff.app` и возвращает предыдущую копию при сбое.
- Конфигурация, ключи восстановления, защищённые родительские копии, версии синхронизации и локальные резервные копии находятся вне каталога приложения и не заменяются.
- Пакеты обновлений используют одни и те же имена в кеше, поэтому новые загрузки заменяют предыдущие, а не накапливаются.

### Уже установленные версии

В Beta 2 механизма обновлений ещё нет. Beta 3 нужно установить вручную один раз. Следующие версии приложение сможет находить, скачивать и устанавливать самостоятельно после подтверждения пользователя.

Сборки остаются неподписанными beta-артефактами. При первом запуске macOS Gatekeeper и Windows SmartScreen могут показать предупреждение. Отдельную офлайн-копию ключа восстановления нужно хранить в безопасном месте.
