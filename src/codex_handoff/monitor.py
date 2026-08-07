from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot

from .models import RemoteHead


class PollSchedule:
    def __init__(self, normal_seconds: int = 60) -> None:
        if normal_seconds < 30:
            raise ValueError("Polling interval must be at least 30 seconds")
        self.normal_seconds = normal_seconds
        self._failures = 0

    def success(self) -> int:
        self._failures = 0
        return self.normal_seconds

    def failure(self) -> int:
        delays = (120, 300, 900)
        delay = delays[min(self._failures, len(delays) - 1)]
        self._failures += 1
        return delay


class _HeadSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)


class _HeadWorker(QRunnable):
    def __init__(self, read_head: Callable[[], RemoteHead | None]) -> None:
        super().__init__()
        self.read_head = read_head
        self.signals = _HeadSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.completed.emit(self.read_head())
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class RemoteHeadMonitor(QObject):
    checked = Signal(object)
    head_changed = Signal(object)
    offline = Signal(str)
    recovered = Signal()

    def __init__(
        self,
        read_head: Callable[[], RemoteHead | None],
        *,
        interval_seconds: int = 60,
        pool: QThreadPool | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.read_head = read_head
        self.schedule = PollSchedule(interval_seconds)
        self.pool = pool or QThreadPool.globalInstance()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.check_now)
        self.paused = False
        self.running = False
        self.was_offline = False
        self.last_version_id: str | None = None
        self._worker: _HeadWorker | None = None

    def start(self, *, immediate: bool = True) -> None:
        self._schedule(0 if immediate else self.schedule.normal_seconds)

    def stop(self) -> None:
        self.timer.stop()

    def pause(self) -> None:
        self.paused = True
        self.timer.stop()

    def resume(self, *, immediate: bool = True) -> None:
        self.paused = False
        self._schedule(0 if immediate else self.schedule.normal_seconds)

    @Slot()
    def check_now(self) -> None:
        if self.paused or self.running:
            return
        self.running = True
        worker = _HeadWorker(self.read_head)
        self._worker = worker
        worker.signals.completed.connect(self._completed)
        worker.signals.failed.connect(self._failed)
        self.pool.start(worker)

    @Slot(object)
    def _completed(self, value: object) -> None:
        self.running = False
        self._worker = None
        head = value if isinstance(value, RemoteHead) else None
        if self.was_offline:
            self.was_offline = False
            self.recovered.emit()
        self.checked.emit(head)
        version_id = head.version_id if head else None
        if version_id and version_id != self.last_version_id:
            self.head_changed.emit(head)
        self.last_version_id = version_id
        self._schedule(self.schedule.success())

    @Slot(str)
    def _failed(self, message: str) -> None:
        self.running = False
        self._worker = None
        self.was_offline = True
        self.offline.emit(message)
        self._schedule(self.schedule.failure())

    def _schedule(self, seconds: int) -> None:
        if not self.paused:
            self.timer.start(max(0, seconds * 1000))
