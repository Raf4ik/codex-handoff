from __future__ import annotations

import csv
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys


def codex_processes() -> list[str]:
    if sys.platform.startswith("win"):
        return _windows_processes()
    return _posix_processes()


def is_codex_running() -> bool:
    return bool(codex_processes())


def _windows_processes() -> list[str]:
    result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError("Unable to inspect Windows processes")
    matches: list[str] = []
    for row in csv.reader(io.StringIO(result.stdout)):
        if not row:
            continue
        name = row[0].strip().lower()
        if name in {"codex.exe", "codex-windows-sandbox.exe"}:
            matches.append(row[0].strip())
    return matches


def _posix_processes() -> list[str]:
    ps = shutil.which("ps")
    if ps is None:
        raise RuntimeError("ps is unavailable")
    result = subprocess.run([ps, "-A", "-o", "comm="], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError("Unable to inspect running processes")
    matches: list[str] = []
    for raw in result.stdout.splitlines():
        name = Path(raw.strip()).name.lower()
        if name in {"codex", "codex-windows-sandbox"}:
            matches.append(raw.strip())
    return matches
