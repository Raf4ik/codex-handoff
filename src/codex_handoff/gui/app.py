from __future__ import annotations

from pathlib import Path
import socket
import sys

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..config import AppConfig, default_config_path, default_workspace, load_config, save_config, validate_config
from ..crypto import generate_recovery_key
from ..processes import is_codex_running
from ..service import HandoffService, create_provider


class SetupDialog(QDialog):
    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.config_path = config_path
        self.setWindowTitle("Codex Handoff Setup")
        self.setMinimumWidth(700)
        existing = load_config(config_path) if config_path.is_file() else None
        form = QFormLayout()
        self.device = QLineEdit(existing.device_id if existing else socket.gethostname())
        self.source = QLineEdit(str(existing.source_dir if existing else Path.home() / ".codex"))
        self.workspace = QLineEdit(str(existing.workspace_dir if existing else default_workspace()))
        self.provider = QComboBox()
        self.provider.addItem("Google Drive", "google_drive")
        self.provider.addItem("Local folder", "local")
        self.storage = QLineEdit(str(existing.local_storage_dir if existing and existing.local_storage_dir else Path.home() / "CodexHandoffStorage"))
        self.secrets = QLineEdit(str(existing.google_client_secrets or "") if existing else "")
        self.recovery_key = QLineEdit(str(existing.encryption_key_file if existing and existing.encryption_key_file else default_workspace() / "recovery.key"))
        for field in (self.source, self.workspace, self.storage, self.secrets, self.recovery_key):
            field.setCursorPosition(0)
        if existing:
            self.provider.setCurrentIndex(self.provider.findData(existing.provider))
        self.storage_row = self._path_row(self.storage, False)
        self.secrets_row = self._path_row(self.secrets, True)
        form.addRow("Device name", self.device)
        form.addRow("Codex state", self._path_row(self.source, False))
        form.addRow("Local workspace", self._path_row(self.workspace, False))
        form.addRow("Cloud provider", self.provider)
        form.addRow("Local provider folder", self.storage_row)
        form.addRow("Google OAuth JSON", self.secrets_row)
        form.addRow("Recovery key", self._recovery_key_row())
        note = QLabel(
            "Google Drive opens a browser for OAuth. The OAuth JSON and token remain on this device. "
            "Confirmed operations wait until Codex is closed."
        )
        note.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)
        self.provider.currentIndexChanged.connect(self._update_provider_fields)
        self._update_provider_fields()

    def _update_provider_fields(self) -> None:
        google_drive = self.provider.currentData() == "google_drive"
        self.secrets_row.setEnabled(google_drive)
        self.storage_row.setEnabled(not google_drive)

    def _path_row(self, field: QLineEdit, file_mode: bool) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        button = QPushButton("Browse")
        button.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        button.clicked.connect(lambda: self._browse(field, file_mode))
        layout.addWidget(field)
        layout.addWidget(button)
        return widget

    def _browse(self, field: QLineEdit, file_mode: bool) -> None:
        if file_mode:
            selected, _ = QFileDialog.getOpenFileName(self, "Select OAuth client JSON", filter="JSON (*.json)")
        else:
            selected = QFileDialog.getExistingDirectory(self, "Select directory")
        if selected:
            field.setText(selected)

    def _recovery_key_row(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        select = QPushButton("Select")
        create = QPushButton("Create new")
        select.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        create.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        select.clicked.connect(lambda: self._browse(self.recovery_key, True))
        create.clicked.connect(self._create_recovery_key)
        layout.addWidget(self.recovery_key)
        layout.addWidget(select)
        layout.addWidget(create)
        return widget

    def _create_recovery_key(self) -> None:
        selected, _ = QFileDialog.getSaveFileName(
            self, "Create recovery key", self.recovery_key.text(), "Key files (*.key)"
        )
        if not selected:
            return
        try:
            generate_recovery_key(Path(selected))
        except Exception as exc:
            QMessageBox.critical(self, "Codex Handoff", str(exc))
            return
        self.recovery_key.setText(selected)
        QMessageBox.information(
            self,
            "Recovery key created",
            "Keep a secure offline copy. Select a copy of this same key on every device. Lost keys cannot be recovered.",
        )

    def _save(self) -> None:
        config = AppConfig(
            device_id=self.device.text().strip(),
            source_dir=Path(self.source.text()).expanduser(),
            workspace_dir=Path(self.workspace.text()).expanduser(),
            provider=str(self.provider.currentData()),
            local_storage_dir=Path(self.storage.text()).expanduser() if self.provider.currentData() == "local" else None,
            google_client_secrets=Path(self.secrets.text()).expanduser() if self.provider.currentData() == "google_drive" else None,
            encryption_key_file=Path(self.recovery_key.text()).expanduser() if self.recovery_key.text().strip() else None,
        )
        try:
            validate_config(config)
        except Exception as exc:
            QMessageBox.critical(self, "Invalid setup", str(exc))
            return
        save_config(config, self.config_path)
        self.accept()


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


class MainWindow(QMainWindow):
    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.config_path = config_path
        self.config = load_config(config_path)
        self.service: HandoffService | None = None
        self.pool = QThreadPool.globalInstance()
        self.workers: set[Worker] = set()
        self.last_notified_version: str | None = None
        self.pending_operation: tuple[object, object] | None = None
        self.setWindowTitle("Codex Handoff")
        self.resize(820, 560)
        self.device_label = QLabel()
        self.codex_label = QLabel()
        self.baseline_label = QLabel()
        self.local_label = QLabel()
        self.remote_label = QLabel()
        self.update_label = QLabel()
        self.versions = QListWidget()
        self.baseline_button = QPushButton("Create baseline")
        self.push_button = QPushButton("Send snapshot")
        self.pull_button = QPushButton("Receive update")
        self.restore_button = QPushButton("Restore selected")
        self.restore_baseline_button = QPushButton("Restore baseline")
        self.refresh_button = QPushButton("Refresh")
        self.cancel_wait_button = QPushButton("Cancel waiting")
        self.cancel_wait_button.setVisible(False)
        self.baseline_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.push_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.pull_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        self.refresh_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.restore_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.restore_baseline_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.cancel_wait_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
        self.baseline_button.clicked.connect(lambda: self._confirm_run("Create the immutable parent baseline?", self._baseline))
        self.push_button.clicked.connect(lambda: self._confirm_run("Publish this device state? Codex must be closed.", self._push))
        self.pull_button.clicked.connect(self._pull)
        self.restore_button.clicked.connect(self._restore)
        self.restore_baseline_button.clicked.connect(self._restore_baseline)
        self.refresh_button.clicked.connect(self.refresh)
        self.cancel_wait_button.clicked.connect(self._cancel_pending_operation)
        controls = QHBoxLayout()
        for button in (self.baseline_button, self.push_button, self.pull_button, self.refresh_button):
            controls.addWidget(button)
        details = QFormLayout()
        details.addRow("Device", self.device_label)
        details.addRow("Codex", self.codex_label)
        details.addRow("Protected baseline", self.baseline_label)
        details.addRow("Last applied", self.local_label)
        details.addRow("Remote version", self.remote_label)
        details.addRow("Update", self.update_label)
        body = QVBoxLayout()
        body.addLayout(details)
        body.addLayout(controls)
        body.addWidget(QLabel("Version history"))
        body.addWidget(self.versions)
        body.addWidget(self.restore_button)
        body.addWidget(self.restore_baseline_button)
        body.addWidget(self.cancel_wait_button)
        container = QWidget()
        container.setLayout(body)
        self.setCentralWidget(container)
        self.setStatusBar(QStatusBar())
        app_icon = self.style().standardIcon(QStyle.SP_DriveNetIcon)
        self.setWindowIcon(app_icon)
        self.tray = QSystemTrayIcon(app_icon, self)
        self.tray.setToolTip("Codex Handoff")
        self.tray.show()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(30_000)
        self.refresh_timer.timeout.connect(self._background_refresh)
        self.refresh_timer.start()
        self.codex_wait_timer = QTimer(self)
        self.codex_wait_timer.setInterval(1_000)
        self.codex_wait_timer.timeout.connect(self._try_pending_operation)
        self.codex_wait_timer.start()
        settings = QAction("Settings", self)
        settings.triggered.connect(self._settings)
        self.menuBar().addMenu("Codex Handoff").addAction(settings)
        self._connect()

    def _connect(self) -> None:
        self.statusBar().showMessage("Connecting to storage...")
        self._run(lambda: HandoffService(self.config, create_provider(self.config)), self._connected)

    def _connected(self, service: object) -> None:
        self.service = service  # type: ignore[assignment]
        self.statusBar().showMessage("Connected", 3000)
        self.refresh()

    def _run(self, function, completed=None) -> None:
        self._set_busy(True)
        worker = Worker(function)
        self.workers.add(worker)
        worker.signals.completed.connect(
            lambda value, current=worker: self._worker_completed(current, value, completed)
        )
        worker.signals.failed.connect(
            lambda message, current=worker: self._worker_failed(current, message)
        )
        self.pool.start(worker)

    def _worker_completed(self, worker: Worker, value: object, callback) -> None:
        self.workers.discard(worker)
        self._done(value, callback)

    def _worker_failed(self, worker: Worker, message: str) -> None:
        self.workers.discard(worker)
        self._failed(message)

    def _done(self, value: object, callback) -> None:
        self._set_busy(False)
        if callback:
            callback(value)
        else:
            self.refresh()

    def _failed(self, message: str) -> None:
        self.pending_operation = None
        self.cancel_wait_button.setVisible(False)
        self._set_busy(False)
        self.statusBar().showMessage("Operation failed")
        QMessageBox.critical(self, "Codex Handoff", message)

    def _set_busy(self, busy: bool) -> None:
        for button in (self.baseline_button, self.push_button, self.pull_button, self.restore_button, self.restore_baseline_button, self.refresh_button):
            button.setEnabled(not busy)

    def _run_when_codex_stopped(self, operation, completed=None) -> None:
        """Queue a mutating operation and start it as soon as Codex exits."""
        if not is_codex_running():
            self._run(operation, completed)
            return
        self.pending_operation = (operation, completed)
        self.cancel_wait_button.setVisible(True)
        self._set_busy(True)
        self.statusBar().showMessage("Close Codex; the confirmed operation will start automatically.")
        QMessageBox.warning(
            self,
            "Close Codex",
            "Codex is still running. Close it to continue. The confirmed operation will start automatically, or cancel it below.",
        )

    def _try_pending_operation(self) -> None:
        if self.pending_operation is None:
            return
        if is_codex_running():
            self.statusBar().showMessage("Waiting for Codex to close...")
            return
        operation, completed = self.pending_operation
        self.pending_operation = None
        self.cancel_wait_button.setVisible(False)
        self._run(operation, completed)

    def _cancel_pending_operation(self) -> None:
        self.pending_operation = None
        self.cancel_wait_button.setVisible(False)
        self._set_busy(False)
        self.statusBar().showMessage("Waiting operation cancelled", 5000)

    def refresh(self) -> None:
        if self.service is None:
            return
        self.statusBar().showMessage("Refreshing...")
        self._run(lambda: (self.service.status(), self.service.list_versions()), self._show_status)

    def _background_refresh(self) -> None:
        if self.service is None or self.pool.activeThreadCount() > 0:
            return
        worker = Worker(lambda: (self.service.status(), self.service.list_versions()))
        self.workers.add(worker)
        worker.signals.completed.connect(
            lambda value, current=worker: self._background_completed(current, value)
        )
        worker.signals.failed.connect(
            lambda message, current=worker: self._background_failed(current, message)
        )
        self.pool.start(worker)

    def _background_completed(self, worker: Worker, value: object) -> None:
        self.workers.discard(worker)
        self._show_status(value)

    def _background_failed(self, worker: Worker, message: str) -> None:
        self.workers.discard(worker)
        self.statusBar().showMessage(f"Background check failed: {message}", 5000)

    def _show_status(self, result: object) -> None:
        status, versions = result  # type: ignore[misc]
        self.device_label.setText(str(status["device_id"]))
        self.codex_label.setText("Running - close it before operations" if status["codex_running"] else "Closed")
        self.baseline_label.setText(str(status["baseline_id"] or "Not created"))
        self.local_label.setText(str(status["last_applied_version"] or "None"))
        self.remote_label.setText(str(status["remote_head"] or "None"))
        self.update_label.setText("Available" if status["update_available"] else "Up to date")
        if self.pending_operation is None:
            has_baseline = bool(status["baseline_id"])
            self.baseline_button.setEnabled(not has_baseline)
            self.push_button.setEnabled(has_baseline)
            self.restore_baseline_button.setEnabled(has_baseline)
        if status["update_available"] and status["remote_head"] != self.last_notified_version:
            source = status["remote_source"] or "another device"
            self.tray.showMessage(
                "Codex Handoff update available",
                f"A new Codex snapshot from {source} is ready to review.",
                QSystemTrayIcon.Information,
                8000,
            )
            self.last_notified_version = str(status["remote_head"])
        self.versions.clear()
        for version in versions:
            self.versions.addItem(f"{version.version_id} | {version.source_device} | {version.created_at}")
        self.statusBar().showMessage("Ready")

    def _confirm_run(self, question: str, operation) -> None:
        if QMessageBox.question(self, "Confirm", question) == QMessageBox.Yes:
            self._run_when_codex_stopped(operation, lambda _: self.refresh())

    def _baseline(self):
        assert self.service
        return self.service.create_baseline()

    def _push(self):
        assert self.service
        return self.service.push()

    def _pull(self) -> None:
        if self.service is None:
            return
        self._run(self.service.preview_pull, self._confirm_pull)

    def _confirm_pull(self, preview: object) -> None:
        if preview is None:
            QMessageBox.information(self, "Codex Handoff", "No update is available.")
            return
        text = f"Apply {preview.version_id} from {preview.source_device}?\nAdded: {len(preview.added)}\nChanged: {len(preview.changed)}"
        if QMessageBox.question(self, "Apply update", text) == QMessageBox.Yes:
            assert self.service
            self._run_when_codex_stopped(self.service.pull, lambda _: self.refresh())

    def _restore(self) -> None:
        item = self.versions.currentItem()
        if item is None or self.service is None:
            QMessageBox.information(self, "Codex Handoff", "Select a version first.")
            return
        identifier = item.text().split(" | ", 1)[0]
        self._confirm_run(f"Restore {identifier}? A local backup will be created first.", lambda: self.service.restore(identifier))

    def _restore_baseline(self) -> None:
        if self.service is None:
            return
        baseline_id = self.baseline_label.text()
        if baseline_id == "Not created":
            baseline_id = ""
        if not baseline_id:
            QMessageBox.information(self, "Codex Handoff", "No protected baseline is available.")
            return
        self._confirm_run(
            f"Restore protected baseline {baseline_id}? A local backup will be created first.",
            lambda: self.service.restore(str(baseline_id)),
        )

    def _settings(self) -> None:
        dialog = SetupDialog(self.config_path)
        if dialog.exec() == QDialog.Accepted:
            self.config = load_config(self.config_path)
            self.service = None
            self._connect()


def launch_gui(config_path: Path | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Codex Handoff")
    path = config_path or default_config_path()
    if not path.is_file():
        dialog = SetupDialog(path)
        if dialog.exec() != QDialog.Accepted:
            return 1
    window = MainWindow(path)
    window.show()
    return app.exec()
