from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..config import AppConfig, load_config, save_config
from ..models import ApplyPreview, RemoteHead
from ..monitor import RemoteHeadMonitor
from ..processes import is_codex_running
from ..service import HandoffService, create_provider
from ..updater import GitHubUpdater, UpdateInfo, is_packaged_application, launch_update
from .i18n import LANGUAGE_NAMES, normalize_language, text
from .platform import application_path, current_platform
from .setup import SetupWizard
from .theme import CHARCOAL, load_app_icon
from .widgets import (
    ActionButton,
    NavigationButton,
    OperationBanner,
    StatusBlock,
    StatusTone,
    SyncRoute,
    VersionTable,
)


class WorkerSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)


class Worker(QRunnable):
    def __init__(self, function) -> None:
        super().__init__()
        self.function = function
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.completed.emit(self.function())
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class UpdatePreviewDialog(QDialog):
    def __init__(self, preview: ApplyPreview, parent: QWidget | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.preview = preview
        self.language = normalize_language(language)
        self.setWindowTitle(text(self.language, "preview_window_title"))
        self.setMinimumSize(660, 500)
        title = QLabel(text(self.language, "preview_title"))
        title.setProperty("role", "heading")
        platform_names = {"windows": "Windows", "macos": "macOS"}
        details = QLabel(
            text(
                self.language,
                "preview_details",
                source=preview.source_device,
                platform=platform_names.get(preview.source_platform or "", text(self.language, "unknown_platform")),
                version=preview.version_id,
                created=preview.created_at or text(self.language, "unknown"),
            )
        )
        details.setProperty("role", "subtitle")
        counts = QHBoxLayout()
        added_frame, self.added_count = self._count(text(self.language, "added"), len(preview.added), StatusTone.SUCCESS)
        changed_frame, self.changed_count = self._count(text(self.language, "changed"), len(preview.changed), StatusTone.WARNING)
        removed_frame, self.removed_count = self._count(text(self.language, "removed"), len(preview.removed), StatusTone.ERROR)
        for widget in (added_frame, changed_frame, removed_frame):
            counts.addWidget(widget)
        tabs = QTabWidget()
        for key, paths in (
            ("added", preview.added),
            ("changed", preview.changed),
            ("removed", preview.removed),
            ("unchanged", preview.unchanged),
        ):
            name = text(self.language, key)
            listing = QListWidget()
            listing.addItems(paths or (text(self.language, "no_files"),))
            tabs.addTab(listing, f"{name} ({len(paths)})")
        note = QLabel(text(self.language, "preview_note"))
        note.setWordWrap(True)
        note.setObjectName("warningNote")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Apply).setText(text(self.language, "apply_update"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(text(self.language, "cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(details)
        layout.addLayout(counts)
        layout.addWidget(tabs, 1)
        layout.addWidget(note)
        layout.addWidget(buttons)

    @staticmethod
    def _count(title: str, value: int, tone: StatusTone) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setProperty("card", True)
        frame.setProperty("tone", tone.value)
        label = QLabel(str(value))
        label.setStyleSheet("font-size: 20px; font-weight: 700;")
        caption = QLabel(title)
        caption.setProperty("role", "subtitle")
        layout = QVBoxLayout(frame)
        layout.addWidget(caption)
        layout.addWidget(label)
        return frame, label


class ApplicationUpdateDialog(QDialog):
    def __init__(
        self,
        update: UpdateInfo,
        current_version: str,
        parent: QWidget | None = None,
        *,
        language: str = "en",
    ) -> None:
        super().__init__(parent)
        selected = normalize_language(language)
        self.setWindowTitle(text(selected, "update_window_title"))
        self.setMinimumSize(660, 500)
        title = QLabel(text(selected, "update_available", version=update.version))
        title.setProperty("role", "heading")
        details = QLabel(
            text(
                selected,
                "update_version_details",
                current=current_version,
                available=update.version,
            )
        )
        details.setProperty("role", "subtitle")
        notes_label = QLabel(text(selected, "release_notes"))
        notes_label.setStyleSheet("font-weight: 700;")
        notes = QTextBrowser()
        notes.setPlainText(update.notes or update.title)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Apply).setText(
            text(selected, "download_update")
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(text(selected, "cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(details)
        layout.addWidget(notes_label)
        layout.addWidget(notes, 1)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.config_path = config_path
        self.config = load_config(config_path)
        self.language = normalize_language(self.config.language)
        self.platform = current_platform()
        self.updater = (
            GitHubUpdater(__version__, self.platform.key)
            if self.platform.key in {"macos", "windows"}
            else None
        )
        self.service: HandoffService | None = None
        self.monitor: RemoteHeadMonitor | None = None
        self.pool = QThreadPool.globalInstance()
        self.workers: set[Worker] = set()
        self.ui_generation = 0
        self.last_notified_version: str | None = None
        self.pending_operation: tuple[object, object] | None = None
        self.requires_initial_sync = False
        self.remote_update_available = False
        self._quitting = False
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)
        self.setWindowTitle("Codex Handoff")
        self.setWindowIcon(load_app_icon())
        self.setMinimumSize(960, 680)
        self.resize(1120, 760)
        self._build_ui()
        self._build_tray()
        self.codex_wait_timer = QTimer(self)
        self.codex_wait_timer.setInterval(1000)
        self.codex_wait_timer.timeout.connect(self._try_pending_operation)
        self.codex_wait_timer.start()
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(24 * 60 * 60 * 1000)
        self.update_timer.timeout.connect(lambda: self._check_for_updates(manual=False))
        self.update_timer.start()
        if is_packaged_application():
            QTimer.singleShot(10000, lambda: self._check_for_updates(manual=False))
        self._connect()

    def _t(self, key: str, **values: object) -> str:
        return text(self.language, key, **values)

    def _local_platform_label(self) -> str:
        key = {"windows": "this_pc", "macos": "this_mac"}.get(
            self.platform.key, "this_generic_device"
        )
        return self._t(key)

    def _build_ui(self) -> None:
        header = QFrame()
        header.setStyleSheet(f"background: {CHARCOAL};")
        header.setFixedHeight(58)
        brand_icon = QLabel()
        brand_icon.setPixmap(load_app_icon().pixmap(32, 32))
        brand = QLabel("Codex Handoff")
        brand.setStyleSheet("color: white; font-size: 16px; font-weight: 700;")
        identity = QLabel(f"{self.config.device_id}  |  {self._provider_name()}")
        identity.setStyleSheet("color: #AFC0C3;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        header_layout.addWidget(brand_icon)
        header_layout.addWidget(brand)
        header_layout.addStretch()
        header_layout.addWidget(identity)

        self.navigation = QVBoxLayout()
        self.navigation.setContentsMargins(12, 18, 12, 18)
        self.nav_buttons: list[NavigationButton] = []
        for index, key in enumerate(("synchronization", "version_history", "recovery", "settings")):
            label = self._t(key)
            button = NavigationButton(label)
            button.clicked.connect(lambda checked=False, page=index: self.pages.setCurrentIndex(page))
            self.nav_buttons.append(button)
            self.navigation.addWidget(button)
        self.nav_buttons[0].setChecked(True)
        self.navigation.addStretch()
        privacy = QLabel(self._t("sidebar_privacy"))
        privacy.setWordWrap(True)
        privacy.setStyleSheet("color: #829599; font-size: 11px; padding: 8px;")
        self.navigation.addWidget(privacy)
        sidebar = QFrame()
        sidebar.setStyleSheet(f"background: {CHARCOAL};")
        sidebar.setFixedWidth(220)
        sidebar.setLayout(self.navigation)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._sync_page())
        self.pages.addWidget(self._history_page())
        self.pages.addWidget(self._recovery_page())
        self.pages.addWidget(self._settings_page())
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(sidebar)
        body.addWidget(self.pages, 1)
        shell = QVBoxLayout()
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(header)
        shell.addLayout(body, 1)
        container = QWidget()
        container.setLayout(shell)
        self.setCentralWidget(container)
        self.setStatusBar(QStatusBar())

    def _sync_page(self) -> QWidget:
        page = QWidget()
        title = QLabel(self._t("synchronization"))
        title.setProperty("role", "heading")
        subtitle = QLabel(self._t("sync_subtitle"))
        subtitle.setProperty("role", "subtitle")
        self.refresh_button = ActionButton(self._t("refresh"))
        self.refresh_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.refresh_button.clicked.connect(self.refresh)
        heading = QHBoxLayout()
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(title)
        text.addWidget(subtitle)
        heading.addLayout(text)
        heading.addStretch()
        heading.addWidget(self.refresh_button)

        self.codex_status = StatusBlock(self._t("codex_process"), language=self.language)
        self.storage_status = StatusBlock(self._t("cloud_storage"), language=self.language)
        self.baseline_status = StatusBlock(self._t("parent_baseline"), language=self.language)
        statuses = QGridLayout()
        statuses.setHorizontalSpacing(12)
        statuses.addWidget(self.codex_status, 0, 0)
        statuses.addWidget(self.storage_status, 0, 1)
        statuses.addWidget(self.baseline_status, 0, 2)

        self.route = SyncRoute(language=self.language)
        self.operation_banner = OperationBanner(language=self.language)
        self.operation_banner.cancel_requested.connect(self._cancel_pending_operation)
        self.push_button = ActionButton(self._t("sync_to_cloud"), tone="primary")
        self.pull_button = ActionButton(self._t("sync_from_cloud"), tone="incoming")
        self.preview_button = ActionButton(self._t("preview_update"))
        self.push_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.pull_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.push_button.clicked.connect(
            lambda: self._confirm_run(self._t("sync_to_cloud_question"), self._push)
        )
        self.pull_button.clicked.connect(self._pull)
        self.preview_button.clicked.connect(self._pull)
        actions = QHBoxLayout()
        actions.addWidget(self.push_button)
        actions.addWidget(self.pull_button)
        actions.addWidget(self.preview_button)
        actions.addStretch()
        route_frame = QFrame()
        route_frame.setProperty("card", True)
        route_layout = QVBoxLayout(route_frame)
        route_layout.setContentsMargins(18, 16, 18, 16)
        route_layout.addWidget(QLabel(self._t("synchronization_route")))
        route_layout.addWidget(self.route)
        route_layout.addLayout(actions)

        recent_title = QLabel(self._t("recent_versions"))
        recent_title.setStyleSheet("font-size: 15px; font-weight: 700;")
        self.recent_versions = VersionTable(language=self.language)
        self.recent_versions.setMaximumHeight(205)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(13)
        layout.addLayout(heading)
        layout.addLayout(statuses)
        layout.addWidget(self.operation_banner)
        layout.addWidget(route_frame)
        layout.addWidget(recent_title)
        layout.addWidget(self.recent_versions)

        self.device_label = QLabel()
        self.codex_label = QLabel()
        self.baseline_label = QLabel()
        self.local_label = QLabel()
        self.remote_label = QLabel()
        self.update_label = QLabel()
        self.cancel_wait_button = self.operation_banner.cancel_button
        return page

    def _history_page(self) -> QWidget:
        page = QWidget()
        title = QLabel(self._t("version_history"))
        title.setProperty("role", "heading")
        subtitle = QLabel(self._t("history_subtitle"))
        subtitle.setProperty("role", "subtitle")
        self.versions = VersionTable(language=self.language)
        self.restore_button = ActionButton(self._t("restore_selected"))
        self.restore_button.clicked.connect(self._restore)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(self.versions, 1)
        layout.addWidget(self.restore_button, alignment=Qt.AlignmentFlag.AlignLeft)
        return page

    def _recovery_page(self) -> QWidget:
        page = QWidget()
        title = QLabel(self._t("recovery"))
        title.setProperty("role", "heading")
        subtitle = QLabel(self._t("recovery_subtitle_main"))
        subtitle.setProperty("role", "subtitle")
        self.baseline_detail = StatusBlock(self._t("protected_parent_baseline"), language=self.language)
        self.baseline_button = ActionButton(self._t("create_protected_baseline"), tone="primary")
        self.restore_baseline_button = ActionButton(self._t("restore_protected_baseline"))
        self.baseline_button.clicked.connect(
            lambda: self._confirm_run(self._t("create_baseline_question"), self._baseline)
        )
        self.restore_baseline_button.clicked.connect(self._restore_baseline)
        actions = QHBoxLayout()
        actions.addWidget(self.baseline_button)
        actions.addWidget(self.restore_baseline_button)
        actions.addStretch()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(12)
        layout.addWidget(self.baseline_detail)
        layout.addLayout(actions)
        layout.addStretch()
        return page

    def _settings_page(self) -> QWidget:
        page = QWidget()
        title = QLabel(self._t("settings"))
        title.setProperty("role", "heading")
        self.settings_summary = QLabel(
            self._t(
                "settings_summary",
                device=self.config.device_id,
                platform=self.platform.display_name,
                storage=self._provider_name(),
                seconds=self.config.poll_interval_seconds,
                language_name=LANGUAGE_NAMES[self.language],
            )
        )
        self.settings_summary.setObjectName("reviewSummary")
        self.language_combo = QComboBox()
        for code, name in LANGUAGE_NAMES.items():
            self.language_combo.addItem(name, code)
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(self.language)))
        language_form = QFormLayout()
        language_form.addRow(self._t("language"), self.language_combo)
        self.language_combo.currentIndexChanged.connect(self._change_language)
        updates_label = QLabel(self._t("updates"))
        updates_label.setStyleSheet("font-weight: 700;")
        self.update_button = ActionButton(self._t("check_for_updates"))
        self.update_button.clicked.connect(lambda: self._check_for_updates(manual=True))
        edit = ActionButton(self._t("edit_connection_settings"))
        edit.clicked.connect(self._settings)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(self.settings_summary)
        layout.addLayout(language_form)
        layout.addWidget(edit, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(12)
        layout.addWidget(updates_label)
        layout.addWidget(self.update_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        return page

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(load_app_icon(), self)
        self.tray.setToolTip("Codex Handoff")
        menu = QMenu()
        show_action = QAction(self._t("show"), self)
        show_action.triggered.connect(self._show_from_tray)
        push_action = QAction(self._t("sync_to_cloud"), self)
        push_action.triggered.connect(
            lambda: self._confirm_run(self._t("sync_to_cloud_question"), self._push)
        )
        pull_action = QAction(self._t("sync_from_cloud"), self)
        pull_action.triggered.connect(self._pull)
        check_action = QAction(self._t("check_now"), self)
        check_action.triggered.connect(self._check_now)
        quit_action = QAction(self._t("quit"), self)
        quit_action.triggered.connect(self._quit)
        for action in (show_action, push_action, pull_action, check_action):
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self._show_from_tray() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def _provider_name(self) -> str:
        return "Google Drive" if self.config.provider == "google_drive" else self._t("local_folder")

    def _change_language(self) -> None:
        selected = normalize_language(str(self.language_combo.currentData()))
        if selected == self.language:
            return
        self.config = replace(self.config, language=selected)
        save_config(self.config, self.config_path)
        self.language = selected
        QTimer.singleShot(0, self._reload_interface)

    def _reload_interface(self) -> None:
        self.ui_generation += 1
        if self.monitor:
            self.monitor.stop()
            self.monitor = None
        self.service = None
        old_tray = self.tray
        old_tray.hide()
        old_tray.deleteLater()
        old_content = self.takeCentralWidget()
        if old_content:
            old_content.deleteLater()
        self._build_ui()
        self._build_tray()
        self._connect()

    def _connect(self) -> None:
        self.statusBar().showMessage(self._t("connecting_storage"))
        self.storage_status.set_state(self._t("connecting"), StatusTone.NEUTRAL)
        self._run(lambda: HandoffService(self.config, create_provider(self.config)), self._connected)

    def _connected(self, service: object) -> None:
        self.service = service  # type: ignore[assignment]
        self.storage_status.set_state(
            self._t("provider_connected", provider=self._provider_name()), StatusTone.SUCCESS
        )
        self.monitor = RemoteHeadMonitor(
            self.service.remote_head,
            interval_seconds=self.config.poll_interval_seconds,
            pool=self.pool,
            parent=self,
        )
        self.monitor.head_changed.connect(self._remote_head_changed)
        self.monitor.offline.connect(self._monitor_offline)
        self.monitor.recovered.connect(
            lambda: self.storage_status.set_state(
                self._t("provider_connected", provider=self._provider_name()), StatusTone.SUCCESS
            )
        )
        if self.config.monitoring_enabled:
            self.monitor.start(immediate=False)
        self.refresh()

    def _run(self, function, completed=None) -> None:
        self._set_busy(True)
        if self.monitor:
            self.monitor.pause()
        worker = Worker(function)
        generation = self.ui_generation
        self.workers.add(worker)
        worker.signals.completed.connect(
            lambda value, current=worker: self._worker_completed(
                current, value, completed, generation
            )
        )
        worker.signals.failed.connect(
            lambda message, current=worker: self._worker_failed(current, message, generation)
        )
        self.pool.start(worker)

    def _worker_completed(self, worker: Worker, value: object, callback, generation: int) -> None:
        self.workers.discard(worker)
        if generation != self.ui_generation:
            return
        self._done(value, callback)

    def _worker_failed(self, worker: Worker, message: str, generation: int) -> None:
        self.workers.discard(worker)
        if generation != self.ui_generation:
            return
        self._failed(message)

    def _done(self, value: object, callback) -> None:
        self._set_busy(False)
        self.operation_banner.hide()
        if self.monitor and self.config.monitoring_enabled:
            self.monitor.resume(immediate=False)
        if callback:
            callback(value)
        else:
            self.refresh()

    def _failed(self, message: str) -> None:
        self.pending_operation = None
        self._set_busy(False)
        if self.monitor and self.config.monitoring_enabled:
            self.monitor.resume(immediate=False)
        self.operation_banner.show_message(message, StatusTone.ERROR)
        self.statusBar().showMessage(self._t("operation_failed"))
        QMessageBox.critical(self, "Codex Handoff", message)

    def _set_busy(self, busy: bool) -> None:
        for button in (
            self.baseline_button,
            self.push_button,
            self.pull_button,
            self.preview_button,
            self.restore_button,
            self.restore_baseline_button,
            self.refresh_button,
            self.update_button,
        ):
            button.setEnabled(not busy)

    def _run_when_codex_stopped(self, operation, completed=None) -> None:
        if not is_codex_running():
            self._run(operation, completed)
            return
        self.pending_operation = (operation, completed)
        self._set_busy(True)
        self.operation_banner.show_message(
            self._t("close_codex_wait"),
            StatusTone.WARNING,
            cancellable=True,
        )
        QMessageBox.warning(
            self,
            self._t("close_codex"),
            self._t("close_codex_message"),
        )

    def _try_pending_operation(self) -> None:
        if self.pending_operation is None or is_codex_running():
            return
        operation, completed = self.pending_operation
        self.pending_operation = None
        self.operation_banner.hide()
        self._run(operation, completed)

    def _cancel_pending_operation(self) -> None:
        self.pending_operation = None
        self.operation_banner.hide()
        self._set_busy(False)
        self.statusBar().showMessage(self._t("waiting_cancelled"), 5000)

    def refresh(self) -> None:
        if self.service is not None:
            self.statusBar().showMessage(self._t("refreshing"))
            self._run(lambda: (self.service.status(), self.service.list_versions()), self._show_status)

    def _background_refresh(self) -> None:
        if self.service is None or self.pool.activeThreadCount() > 0:
            return
        worker = Worker(lambda: (self.service.status(), self.service.list_versions()))
        generation = self.ui_generation
        self.workers.add(worker)
        worker.signals.completed.connect(
            lambda value, current=worker: self._background_completed(current, value, generation)
        )
        worker.signals.failed.connect(
            lambda message, current=worker: self._background_failed(current, message, generation)
        )
        self.pool.start(worker)

    def _background_completed(self, worker: Worker, value: object, generation: int) -> None:
        self.workers.discard(worker)
        if generation != self.ui_generation:
            return
        self._show_status(value)

    def _background_failed(self, worker: Worker, message: str, generation: int) -> None:
        self.workers.discard(worker)
        if generation != self.ui_generation:
            return
        self._monitor_offline(message)

    def _show_status(self, result: object) -> None:
        status, versions = result  # type: ignore[misc]
        self.device_label.setText(str(status["device_id"]))
        codex_running = bool(status["codex_running"])
        self.codex_label.setText(self._t("running" if codex_running else "closed"))
        self.codex_status.set_state(
            self._t("running_close" if codex_running else "closed_ready"),
            StatusTone.WARNING if codex_running else StatusTone.SUCCESS,
        )
        baseline_id = str(status["baseline_id"] or "")
        self.baseline_label.setText(baseline_id or self._t("not_created"))
        self.baseline_status.set_state(
            self._t("protected" if baseline_id else "not_created"),
            StatusTone.SUCCESS if baseline_id else StatusTone.WARNING,
        )
        self.baseline_detail.set_state(
            baseline_id or self._t("no_protected_baseline"),
            StatusTone.SUCCESS if baseline_id else StatusTone.WARNING,
        )
        self.local_label.setText(str(status["last_applied_version"] or self._t("none")))
        self.remote_label.setText(str(status["remote_head"] or self._t("none")))
        update_available = bool(status["update_available"])
        requires_initial_sync = bool(status.get("requires_initial_sync"))
        can_publish = bool(status.get("can_publish"))
        self.requires_initial_sync = requires_initial_sync
        self.remote_update_available = update_available
        self.update_label.setText(self._t("available" if update_available else "up_to_date"))
        if requires_initial_sync:
            self.update_label.setText(self._t("initial_sync_required"))
        self.preview_button.setEnabled(update_available)
        self.pull_button.setText(
            self._t("initialize_from_baseline")
            if requires_initial_sync and not update_available
            else self._t("sync_from_cloud")
        )
        self.pull_button.setEnabled(update_available or requires_initial_sync)
        self.route.set_route(
            self._local_platform_label(),
            str(status["device_id"]),
            self._provider_name(),
            str(status["remote_source"]) if status["remote_source"] else None,
            next((item.source_platform for item in versions if item.version_id == status["remote_head"]), None),
        )
        has_baseline = bool(baseline_id)
        if self.pending_operation is None:
            self.baseline_button.setEnabled(not has_baseline and self.config.pair_mode == "create_pair")
            self.push_button.setEnabled(can_publish)
            self.restore_baseline_button.setEnabled(has_baseline)
            if requires_initial_sync:
                instruction = (
                    self._t("new_device_apply")
                    if update_available
                    else self._t("new_device_baseline")
                )
                self.operation_banner.show_message(instruction, StatusTone.WARNING)
            elif self.operation_banner.isVisible():
                self.operation_banner.hide()
        self.versions.set_versions(versions)
        self.recent_versions.set_versions(versions[:3])
        if self.monitor:
            self.monitor.last_version_id = str(status["remote_head"]) if status["remote_head"] else None
        self.statusBar().showMessage(self._t("ready"))

    def _remote_head_changed(self, head: RemoteHead) -> None:
        if head.version_id != self.last_notified_version:
            self.tray.showMessage(
                self._t("update_available_title"),
                self._t("update_available_message", device=head.source_device),
                QSystemTrayIcon.MessageIcon.Information,
                8000,
            )
            self.last_notified_version = head.version_id
        self._background_refresh()

    def _monitor_offline(self, message: str) -> None:
        self.storage_status.set_state(self._t("offline"), StatusTone.ERROR)
        self.operation_banner.show_message(
            self._t("storage_check_failed", message=message), StatusTone.ERROR
        )

    def _check_now(self) -> None:
        if self.monitor:
            self.monitor.check_now()
        else:
            self.refresh()

    def _check_for_updates(self, *, manual: bool) -> None:
        if self.updater is None or (manual and not is_packaged_application()):
            if manual:
                QMessageBox.information(
                    self,
                    self._t("updates"),
                    self._t("updates_installed_only"),
                )
            return
        if not manual and not self.updater.should_check():
            return
        if manual:
            self.statusBar().showMessage(self._t("checking_for_updates"))
            self._run(
                self.updater.check,
                lambda result: self._update_checked(result, manual=True),
            )
            return
        worker = Worker(self.updater.check)
        generation = self.ui_generation
        self.workers.add(worker)
        worker.signals.completed.connect(
            lambda result, current=worker: self._silent_update_check_completed(
                current, result, generation
            )
        )
        worker.signals.failed.connect(
            lambda _message, current=worker: self.workers.discard(current)
        )
        self.pool.start(worker)

    def _silent_update_check_completed(
        self, worker: Worker, result: object, generation: int
    ) -> None:
        self.workers.discard(worker)
        if generation != self.ui_generation:
            return
        self._update_checked(result, manual=False)

    def _update_checked(self, result: object, *, manual: bool) -> None:
        update = result if isinstance(result, UpdateInfo) else None
        if update is None:
            if manual:
                QMessageBox.information(
                    self,
                    self._t("updates"),
                    self._t("latest_version_installed"),
                )
            self.statusBar().showMessage(self._t("ready"))
            return
        dialog = ApplicationUpdateDialog(
            update,
            __version__,
            self,
            language=self.language,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            assert self.updater is not None
            self.statusBar().showMessage(self._t("downloading_update"))
            self._run(
                lambda: self.updater.download(update),
                self._confirm_install_update,
            )

    def _confirm_install_update(self, package: object) -> None:
        dialog = QMessageBox(
            QMessageBox.Icon.Question,
            self._t("install_update_title"),
            self._t("install_update_question"),
            parent=self,
        )
        dialog.setStandardButtons(
            QMessageBox.StandardButton.Apply | QMessageBox.StandardButton.Cancel
        )
        dialog.button(QMessageBox.StandardButton.Apply).setText(self._t("install_now"))
        dialog.button(QMessageBox.StandardButton.Cancel).setText(self._t("cancel"))
        if dialog.exec() == QMessageBox.StandardButton.Apply:
            self._install_update(package)
        else:
            self.statusBar().showMessage(self._t("ready"))

    def _install_update(self, package: object) -> None:
        try:
            launch_update(
                Path(package),
                self.platform.key,
                application=application_path(),
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                self._t("updates"),
                self._t("update_launch_failed", message=str(exc)),
            )
            self.statusBar().showMessage(self._t("operation_failed"))
            return
        self._quit()

    def _confirm_run(self, question: str, operation) -> None:
        dialog = QMessageBox(QMessageBox.Icon.Question, self._t("confirm"), question, parent=self)
        dialog.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        dialog.button(QMessageBox.StandardButton.Yes).setText(self._t("confirm_action"))
        dialog.button(QMessageBox.StandardButton.Cancel).setText(self._t("cancel"))
        if dialog.exec() == QMessageBox.StandardButton.Yes:
            self._run_when_codex_stopped(operation, lambda _: self.refresh())

    def _baseline(self):
        assert self.service
        return self.service.create_baseline()

    def _push(self):
        assert self.service
        return self.service.push()

    def _pull(self) -> None:
        if self.service is not None:
            if self.requires_initial_sync and not self.remote_update_available:
                self._restore_baseline()
                return
            self._run(self.service.preview_pull, self._confirm_pull)

    def build_preview_dialog(self, preview: ApplyPreview) -> UpdatePreviewDialog:
        return UpdatePreviewDialog(preview, self, language=self.language)

    def _confirm_pull(self, preview: object) -> None:
        if preview is None:
            QMessageBox.information(self, "Codex Handoff", self._t("no_update"))
            return
        dialog = self.build_preview_dialog(preview)  # type: ignore[arg-type]
        if dialog.exec() == QDialog.DialogCode.Accepted:
            assert self.service
            self._run_when_codex_stopped(self.service.pull, lambda _: self.refresh())

    def _restore(self) -> None:
        identifier = self.versions.selected_version_id()
        if identifier is None or self.service is None:
            QMessageBox.information(self, "Codex Handoff", self._t("select_version_first"))
            return
        self._confirm_run(
            self._t("restore_version_question", version=identifier),
            lambda: self.service.restore(identifier),
        )

    def _restore_baseline(self) -> None:
        if self.service is None:
            return
        baseline_id = self.baseline_label.text()
        if not baseline_id or baseline_id == self._t("not_created"):
            QMessageBox.information(self, "Codex Handoff", self._t("no_baseline_available"))
            return
        self._confirm_run(
            self._t("restore_baseline_question", baseline=baseline_id),
            lambda: self.service.restore(baseline_id),
        )

    def _settings(self) -> None:
        dialog = SetupWizard(self.config_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config = load_config(self.config_path)
            self.language = normalize_language(self.config.language)
            self._reload_interface()

    def _show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        self._quitting = True
        if self.monitor:
            self.monitor.stop()
        self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        if (
            not self._quitting
            and self.config.monitoring_enabled
            and self.config.minimize_to_tray
            and QSystemTrayIcon.isSystemTrayAvailable()
        ):
            event.ignore()
            self.hide()
            if not self.config.close_notice_seen:
                self.tray.showMessage(
                    self._t("still_running_title"),
                    self._t("still_running_message"),
                    QSystemTrayIcon.MessageIcon.Information,
                    6000,
                )
                self.config = replace(self.config, close_notice_seen=True)
                save_config(self.config, self.config_path)
            return
        event.accept()
