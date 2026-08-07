# Codex Handoff v0.2.0 Beta 2

## English

Beta 2 makes the synchronization model explicitly two-device and independent of the operating-system combination. A pair can be macOS to Windows, Windows to Windows, or macOS to macOS.

### Changes

- New-device onboarding is protected: a replacement computer cannot publish before it has applied the current cloud version or initialized from the protected baseline.
- The dashboard now explains the initial-sync state and offers **Initialize from baseline** when a pair has no published versions yet.
- The encrypted parent baseline is cached locally on both devices after creation or first synchronization.
- Either paired device can restore its local baseline copy if the cloud is temporarily unavailable.
- Added integration coverage for macOS to Windows, Windows to Windows, and macOS to macOS pairings, plus replacement-computer onboarding.
- Normalized macOS platform metadata to `macos` so source labels remain consistent across artifacts, local storage, Google Drive, and the GUI.
- Fixed local version-history ordering to use manifest creation time rather than the random portion of an artifact identifier.
- Updated README and protocol documentation with replacement-computer instructions and the two-device model.

### Safety model

Only one of the two paired devices publishes at a time. If the other device has a newer cloud version, publishing is rejected until that update is applied. Codex Handoff does not silently merge simultaneous edits.

The builds are unsigned beta artifacts. macOS Gatekeeper and Windows SmartScreen may warn on first launch. Keep an offline copy of the recovery key.

## Русский

В Beta 2 модель синхронизации явно рассчитана на два устройства и не зависит от сочетания операционных систем. Поддерживаются связки macOS ↔ Windows, Windows ↔ Windows и macOS ↔ macOS.

### Изменения

- Новое устройство не может публиковать данные, пока не применит актуальную версию из облака или не инициализируется из защищённой родительской копии.
- Dashboard показывает состояние первичной синхронизации и предлагает **Initialize from baseline**, если в связке ещё нет опубликованных версий.
- Зашифрованная родительская копия сохраняется локально на обоих устройствах после создания или первой синхронизации.
- Любое из двух устройств может восстановить локальную копию baseline, если облако временно недоступно.
- Добавлены интеграционные тесты для связок macOS ↔ Windows, Windows ↔ Windows и macOS ↔ macOS, а также для замены компьютера.
- Метаданные macOS нормализованы к значению `macos`, поэтому источник корректно отображается в артефактах, локальном хранилище, Google Drive и GUI.
- Исправлена сортировка локальной истории версий: теперь она использует время создания манифеста, а не случайную часть идентификатора.
- README и протокол дополнены инструкциями для нового ноутбука или ПК и описанием двухустройственной модели.

### Правило безопасности

В каждый момент публикует только одно из двух устройств. Если в облаке есть более новая версия, публикация блокируется до её применения. Codex Handoff не пытается незаметно объединять одновременные изменения.

Сборки остаются неподписанными beta-артефактами. При первом запуске macOS Gatekeeper и Windows SmartScreen могут показать предупреждение. Отдельную офлайн-копию ключа восстановления нужно хранить в безопасном месте.
