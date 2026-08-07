from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
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
    QVBoxLayout,
    QWidget,
)

from ..config import AppConfig, load_config, save_config
from ..models import ApplyPreview, RemoteHead
from ..monitor import RemoteHeadMonitor
from ..processes import is_codex_running
from ..service import HandoffService, create_provider
from .platform import current_platform
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
    def __init__(self, preview: ApplyPreview, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.preview = preview
        self.setWindowTitle("Review synchronization update")
        self.setMinimumSize(660, 500)
        title = QLabel("Review incoming update")
        title.setProperty("role", "heading")
        platform_names = {"windows": "Windows", "macos": "macOS"}
        details = QLabel(
            f"Source: {preview.source_device} ({platform_names.get(preview.source_platform or '', 'Unknown platform')})\n"
            f"Version: {preview.version_id}\nCreated: {preview.created_at or 'Unknown'}"
        )
        details.setProperty("role", "subtitle")
        counts = QHBoxLayout()
        added_frame, self.added_count = self._count("Added", len(preview.added), StatusTone.SUCCESS)
        changed_frame, self.changed_count = self._count("Changed", len(preview.changed), StatusTone.WARNING)
        removed_frame, self.removed_count = self._count("Removed", len(preview.removed), StatusTone.ERROR)
        for widget in (added_frame, changed_frame, removed_frame):
            counts.addWidget(widget)
        tabs = QTabWidget()
        for name, paths in (
            ("Added", preview.added),
            ("Changed", preview.changed),
            ("Removed", preview.removed),
            ("Unchanged", preview.unchanged),
        ):
            listing = QListWidget()
            listing.addItems(paths or ("No files",))
            tabs.addTab(listing, f"{name} ({len(paths)})")
        note = QLabel("Codex must be closed. A local encrypted backup is created before applying this update.")
        note.setWordWrap(True)
        note.setObjectName("warningNote")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Apply).setText("Apply update")
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


