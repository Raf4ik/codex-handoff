from __future__ import annotations

from enum import Enum

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models import RemoteHead


def _refresh_style(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class StatusTone(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    NEUTRAL = "neutral"


class StatusBlock(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("card", True)
        self.setProperty("tone", StatusTone.NEUTRAL.value)
        self.setMinimumHeight(76)
        self.title_label = QLabel(title)
        self.title_label.setProperty("role", "subtitle")
        self.value_label = QLabel("Checking...")
        self.value_label.setStyleSheet("font-weight: 700;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_state(self, value: str, tone: StatusTone) -> None:
        self.value_label.setText(value)
        self.setProperty("tone", tone.value)
        _refresh_style(self)


class ActionButton(QPushButton):
    def __init__(self, text: str, *, tone: str = "default", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("tone", tone)
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class NavigationButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setProperty("nav", True)
        self.setFixedHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class _Endpoint(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setProperty("card", True)
        self.setMinimumHeight(72)
        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("font-weight: 700;")
        self.detail = QLabel("-")
        self.detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail.setProperty("role", "subtitle")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(3)
        layout.addWidget(self.title)
        layout.addWidget(self.detail)


class SyncRoute(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.local = _Endpoint("This device")
        self.cloud = _Endpoint("Storage")
        self.remote = _Endpoint("Other device")
        self.local_title = self.local.title
        self.local_detail = self.local.detail
        self.remote_detail = self.remote.detail
        first_arrow = QLabel("->")
        second_arrow = QLabel("->")
        for arrow in (first_arrow, second_arrow):
            arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
            arrow.setStyleSheet("color: #19988D; font-size: 20px; font-weight: 700;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self.local, 1)
        layout.addWidget(first_arrow)
        layout.addWidget(self.cloud, 1)
        layout.addWidget(second_arrow)
        layout.addWidget(self.remote, 1)

    def set_route(
        self,
        local_label: str,
        local_device: str,
        provider: str,
        remote_device: str | None,
        remote_platform: str | None,
    ) -> None:
        self.local.title.setText(local_label)
        self.local.detail.setText(local_device)
        self.cloud.title.setText(provider)
        self.cloud.detail.setText("Encrypted versions")
        remote_names = {"windows": "Windows PC", "macos": "Mac"}
        self.remote.title.setText(remote_names.get(remote_platform or "", "Other device"))
        self.remote.detail.setText(remote_device or "Not connected")


class VersionTable(QTableWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, 4, parent)
        self.setHorizontalHeaderLabels(("VERSION", "SOURCE", "PLATFORM", "CREATED"))
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)

    def set_versions(self, versions: list[RemoteHead]) -> None:
        self.setRowCount(len(versions))
        platform_names = {"windows": "Windows", "macos": "macOS"}
        for row, version in enumerate(versions):
            values = (
                version.version_id,
                version.source_device,
                platform_names.get(version.source_platform or "", "Unknown"),
                version.created_at,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, version.version_id)
                self.setItem(row, column, item)
        self.resizeColumnsToContents()

    def selected_version_id(self) -> str | None:
        row = self.currentRow()
        item = self.item(row, 0) if row >= 0 else None
        return str(item.data(Qt.ItemDataRole.UserRole)) if item else None


class OperationBanner(QFrame):
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("card", True)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.cancel_button = ActionButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_requested)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.addWidget(self.message, 1)
        layout.addWidget(self.cancel_button)
        self.hide()

    def show_message(self, message: str, tone: StatusTone, *, cancellable: bool = False) -> None:
        self.message.setText(message)
        self.setProperty("tone", tone.value)
        self.cancel_button.setVisible(cancellable)
        _refresh_style(self)
        self.show()
