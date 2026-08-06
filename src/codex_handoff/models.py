from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class FileEntry:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class SnapshotManifest:
    version_id: str
    parent_version: str | None
    source_device: str
    profile: str
    created_at: str
    files: tuple[FileEntry, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class DeviceState:
    device_id: str
    baseline_id: str
    last_applied_version: str | None


@dataclass(frozen=True, slots=True)
class Profile:
    name: str
    include_roots: tuple[str, ...]
    exclude_globs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RemoteHead:
    version_id: str
    parent_version: str | None
    source_device: str
    created_at: str


@dataclass(frozen=True, slots=True)
class ApplyPreview:
    version_id: str
    source_device: str
    added: tuple[str, ...]
    changed: tuple[str, ...]
    unchanged: tuple[str, ...]
