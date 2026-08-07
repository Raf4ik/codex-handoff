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
from .i18n import LANGUAGE_NAMES, normalize_language, text
from .platform import application_path, create_desktop_shortcut, current_platform, set_autostart
from .theme import load_app_icon
from .widgets import ActionButton


class DevicePage(QWidget):
    def __init__(self, existing: AppConfig | None, language: str) -> None:
        super().__init__()
        self.info = current_platform()
        self.device = QLineEdit(existing.device_id if existing else socket.gethostname())
        self.source = QLineEdit(str(existing.source_dir if existing else self.info.codex_dir))
        self.workspace = QLineEdit(str(existing.workspace_dir if existing else default_workspace()))
        self.language = QComboBox()
        for code, name in LANGUAGE_NAMES.items():
            self.language.addItem(name, code)
        self.language.setCurrentIndex(max(0, self.language.findData(language)))
        self.advanced = QWidget()
        advanced_form = QFormLayout(self.advanced)
        advanced_form.setContentsMargins(0, 8, 0, 0)
        self.workspace_row = _PathRow(self.workspace, directory=True, language=language)
        self.workspace_label = QLabel()
        advanced_form.addRow(self.workspace_label, self.workspace_row)
        self.advanced_form = advanced_form
        self.advanced.hide()
        self.advanced_button = QPushButton()
        self.advanced_button.setCheckable(True)
        self.advanced_button.toggled.connect(self.advanced.setVisible)
        self.form = QFormLayout()
        self.form.setSpacing(14)
        self.source_row = _PathRow(self.source, directory=True, language=language)
        self.language_label = QLabel()
        self.device_label = QLabel()
        self.source_label = QLabel()
        self.form.addRow(self.language_label, self.language)
        self.form.addRow(self.device_label, self.device)
        self.form.addRow(self.source_label, self.source_row)
        body, self.eyebrow, self.title, self.subtitle = _page_body()
        self.platform_badge = QLabel()
        self.platform_badge.setObjectName("platformBadge")
        body.addWidget(self.platform_badge)
        body.addSpacing(8)
        body.addLayout(self.form)
        body.addWidget(self.advanced_button)
        body.addWidget(self.advanced)
        body.addStretch()
        self.setLayout(body)
        self.retranslate(language)

    def retranslate(self, language: str) -> None:
        local_label = text(language, {"windows": "this_pc", "macos": "this_mac"}.get(self.info.key, "this_generic_device"))
        self.eyebrow.setText(text(language, "this_device"))
        self.title.setText(text(language, "setup_device", local_label=local_label))
        self.subtitle.setText(text(language, "platform_detected", platform=self.info.display_name))
        self.platform_badge.setText(text(language, "detected_badge", platform=self.info.display_name))
        self.language_label.setText(text(language, "language"))
        self.device_label.setText(text(language, "device_name"))
        self.source_label.setText(text(language, "codex_data"))
        self.workspace_label.setText(text(language, "local_workspace"))
        self.advanced_button.setText(text(language, "advanced_paths"))
        self.source_row.retranslate(language)
        self.workspace_row.retranslate(language)


