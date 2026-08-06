from __future__ import annotations

from pathlib import Path
import socket
import sys

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
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
    QVBoxLayout,
    QWidget,
)

from ..config import AppConfig, default_config_path, default_workspace, load_config, save_config, validate_config
from ..crypto import generate_recovery_key
from ..service import HandoffService, create_provider


class SetupDialog(QDialog):
    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.config_path = config_path
        self.setWindowTitle("Codex Handoff Setup")
        self.setMinimumWidth(620)
        form = QFormLayout()
        self.device = QLineEdit(socket.gethostname())
        self.source = QLineEdit(str(Path.home() / ".codex"))
        self.workspace = QLineEdit(str(default_workspace()))
        self.provider = QComboBox()
        self.provider.addItem("Local folder", "local")
        self.provider.addItem("Google Drive", "google_drive")
        self.storage = QLineEdit(str(Path.home() / "CodexHandoffStorage"))
        self.secrets = QLineEdit()
        self.recovery_key = QLineEdit(str(default_workspace() / "recovery.key"))
        form.addRow("Device name", self.device)
        form.addRow("Codex state", self._path_row(self.source, False))
        form.addRow("Local workspace", self._path_row(self.workspace, False))
        form.addRow("Cloud provider", self.provider)
        form.addRow("Local provider folder", self._path_row(self.storage, False))
        form.addRow("Google OAuth JSON", self._path_row(self.secrets, True))
        form.addRow("Recovery key", self._recovery_key_row())
        note = QLabel(
            "Google Drive opens a browser for OAuth. The OAuth JSON and token remain on this device. "
            "Codex must be closed for baseline, push, pull, and restore."
        )
        note.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def _path_row(self, field: QLineEdit, file_mode: bool) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        button = QPushButton("Browse")
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
            local_storage_dir=Path(self.storage.text()).expanduser() if self.storage.text().strip() else None,
            google_client_secrets=Path(self.secrets.text()).expanduser() if self.secrets.text().strip() else None,
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
        self.setWindowTitle("Codex Handoff")
        self.resize(820, 560)
        self.device_label = QLabel()
        self.codex_label = QLabel()
        self.baseline_label = QLabel()
        self.local_label = QLabel()
        self.remote_label = QLabel()
        self.update_label = QLabel()
        self.versions = QListWidget()
        self.baseline_button = QPushButton("Create protected baseline")
        self.push_button = QPushButton("Send this device state")
        self.pull_button = QPushButton("Receive available update")
        self.restore_button = QPushButton("Restore selected version")
        self.restore_baseline_button = QPushButton("Restore protected baseline")
        self.refresh_button = QPushButton("Refresh")
        self.baseline_button.clicked.connect(lambda: self._confirm_run("Create the immutable parent baseline?", self._baseline))
        self.push_button.clicked.connect(lambda: self._confirm_run("Publish this device state? Codex must be closed.", self._push))
        self.pull_button.clicked.connect(self._pull)
        self.restore_button.clicked.connect(self._restore)
        self.restore_baseline_button.clicked.connect(self._restore_baseline)
        self.refresh_button.clicked.connect(self.refresh)
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
        container = QWidget()
        container.setLayout(body)
        self.setCentralWidget(container)
        self.setStatusBar(QStatusBar())
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
        worker.signals.completed.connect(lambda value: self._done(value, completed))
        worker.signals.failed.connect(self._failed)
        self.pool.start(worker)

    def _done(self, value: object, callback) -> None:
        self._set_busy(False)
        if callback:
            callback(value)
        else:
            self.refresh()

    def _failed(self, message: str) -> None:
        self._set_busy(False)
        self.statusBar().showMessage("Operation failed")
        QMessageBox.critical(self, "Codex Handoff", message)

    def _set_busy(self, busy: bool) -> None:
        for button in (self.baseline_button, self.push_button, self.pull_button, self.restore_button, self.restore_baseline_button, self.refresh_button):
            button.setEnabled(not busy)

    def refresh(self) -> None:
        if self.service is None:
            return
        self.statusBar().showMessage("Refreshing...")
        self._run(lambda: (self.service.status(), self.service.list_versions()), self._show_status)

    def _show_status(self, result: object) -> None:
        status, versions = result  # type: ignore[misc]
        self.device_label.setText(str(status["device_id"]))
        self.codex_label.setText("Running - close it before operations" if status["codex_running"] else "Closed")
        self.baseline_label.setText(str(status["baseline_id"] or "Not created"))
        self.local_label.setText(str(status["last_applied_version"] or "None"))
        self.remote_label.setText(str(status["remote_head"] or "None"))
        self.update_label.setText("Available" if status["update_available"] else "Up to date")
        self.versions.clear()
        for version in versions:
            self.versions.addItem(f"{version.version_id} | {version.source_device} | {version.created_at}")
        self.statusBar().showMessage("Ready")

    def _confirm_run(self, question: str, operation) -> None:
        if QMessageBox.question(self, "Confirm", question) == QMessageBox.Yes:
            self._run(operation, lambda _: self.refresh())

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
            self._run(self.service.pull, lambda _: self.refresh())

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
        baseline_id = self.service.status().get("baseline_id")
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
