from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QSignalSpy

from codex_handoff.models import RemoteHead
from codex_handoff.monitor import PollSchedule, RemoteHeadMonitor


def test_poll_schedule_backs_off_and_success_resets() -> None:
    schedule = PollSchedule(normal_seconds=60)

    assert schedule.failure() == 120
    assert schedule.failure() == 300
    assert schedule.failure() == 900
    assert schedule.failure() == 900
    assert schedule.success() == 60
    assert schedule.failure() == 120


def test_poll_schedule_rejects_aggressive_interval() -> None:
    try:
        PollSchedule(normal_seconds=10)
    except ValueError as exc:
        assert "30" in str(exc)
    else:
        raise AssertionError("Expected a minimum interval error")


def test_monitor_emits_each_head_change_once() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    monitor = RemoteHeadMonitor(lambda: None)
    changes = QSignalSpy(monitor.head_changed)
    first = RemoteHead("v1", None, "mac", "now", "macos")

    monitor._completed(first)
    monitor._completed(first)

    monitor.stop()
    assert changes.count() == 1
    assert app is not None


def test_monitor_emits_recovery_after_offline_state() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    monitor = RemoteHeadMonitor(lambda: None)
    offline = QSignalSpy(monitor.offline)
    recovered = QSignalSpy(monitor.recovered)

    monitor._failed("network unavailable")
    monitor._completed(None)

    monitor.stop()
    assert offline.count() == 1
    assert recovered.count() == 1
    assert app is not None