class StoragePage(QWidget):
    def __init__(self, existing: AppConfig | None, language: str) -> None:
        super().__init__()
        self.provider = QComboBox()
        self.provider.addItem("Google Drive", "google_drive")
        self.provider.addItem(text(language, "local_folder"), "local")
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
        self.storage_row = _PathRow(self.storage, directory=True, language=language)
        self.secrets_row = _PathRow(self.secrets, file_filter="JSON (*.json)", language=language)
        self.local_folder_row = self.storage_row
        self.oauth_row = self.secrets_row
        self.form = QFormLayout()
        self.form.setSpacing(14)
        self.provider_label = QLabel()
        self.secrets_label = QLabel()
        self.storage_label = QLabel()
        self.form.addRow(self.provider_label, self.provider)
        self.form.addRow(self.secrets_label, self.secrets_row)
        self.form.addRow(self.storage_label, self.storage_row)
        body, self.eyebrow, self.title, self.subtitle = _page_body()
        body.addLayout(self.form)
        body.addStretch()
        self.setLayout(body)
        self.provider.currentIndexChanged.connect(self._update_fields)
        self.retranslate(language)
        self._update_fields()

    def retranslate(self, language: str) -> None:
        _set_combo_items(
            self.provider,
            (("Google Drive", "google_drive"), (text(language, "local_folder"), "local")),
        )
        self.eyebrow.setText(text(language, "storage"))
        self.title.setText(text(language, "choose_storage"))
        self.subtitle.setText(text(language, "storage_subtitle"))
        self.provider_label.setText(text(language, "storage_provider"))
        self.secrets_label.setText(text(language, "google_oauth_json"))
        self.storage_label.setText(text(language, "local_provider_folder"))
        self.secrets_row.retranslate(language)
        self.storage_row.retranslate(language)
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
    def __init__(self, existing: AppConfig | None, language: str) -> None:
        super().__init__()
        self.recovery_key = QLineEdit(
            str(existing.encryption_key_file)
            if existing and existing.encryption_key_file
            else str(default_workspace() / "recovery.key")
        )
        self.select_button = ActionButton("")
        self.create_button = ActionButton("", tone="primary")
        self.select_button.clicked.connect(self._select)
        self.create_button.clicked.connect(self._create)
        actions = QHBoxLayout()
        actions.addWidget(self.select_button)
        actions.addWidget(self.create_button)
        body, self.eyebrow, self.title, self.subtitle = _page_body()
        self.form = QFormLayout()
        self.recovery_key_label = QLabel()
        self.form.addRow(self.recovery_key_label, self.recovery_key)
        body.addLayout(self.form)
        body.addLayout(actions)
        self.warning = QLabel()
        self.warning.setWordWrap(True)
        self.warning.setObjectName("warningNote")
        body.addWidget(self.warning)
        body.addStretch()
        self.setLayout(body)
        self.language = language
        self.retranslate(language)

    def retranslate(self, language: str) -> None:
        self.language = language
        self.eyebrow.setText(text(language, "recovery_key_eyebrow"))
        self.title.setText(text(language, "protect_versions"))
        self.subtitle.setText(text(language, "recovery_subtitle"))
        self.recovery_key_label.setText(text(language, "recovery_key"))
        self.select_button.setText(text(language, "select_existing"))
        self.create_button.setText(text(language, "create_new"))
        self.warning.setText(text(language, "recovery_warning"))

    def _select(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            text(self.language, "select_recovery_key"),
            filter=text(self.language, "key_files"),
        )
        if selected:
            self.recovery_key.setText(selected)

    def _create(self) -> None:
        selected, _ = QFileDialog.getSaveFileName(
            self,
            text(self.language, "create_recovery_key"),
            self.recovery_key.text(),
            text(self.language, "key_files"),
        )
        if not selected:
            return
        try:
            generate_recovery_key(Path(selected))
        except Exception as exc:
            QMessageBox.critical(self, "Codex Handoff", str(exc))
            return
        self.recovery_key.setText(selected)


class PairingPage(QWidget):
    def __init__(self, existing: AppConfig | None, language: str) -> None:
        super().__init__()
        self.mode = QComboBox()
        self.mode.addItem("", "create_pair")
        self.mode.addItem("", "join_pair")
        if existing:
            index = self.mode.findData(existing.pair_mode)
            if index >= 0:
                self.mode.setCurrentIndex(index)
        self.explanation = QLabel()
        self.explanation.setWordWrap(True)
        self.explanation.setObjectName("reviewSummary")
        self.mode.currentIndexChanged.connect(self._update_explanation)
        body, self.eyebrow, self.title, self.subtitle = _page_body()
        self.form = QFormLayout()
        self.mode_label = QLabel()
        self.form.addRow(self.mode_label, self.mode)
        body.addLayout(self.form)
        body.addSpacing(12)
        body.addWidget(self.explanation)
        body.addStretch()
        self.setLayout(body)
        self.language = language
        self.retranslate(language)
        self._update_explanation()

    def retranslate(self, language: str) -> None:
        self.language = language
        _set_combo_items(
            self.mode,
            ((text(language, "pair_create"), "create_pair"), (text(language, "pair_join"), "join_pair")),
        )
        self.eyebrow.setText(text(language, "pairing"))
        self.title.setText(text(language, "connect_two_computers"))
        self.subtitle.setText(text(language, "pairing_subtitle"))
        self.mode_label.setText(text(language, "pairing_mode"))
        self._update_explanation()

    def _update_explanation(self) -> None:
        if self.mode.currentData() == "join_pair":
            self.explanation.setText(text(self.language, "pair_join_explanation"))
        else:
            self.explanation.setText(text(self.language, "pair_create_explanation"))


