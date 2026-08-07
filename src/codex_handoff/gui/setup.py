from __future__ import annotations

from pathlib import Path
import socket

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import AppConfig, default_workspace, load_config, save_config, validate_config
from ..crypto import generate_recovery_key
from .platform import application_path, create_desktop_shortcut, current_platform, set_autostart
from .theme import load_app_icon
from .widgets import ActionButton


class DevicePage(QWidget):
    def __init__(self, existing: AppConfig | None) -> None:
        super().__init__()
        info = current_platform()
        self.device = QLineEdit(existing.device_id if existing else socket.gethostname())
        self.source = QLineEdit(str(existing.source_dir if existing else info.codex_dir))
        self.workspace = QLineEdit(str(existing.workspace_dir if existing else default_workspace()))
        self.advanced = QWidget()
        advanced_form = QFormLayout(self.advanced)
        advanced_form.setContentsMargins(0, 8, 0, 0)
        advanced_form.addRow("Local workspace", _path_row(self.workspace, directory=True))
        self.advanced.hide()
        advanced_button = QPushButton("Advanced paths")
        advanced_button.setCheckable(True)
        advanced_button.toggled.connect(self.advanced.setVisible)
        form = QFormLayout()
        form.setSpacing(14)
        form.addRow("Device name", self.device)
        form.addRow("Codex data", _path_row(self.source, directory=True))
        body = _page_body(
            "THIS DEVICE",
            f"Set up {info.local_label}",
            f"{info.display_name} detected. Confirm the Codex data directory.",
        )
        platform_badge = QLabel(f"{info.display_name}  |  DETECTED")
        platform_badge.setObjectName("platformBadge")
        body.addWidget(platform_badge)
        body.addSpacing(8)
        body.addLayout(form)
        body.addWidget(advanced_button)
        body.addWidget(self.advanced)
        body.addStretch()
        self.setLayout(body)


class StoragePage(QWidget):
    def __init__(self, existing: AppConfig | None) -> None:
        super().__init__()
        self.provider = QComboBox()
        self.provider.addItem("Google Drive", "google_drive")
        self.provider.addItem("Local folder", "local")
        if existing:
            self.provider.setCurrentIndex(max(0, self.provider.findData(existing.provider)))
        self.storage = QLineEdit(
            str(existing.local_storage_dir)
            if existing and existing.local_storage_dir
            else str(Path.home() / "CodexHandoffStorage")
        )
        self.secrets = QLineEdit(
            str(existing.google_client_secrets) if existing and existing.google_client_secrets else ""
        )
        self.storage_row = _path_row(self.storage, directory=True)
        self.secrets_row = _path_row(self.secrets, file_filter="JSON (*.json)")
        self.local_folder_row = self.storage_row
        self.oauth_row = self.secrets_row
        self.form = QFormLayout()
        self.form.setSpacing(14)
        self.form.addRow("Storage provider", self.provider)
        self.form.addRow("Google OAuth JSON", self.secrets_row)
        self.form.addRow("Local provider folder", self.storage_row)
        body = _page_body(
            "STORAGE",
            "Choose storage",
            "Encrypted versions are stored in an account or folder you control.",
        )
        body.addLayout(self.form)
        body.addStretch()
        self.setLayout(body)
        self.provider.currentIndexChanged.connect(self._update_fields)
        self._update_fields()

    def _update_fields(self) -> None:
        google = self.provider.currentData() == "google_drive"
        self.secrets_row.setVisible(google)
        self.secrets_row.setEnabled(google)
        self.storage_row.setVisible(not google)
        self.storage_row.setEnabled(not google)
        label = self.form.labelForField(self.secrets_row)
        if label:
            label.setVisible(google)
        label = self.form.labelForField(self.storage_row)
        if label:
            label.setVisible(not google)


