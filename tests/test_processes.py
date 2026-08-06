import subprocess

from codex_handoff import processes


def test_posix_process_detection_matches_codex_app(monkeypatch) -> None:
    monkeypatch.setattr(processes.shutil, "which", lambda name: "/bin/ps")
    monkeypatch.setattr(
        processes.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "/Applications/Codex.app/Contents/MacOS/Codex\n/usr/bin/python\n", ""),
    )
    assert processes._posix_processes() == ["/Applications/Codex.app/Contents/MacOS/Codex"]


def test_windows_process_detection_matches_main_and_sandbox(monkeypatch) -> None:
    monkeypatch.setattr(
        processes.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, '"Codex.exe","101","Console","1","10,000 K"\n"codex-windows-sandbox.exe","102","Console","1","9,000 K"\n', ""
        ),
    )
    assert processes._windows_processes() == ["Codex.exe", "codex-windows-sandbox.exe"]