class ReviewPage(QWidget):
    def __init__(self, existing: AppConfig | None, language: str) -> None:
        super().__init__()
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setObjectName("reviewSummary")
        self.autostart = QCheckBox()
        self.autostart.setChecked(existing.autostart_enabled if existing else True)
        self.desktop_shortcut = QCheckBox()
        self.desktop_shortcut.setChecked(True)
        body, self.eyebrow, self.title, self.subtitle = _page_body()
        body.addWidget(self.summary)
        body.addSpacing(12)
        body.addWidget(self.autostart)
        body.addWidget(self.desktop_shortcut)
        body.addStretch()
        self.setLayout(body)
        self.retranslate(language)

    def retranslate(self, language: str) -> None:
        self.eyebrow.setText(text(language, "review"))
        self.title.setText(text(language, "ready_to_connect"))
        self.subtitle.setText(text(language, "review_subtitle"))
        self.autostart.setText(text(language, "start_with_os"))
        self.desktop_shortcut.setText(text(language, "create_desktop_shortcut"))


class SetupWizard(QDialog):
    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.config_path = config_path
        self.existing = load_config(config_path) if config_path.is_file() else None
        self.language_code = normalize_language(self.existing.language if self.existing else None)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)
        self.setMinimumSize(840, 560)
        self.resize(900, 600)
        self.device_page = DevicePage(self.existing, self.language_code)
        self.storage_page = StoragePage(self.existing, self.language_code)
        self.pairing_page = PairingPage(self.existing, self.language_code)
        self.recovery_page = RecoveryPage(self.existing, self.language_code)
        self.review_page = ReviewPage(self.existing, self.language_code)
        self.pages = QStackedWidget()
        for page in (self.device_page, self.storage_page, self.pairing_page, self.recovery_page, self.review_page):
            self.pages.addWidget(page)
        self.step_labels: list[QLabel] = []
        rail = self._build_rail()
        self.back_button = ActionButton("")
        self.continue_button = ActionButton("", tone="primary")
        self.cancel_button = ActionButton("")
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
        self.device_page.language.currentIndexChanged.connect(self._language_changed)
        self.retranslate()
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
        for number in range(1, 6):
            label = QLabel(f"  {number}")
            label.setFixedHeight(42)
            label.setProperty("step", "pending")
            self.step_labels.append(label)
            layout.addWidget(label)
        layout.addStretch()
        self.privacy = QLabel()
        self.privacy.setObjectName("setupPrivacy")
        layout.addWidget(self.privacy)
        return rail

    def _bind_compatibility_fields(self) -> None:
        self.device = self.device_page.device
        self.language = self.device_page.language
        self.source = self.device_page.source
        self.workspace = self.device_page.workspace
        self.provider = self.storage_page.provider
        self.storage = self.storage_page.storage
        self.secrets = self.storage_page.secrets
        self.pair_mode = self.pairing_page.mode
        self.recovery_key = self.recovery_page.recovery_key
        self.storage_row = self.storage_page.storage_row
        self.secrets_row = self.storage_page.secrets_row

    def _language_changed(self) -> None:
        self.language_code = normalize_language(str(self.language.currentData()))
        self.retranslate()

    def retranslate(self) -> None:
        language = self.language_code
        self.setWindowTitle(text(language, "setup_window_title"))
        self.device_page.retranslate(language)
        self.storage_page.retranslate(language)
        self.pairing_page.retranslate(language)
        self.recovery_page.retranslate(language)
        self.review_page.retranslate(language)
        step_keys = ("rail_this_device", "rail_storage", "rail_pairing", "rail_recovery_key", "rail_review")
        for number, (label, key) in enumerate(zip(self.step_labels, step_keys), start=1):
            label.setText(f"  {number}    {text(language, key)}")
        self.privacy.setText(text(language, "privacy_note"))
        self.back_button.setText(text(language, "back"))
        self.cancel_button.setText(text(language, "cancel"))
        self._show_step(self.current_step)

    def _show_step(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for position, label in enumerate(self.step_labels):
            label.setProperty("step", "active" if position == index else "done" if position < index else "pending")
            label.style().unpolish(label)
            label.style().polish(label)
        self.back_button.setVisible(index > 0)
        self.continue_button.setText(
            text(self.language_code, "finish_setup" if index == 4 else "continue")
        )
        if index == 4:
            self._update_review()

    def _back(self) -> None:
        self._show_step(max(0, self.current_step - 1))

    def _next(self) -> None:
        error = self._current_step_error()
        if error:
            QMessageBox.warning(self, text(self.language_code, "check_step"), error)
            return
        if self.current_step < 4:
            self._show_step(self.current_step + 1)
        else:
            self._finish()

    def _current_step_error(self) -> str | None:
        if self.current_step == 0:
            if not self.device.text().strip():
                return text(self.language_code, "device_required")
            if not Path(self.source.text()).expanduser().is_dir():
                return text(self.language_code, "codex_dir_missing")
        elif self.current_step == 1:
            if self.provider.currentData() == "google_drive" and not Path(self.secrets.text()).expanduser().is_file():
                return text(self.language_code, "select_oauth")
            if self.provider.currentData() == "local" and not self.storage.text().strip():
                return text(self.language_code, "select_local_folder")
        elif self.current_step == 3 and not Path(self.recovery_key.text()).expanduser().is_file():
            return text(self.language_code, "select_or_create_key")
        return None

    def _config(self) -> AppConfig:
        return AppConfig(
            device_id=self.device.text().strip(),
            source_dir=Path(self.source.text()).expanduser(),
            workspace_dir=Path(self.workspace.text()).expanduser(),
            language=self.language_code,
            pair_mode=str(self.pair_mode.currentData()),
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
        provider = "Google Drive" if self.provider.currentData() == "google_drive" else text(self.language_code, "local_folder")
        pairing = text(
            self.language_code,
            "join_existing_pair" if self.pair_mode.currentData() == "join_pair" else "create_new_pair",
        )
        self.review_page.summary.setText(
            "\n".join(
                (
                    text(self.language_code, "review_device", value=self.device.text()),
                    text(self.language_code, "review_pairing", value=pairing),
                    text(self.language_code, "review_codex_data", value=self.source.text()),
                    text(self.language_code, "review_storage", value=provider),
                    text(self.language_code, "review_recovery_key", value=self.recovery_key.text()),
                )
            )
        )

    def _finish(self) -> None:
        config = self._config()
        try:
            validate_config(config)
            save_config(config, self.config_path)
        except Exception as exc:
            QMessageBox.critical(self, text(self.language_code, "invalid_setup"), str(exc))
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
            QMessageBox.warning(self, text(self.language_code, "system_integration"), "\n".join(warnings))
        self.accept()


SetupDialog = SetupWizard


def _page_body() -> tuple[QVBoxLayout, QLabel, QLabel, QLabel]:
    layout = QVBoxLayout()
    layout.setContentsMargins(38, 34, 38, 18)
    layout.setSpacing(10)
    eyebrow_label = QLabel()
    eyebrow_label.setObjectName("eyebrow")
    title_label = QLabel()
    title_label.setProperty("role", "heading")
    subtitle_label = QLabel()
    subtitle_label.setProperty("role", "subtitle")
    subtitle_label.setWordWrap(True)
    layout.addWidget(eyebrow_label)
    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    layout.addSpacing(12)
    return layout, eyebrow_label, title_label, subtitle_label


class _PathRow(QWidget):
    def __init__(
        self,
        field: QLineEdit,
        *,
        directory: bool = False,
        file_filter: str = "",
        language: str = "en",
    ) -> None:
        super().__init__()
        self.field = field
        self.directory = directory
        self.file_filter = file_filter
        self.language = language
        self.browse = QPushButton()
        self.browse.clicked.connect(self._select_path)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(field, 1)
        layout.addWidget(self.browse)
        self.retranslate(language)

    def retranslate(self, language: str) -> None:
        self.language = language
        self.browse.setText(text(language, "browse"))

    def _select_path(self) -> None:
        if self.directory:
            selected = QFileDialog.getExistingDirectory(self, text(self.language, "select_directory"))
        else:
            selected, _ = QFileDialog.getOpenFileName(
                self,
                text(self.language, "select_file"),
                filter=self.file_filter,
            )
        if selected:
            self.field.setText(selected)


def _set_combo_items(combo: QComboBox, items: tuple[tuple[str, str], ...]) -> None:
    current = combo.currentData()
    combo.blockSignals(True)
    combo.clear()
    for label, value in items:
        combo.addItem(label, value)
    index = combo.findData(current)
    combo.setCurrentIndex(max(0, index))
    combo.blockSignals(False)
