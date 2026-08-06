from __future__ import annotations

from pathlib import PurePosixPath

from .models import Profile

DEFAULT_PROFILE = Profile(
    name="safe",
    include_roots=(
        "sessions",
        "archived_sessions",
        "attachments",
        "session_index.jsonl",
        "skills",
        "plugins",
        "rules",
        "AGENTS.md",
    ),
    exclude_globs=(
        "**/*.lock", "**/*.tmp", "**/*.temp", "**/*.log", "**/cache/**",
        "**/.cache/**", "**/tmp/**", "**/*.sqlite", "**/*.db",
        "**/*.sqlite-wal", "**/*.sqlite-shm",
    ),
)


def is_excluded(relative_path: str, profile: Profile = DEFAULT_PROFILE) -> bool:
    path = PurePosixPath(relative_path.replace("\\", "/"))
    return any(path.match(pattern) for pattern in profile.exclude_globs)


def is_included(relative_path: str, profile: Profile = DEFAULT_PROFILE) -> bool:
    path = relative_path.replace("\\", "/").strip("/")
    if is_excluded(path, profile):
        return False
    return any(path == root or path.startswith(f"{root}/") for root in profile.include_roots)