class MainWindow(QMainWindow):
    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.config_path = config_path
        self.config = load_config(config_path)
        self.platform = current_platform()
        self.service: HandoffService | None = None
        self.monitor: RemoteHeadMonitor | None = None
        self.pool = QThreadPool.globalInstance()
        self.workers: set[Worker] = set()
        self.last_notified_version: str | None = None
        self.pending_operation: tuple[object, object] | None = None
        self.requires_initial_sync = False
        self.remote_update_available = False
        self._quitting = False
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
        self._connect()

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
        for index, label in enumerate(("Synchronization", "Version history", "Recovery", "Settings")):
            button = NavigationButton(label)
            button.clicked.connect(lambda checked=False, page=index: self.pages.setCurrentIndex(page))
            self.nav_buttons.append(button)
            self.navigation.addWidget(button)
        self.nav_buttons[0].setChecked(True)
        self.navigation.addStretch()
        privacy = QLabel("Encrypted locally\nRecovery key stays on this device")
        privacy.setStyleSheet("color: #829599; font-size: 11px; padding: 8px;")
        self.navigation.addWidget(privacy)
        sidebar = QFrame()
        sidebar.setStyleSheet(f"background: {CHARCOAL};")
        sidebar.setFixedWidth(190)
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
        title = QLabel("Synchronization")
        title.setProperty("role", "heading")
        subtitle = QLabel("Controlled, encrypted updates between your devices.")
        subtitle.setProperty("role", "subtitle")
        self.refresh_button = ActionButton("Refresh")
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

        self.codex_status = StatusBlock("Codex process")
        self.storage_status = StatusBlock("Cloud storage")
        self.baseline_status = StatusBlock("Parent baseline")
        statuses = QGridLayout()
        statuses.setHorizontalSpacing(12)
        statuses.addWidget(self.codex_status, 0, 0)
        statuses.addWidget(self.storage_status, 0, 1)
        statuses.addWidget(self.baseline_status, 0, 2)

        self.route = SyncRoute()
        self.operation_banner = OperationBanner()
        self.operation_banner.cancel_requested.connect(self._cancel_pending_operation)
        self.push_button = ActionButton("Sync to cloud", tone="primary")
        self.pull_button = ActionButton("Sync from cloud", tone="incoming")
        self.preview_button = ActionButton("Preview update")
        self.push_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.pull_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.push_button.clicked.connect(
            lambda: self._confirm_run("Synchronize this device state to the cloud?", self._push)
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
        route_layout.addWidget(QLabel("Synchronization route"))
        route_layout.addWidget(self.route)
        route_layout.addLayout(actions)

        recent_title = QLabel("Recent versions")
        recent_title.setStyleSheet("font-size: 15px; font-weight: 700;")
        self.recent_versions = VersionTable()
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
        title = QLabel("Version history")
        title.setProperty("role", "heading")
        subtitle = QLabel("Immutable versions published by connected devices.")
        subtitle.setProperty("role", "subtitle")
        self.versions = VersionTable()
        self.restore_button = ActionButton("Restore selected")
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
        title = QLabel("Recovery")
        title.setProperty("role", "heading")
        subtitle = QLabel("Restore a protected baseline or a selected version.")
        subtitle.setProperty("role", "subtitle")
        self.baseline_detail = StatusBlock("Protected parent baseline")
        self.baseline_button = ActionButton("Create protected baseline", tone="primary")
        self.restore_baseline_button = ActionButton("Restore protected baseline")
        self.baseline_button.clicked.connect(
            lambda: self._confirm_run("Create the immutable parent baseline?", self._baseline)
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
        title = QLabel("Settings")
        title.setProperty("role", "heading")
        self.settings_summary = QLabel(
            f"Device: {self.config.device_id}\n"
            f"Platform: {self.platform.display_name}\n"
            f"Storage: {self._provider_name()}\n"
            f"Update check: every {self.config.poll_interval_seconds} seconds"
        )
        self.settings_summary.setObjectName("reviewSummary")
        edit = ActionButton("Edit connection settings")
        edit.clicked.connect(self._settings)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(self.settings_summary)
        layout.addWidget(edit, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        return page

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(load_app_icon(), self)
        self.tray.setToolTip("Codex Handoff")
        menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self._show_from_tray)
        push_action = QAction("Sync to cloud", self)
        push_action.triggered.connect(
            lambda: self._confirm_run("Synchronize this device state to the cloud?", self._push)
        )
        pull_action = QAction("Sync from cloud", self)
        pull_action.triggered.connect(self._pull)
        check_action = QAction("Check now", self)
        check_action.triggered.connect(self._check_now)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit)
        for action in (show_action, push_action, pull_action, check_action):
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self._show_from_tray() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def _provider_name(self) -> str:
        return "Google Drive" if self.config.provider == "google_drive" else "Local folder"

    def _connect(self) -> None:
        self.statusBar().showMessage("Connecting to storage...")
        self.storage_status.set_state("Connecting...", StatusTone.NEUTRAL)
        self._run(lambda: HandoffService(self.config, create_provider(self.config)), self._connected)

    def _connected(self, service: object) -> None:
        self.service = service  # type: ignore[assignment]
        self.storage_status.set_state(f"{self._provider_name()} connected", StatusTone.SUCCESS)
        self.monitor = RemoteHeadMonitor(
            self.service.remote_head,
            interval_seconds=self.config.poll_interval_seconds,
            pool=self.pool,
            parent=self,
        )
        self.monitor.head_changed.connect(self._remote_head_changed)
        self.monitor.offline.connect(self._monitor_offline)
        self.monitor.recovered.connect(lambda: self.storage_status.set_state(f"{self._provider_name()} connected", StatusTone.SUCCESS))
        if self.config.monitoring_enabled:
            self.monitor.start(immediate=False)
        self.refresh()

    def _run(self, function, completed=None) -> None:
        self._set_busy(True)
        if self.monitor:
            self.monitor.pause()
        worker = Worker(function)
        self.workers.add(worker)
        worker.signals.completed.connect(lambda value, current=worker: self._worker_completed(current, value, completed))
        worker.signals.failed.connect(lambda message, current=worker: self._worker_failed(current, message))
        self.pool.start(worker)

    def _worker_completed(self, worker: Worker, value: object, callback) -> None:
        self.workers.discard(worker)
        self._done(value, callback)

    def _worker_failed(self, worker: Worker, message: str) -> None:
        self.workers.discard(worker)
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
        self.statusBar().showMessage("Operation failed")
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
        ):
            button.setEnabled(not busy)

    def _run_when_codex_stopped(self, operation, completed=None) -> None:
        if not is_codex_running():
            self._run(operation, completed)
            return
        self.pending_operation = (operation, completed)
        self._set_busy(True)
        self.operation_banner.show_message(
            "Close Codex. The confirmed operation starts automatically when it exits.",
            StatusTone.WARNING,
            cancellable=True,
        )
        QMessageBox.warning(
            self,
            "Close Codex",
            "Codex is still running. Close it to continue, or cancel the waiting operation.",
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
        self.statusBar().showMessage("Waiting operation cancelled", 5000)

    def refresh(self) -> None:
        if self.service is not None:
            self.statusBar().showMessage("Refreshing...")
            self._run(lambda: (self.service.status(), self.service.list_versions()), self._show_status)

    def _background_refresh(self) -> None:
        if self.service is None or self.pool.activeThreadCount() > 0:
            return
        worker = Worker(lambda: (self.service.status(), self.service.list_versions()))
        self.workers.add(worker)
        worker.signals.completed.connect(lambda value, current=worker: self._background_completed(current, value))
        worker.signals.failed.connect(lambda message, current=worker: self._background_failed(current, message))
        self.pool.start(worker)

    def _background_completed(self, worker: Worker, value: object) -> None:
        self.workers.discard(worker)
        self._show_status(value)

    def _background_failed(self, worker: Worker, message: str) -> None:
        self.workers.discard(worker)
        self._monitor_offline(message)

    def _show_status(self, result: object) -> None:
        status, versions = result  # type: ignore[misc]
        self.device_label.setText(str(status["device_id"]))
        codex_running = bool(status["codex_running"])
        self.codex_label.setText("Running" if codex_running else "Closed")
        self.codex_status.set_state(
            "Running - close before sync" if codex_running else "Closed - ready",
            StatusTone.WARNING if codex_running else StatusTone.SUCCESS,
        )
        baseline_id = str(status["baseline_id"] or "")
        self.baseline_label.setText(baseline_id or "Not created")
        self.baseline_status.set_state("Protected" if baseline_id else "Not created", StatusTone.SUCCESS if baseline_id else StatusTone.WARNING)
        self.baseline_detail.set_state(baseline_id or "No protected baseline", StatusTone.SUCCESS if baseline_id else StatusTone.WARNING)
        self.local_label.setText(str(status["last_applied_version"] or "None"))
        self.remote_label.setText(str(status["remote_head"] or "None"))
        update_available = bool(status["update_available"])
        requires_initial_sync = bool(status.get("requires_initial_sync"))
        can_publish = bool(status.get("can_publish"))
        self.requires_initial_sync = requires_initial_sync
        self.remote_update_available = update_available
        self.update_label.setText("Available" if update_available else "Up to date")
        if requires_initial_sync:
            self.update_label.setText("Initial sync required")
        self.preview_button.setEnabled(update_available)
        self.pull_button.setText(
            "Initialize from baseline" if requires_initial_sync and not update_available else "Sync from cloud"
        )
        self.pull_button.setEnabled(update_available or requires_initial_sync)
        self.route.set_route(
            self.platform.local_label,
            str(status["device_id"]),
            self._provider_name(),
            str(status["remote_source"]) if status["remote_source"] else None,
            next((item.source_platform for item in versions if item.version_id == status["remote_head"]), None),
        )
        has_baseline = bool(baseline_id)
        if self.pending_operation is None:
            self.baseline_button.setEnabled(not has_baseline)
            self.push_button.setEnabled(can_publish)
            self.restore_baseline_button.setEnabled(has_baseline)
            if requires_initial_sync:
                instruction = (
                    "This is a new device. Review and apply the latest cloud version before publishing."
                    if update_available
                    else "This is a new device. Initialize it from the protected baseline before publishing."
                )
                self.operation_banner.show_message(instruction, StatusTone.WARNING)
            elif self.operation_banner.isVisible():
                self.operation_banner.hide()
        self.versions.set_versions(versions)
        self.recent_versions.set_versions(versions[:3])
        if self.monitor:
            self.monitor.last_version_id = str(status["remote_head"]) if status["remote_head"] else None
        self.statusBar().showMessage("Ready")

    def _remote_head_changed(self, head: RemoteHead) -> None:
        if head.version_id != self.last_notified_version:
            self.tray.showMessage(
                "Codex synchronization update available",
                f"A new encrypted version from {head.source_device} is ready to review.",
                QSystemTrayIcon.MessageIcon.Information,
                8000,
            )
            self.last_notified_version = head.version_id
        self._background_refresh()

    def _monitor_offline(self, message: str) -> None:
        self.storage_status.set_state("Offline", StatusTone.ERROR)
        self.operation_banner.show_message(f"Storage check failed: {message}", StatusTone.ERROR)

    def _check_now(self) -> None:
        if self.monitor:
            self.monitor.check_now()
        else:
            self.refresh()

    def _confirm_run(self, question: str, operation) -> None:
        if QMessageBox.question(self, "Confirm", question) == QMessageBox.StandardButton.Yes:
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
        return UpdatePreviewDialog(preview, self)

    def _confirm_pull(self, preview: object) -> None:
        if preview is None:
            QMessageBox.information(self, "Codex Handoff", "No update is available.")
            return
        dialog = self.build_preview_dialog(preview)  # type: ignore[arg-type]
        if dialog.exec() == QDialog.DialogCode.Accepted:
            assert self.service
            self._run_when_codex_stopped(self.service.pull, lambda _: self.refresh())

    def _restore(self) -> None:
        identifier = self.versions.selected_version_id()
        if identifier is None or self.service is None:
            QMessageBox.information(self, "Codex Handoff", "Select a version first.")
            return
        self._confirm_run(
            f"Restore {identifier}? A local backup will be created first.",
            lambda: self.service.restore(identifier),
        )

    def _restore_baseline(self) -> None:
        if self.service is None:
            return
        baseline_id = self.baseline_label.text()
        if not baseline_id or baseline_id == "Not created":
            QMessageBox.information(self, "Codex Handoff", "No protected baseline is available.")
            return
        self._confirm_run(
            f"Restore protected baseline {baseline_id}? A local backup will be created first.",
            lambda: self.service.restore(baseline_id),
        )

    def _settings(self) -> None:
        dialog = SetupWizard(self.config_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config = load_config(self.config_path)
            if self.monitor:
                self.monitor.stop()
            self.service = None
            self._connect()

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
                    "Codex Handoff is still running",
                    "Synchronization monitoring continues in the system tray.",
                    QSystemTrayIcon.MessageIcon.Information,
                    6000,
                )
                self.config = replace(self.config, close_notice_seen=True)
                save_config(self.config, self.config_path)
            return
        event.accept()
