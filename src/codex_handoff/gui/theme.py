from atexit import register
from contextlib import ExitStack
from importlib.resources import as_file, files
from pathlib import Path

from PySide6.QtGui import QIcon


_RESOURCE_CONTEXTS = ExitStack()
register(_RESOURCE_CONTEXTS.close)


def app_icon_path() -> Path:
    resource = files("codex_handoff.assets").joinpath("codex-handoff.png")
    try:
        return Path(resource)
    except TypeError:
        return _RESOURCE_CONTEXTS.enter_context(as_file(resource))


def load_app_icon() -> QIcon:
    return QIcon(str(app_icon_path()))
