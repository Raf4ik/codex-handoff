from codex_handoff.gui import app


class VisibleFlag:
    def __init__(self) -> None:
        self.visible = False

    def setVisible(self, value: bool) -> None:
        self.visible = value


class Status:
    def __init__(self) -> None:
        self.message = ""

    def showMessage(self, message: str, *args) -> None:
        self.message = message


class WindowDouble:
    def __init__(self) -> None:
        self.pending_operation = None
        self.cancel_wait_button = VisibleFlag()
        self.status = Status()
        self.busy = False
        self.started = []

    def _set_busy(self, value: bool) -> None:
        self.busy = value

    def statusBar(self) -> Status:
        return self.status

    def _run(self, operation, completed) -> None:
        self.started.append((operation, completed))


def test_confirmed_operation_waits_for_codex_then_runs(monkeypatch) -> None:
    window = WindowDouble()
    operation = object()
    completed = object()
    running = iter((True, True, False))
    monkeypatch.setattr(app, "is_codex_running", lambda: next(running))
    monkeypatch.setattr(app.QMessageBox, "warning", lambda *args: None)

    app.MainWindow._run_when_codex_stopped(window, operation, completed)
    assert window.pending_operation == (operation, completed)
    assert window.cancel_wait_button.visible is True
    assert window.busy is True

    app.MainWindow._try_pending_operation(window)
    assert window.started == []
    app.MainWindow._try_pending_operation(window)
    assert window.started == [(operation, completed)]
    assert window.pending_operation is None
    assert window.cancel_wait_button.visible is False