class RecoveryPage(QWidget):
    def __init__(self, existing: AppConfig | None) -> None:
        super().__init__()
        self.recovery_key = QLineEdit(
            str(existing.encryption_key_file)
            if existing and existing.encryption_key_file
            else str(default_workspace() / "recovery.key")
        )
        select = ActionButton("Select existing")
        create = ActionButton("Create new", tone="primary")
        select.clicked.connect(self._select)
        create.clicked.connect(self._create)
        actions = QHBoxLayout()
        actions.addWidget(select)
        actions.addWidget(create)
        body = _page_body(
            "RECOVERY KEY",
            "Protect synchronized versions",
            "Use the same key on every device. The key is never uploaded.",
        )
        form = QFormLayout()
        form.addRow("Recovery key", self.recovery_key)
        body.addLayout(form)
        body.addLayout(actions)
        warning = QLabel("Keep an offline copy. Lost recovery keys cannot be restored.")
        warning.setWordWrap(True)
        warning.setObjectName("warningNote")
        body.addWidget(warning)
        body.addStretch()
        self.setLayout(body)

    def _select(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Select recovery key", filter="Key files (*.key)")
        if selected:
            self.recovery_key.setText(selected)

    def _create(self) -> None:
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


class ReviewPage(QWidget):
    def __init__(self, existing: AppConfig | None) -> None:
        super().__init__()
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setObjectName("reviewSummary")
        self.autostart = QCheckBox("Start with the operating system")
        self.autostart.setChecked(existing.autostart_enabled if existing else True)
        self.desktop_shortcut = QCheckBox("Create a desktop shortcut")
        self.desktop_shortcut.setChecked(True)
        body = _page_body(
            "REVIEW",
            "Ready to connect",
            "Confirm these settings before opening the synchronization dashboard.",
        )
        body.addWidget(self.summary)
        body.addSpacing(12)
        body.addWidget(self.autostart)
        body.addWidget(self.desktop_shortcut)
        body.addStretch()
        self.setLayout(body)


class SetupWizard(QDialog):
    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.config_path = config_path
        self.existing = load_config(config_path) if config_path.is_file() else None
        self.setWindowTitle("Codex Handoff Setup")
        self.setMinimumSize(840, 560)
        self.resize(900, 600)
        self.device_page = DevicePage(self.existing)
        self.storage_page = StoragePage(self.existing)
        self.recovery_page = RecoveryPage(self.existing)
        self.review_page = ReviewPage(self.existing)
        self.pages = QStackedWidget()
        for page in (self.device_page, self.storage_page, self.recovery_page, self.review_page):
            self.pages.addWidget(page)
        self.step_labels: list[QLabel] = []
        rail = self._build_rail()
        self.back_button = ActionButton("Back")
        self.continue_button = ActionButton("Continue", tone="primary")
        self.cancel_button = ActionButton("Cancel")
        self.back_button.clicked.connect(self._back)
        self.continue_button.clicked.connect(self._next)
        self.cancel_button.clicked.connect(self.reject)
        footer = QHBoxLayout()
        footer.setContentsMargins(24, 12, 24, 16)
        footer.addWidget(self.cancel_button)
        footer.addStretch()
        footer.addWidget(self.back_button)
        footer.addWidget(self.continue_button)
        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.addWidget(self.pages, 1)
        content.addLayout(footer)
        panel = QWidget()
        panel.setLayout(content)
        shell = QHBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(rail)
        shell.addWidget(panel, 1)
        self._bind_compatibility_fields()
        self._show_step(0)

    @property
    def current_step(self) -> int:
        return self.pages.currentIndex()

    def _build_rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("setupRail")
        rail.setFixedWidth(240)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(24, 28, 24, 24)
        brand_icon = QLabel()
        brand_icon.setPixmap(load_app_icon().pixmap(32, 32))
        brand = QLabel("Codex Handoff")
        brand.setObjectName("setupBrand")
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.addWidget(brand_icon)
        brand_row.addWidget(brand)
        brand_row.addStretch()
        layout.addLayout(brand_row)
        layout.addSpacing(36)
        for number, title in enumerate(("This device", "Storage", "Recovery key", "Review"), start=1):
            label = QLabel(f"  {number}    {title}")
            label.setFixedHeight(42)
            label.setProperty("step", "pending")
            self.step_labels.append(label)
            layout.addWidget(label)
        layout.addStretch()
        privacy = QLabel("Encrypted locally\nYour key stays on this device")
        privacy.setObjectName("setupPrivacy")
        layout.addWidget(privacy)
        return rail

    def _bind_compatibility_fields(self) -> None:
        self.device = self.device_page.device
        self.source = self.device_page.source
        self.workspace = self.device_page.workspace
        self.provider = self.storage_page.provider
        self.storage = self.storage_page.storage
        self.secrets = self.storage_page.secrets
        self.recovery_key = self.recovery_page.recovery_key
        self.storage_row = self.storage_page.storage_row
        self.secrets_row = self.storage_page.secrets_row

    def _show_step(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for position, label in enumerate(self.step_labels):
            label.setProperty("step", "active" if position == index else "done" if position < index else "pending")
            label.style().unpolish(label)
            label.style().polish(label)
        self.back_button.setVisible(index > 0)
        self.continue_button.setText("Finish setup" if index == 3 else "Continue")
        if index == 3:
            self._update_review()

    def _back(self) -> None:
        self._show_step(max(0, self.current_step - 1))

    def _next(self) -> None:
        error = self._current_step_error()
        if error:
            QMessageBox.warning(self, "Check this step", error)
            return
        if self.current_step < 3:
            self._show_step(self.current_step + 1)
        else:
            self._finish()

    def _current_step_error(self) -> str | None:
        if self.current_step == 0:
            if not self.device.text().strip():
                return "Device name is required."
            if not Path(self.source.text()).expanduser().is_dir():
                return "Codex data directory was not found."
        elif self.current_step == 1:
            if self.provider.currentData() == "google_drive" and not Path(self.secrets.text()).expanduser().is_file():
                return "Select the Google Desktop OAuth JSON file."
            if self.provider.currentData() == "local" and not self.storage.text().strip():
                return "Select a local provider folder."
        elif self.current_step == 2 and not Path(self.recovery_key.text()).expanduser().is_file():
            return "Create or select the recovery key."
        return None

    def _config(self) -> AppConfig:
        return AppConfig(
            device_id=self.device.text().strip(),
            source_dir=Path(self.source.text()).expanduser(),
            workspace_dir=Path(self.workspace.text()).expanduser(),
            provider=str(self.provider.currentData()),
            local_storage_dir=Path(self.storage.text()).expanduser() if self.provider.currentData() == "local" else None,
            google_client_secrets=Path(self.secrets.text()).expanduser() if self.provider.currentData() == "google_drive" else None,
            encryption_key_file=Path(self.recovery_key.text()).expanduser(),
            monitoring_enabled=self.existing.monitoring_enabled if self.existing else True,
            poll_interval_seconds=self.existing.poll_interval_seconds if self.existing else 60,
            autostart_enabled=self.review_page.autostart.isChecked(),
            minimize_to_tray=self.existing.minimize_to_tray if self.existing else True,
            close_notice_seen=self.existing.close_notice_seen if self.existing else False,
        )

    def _update_review(self) -> None:
        provider = "Google Drive" if self.provider.currentData() == "google_drive" else "Local folder"
        self.review_page.summary.setText(
            f"Device: {self.device.text()}\n"
            f"Codex data: {self.source.text()}\n"
            f"Storage: {provider}\n"
            f"Recovery key: {self.recovery_key.text()}"
        )

    def _finish(self) -> None:
        config = self._config()
        try:
            validate_config(config)
            save_config(config, self.config_path)
        except Exception as exc:
            QMessageBox.critical(self, "Invalid setup", str(exc))
            return
        warnings: list[str] = []
        executable = application_path()
        try:
            set_autostart(config.autostart_enabled, executable)
        except Exception as exc:
            warnings.append(str(exc))
        if self.review_page.desktop_shortcut.isChecked() and (
            executable.suffix.lower() in {".app", ".exe"}
        ):
            try:
                create_desktop_shortcut(executable)
            except Exception as exc:
                warnings.append(str(exc))
        if warnings:
            QMessageBox.warning(self, "System integration", "\n".join(warnings))
        self.accept()


SetupDialog = SetupWizard


def _page_body(eyebrow: str, title: str, subtitle: str) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setContentsMargins(38, 34, 38, 18)
    layout.setSpacing(10)
    eyebrow_label = QLabel(eyebrow)
    eyebrow_label.setObjectName("eyebrow")
    title_label = QLabel(title)
    title_label.setProperty("role", "heading")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setProperty("role", "subtitle")
    subtitle_label.setWordWrap(True)
    layout.addWidget(eyebrow_label)
    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    layout.addSpacing(12)
    return layout


def _path_row(field: QLineEdit, *, directory: bool = False, file_filter: str = "") -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    browse = QPushButton("Browse")

    def select_path() -> None:
        if directory:
            selected = QFileDialog.getExistingDirectory(widget, "Select directory")
        else:
            selected, _ = QFileDialog.getOpenFileName(widget, "Select file", filter=file_filter)
        if selected:
            field.setText(selected)

    browse.clicked.connect(select_path)
    layout.addWidget(field, 1)
    layout.addWidget(browse)
    return widget
