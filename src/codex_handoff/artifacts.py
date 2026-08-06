from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import uuid
import zipfile

from .exceptions import IntegrityError
from .models import ApplyPreview, FileEntry, Profile, SnapshotManifest
from .profiles import DEFAULT_PROFILE, is_included


def new_identifier(prefix: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{timestamp}-{uuid.uuid4().hex[:12]}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable_files(source: Path, profile: Profile) -> list[Path]:
    files: list[Path] = []
    for path in source.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(source).as_posix()
        if is_included(relative, profile):
            files.append(path)
    return sorted(files, key=lambda value: value.relative_to(source).as_posix())


def build_artifact(
    source: Path,
    destination: Path,
    *,
    version_id: str,
    parent_version: str | None,
    device_id: str,
    profile: Profile = DEFAULT_PROFILE,
) -> SnapshotManifest:
    destination.parent.mkdir(parents=True, exist_ok=True)
    entries = tuple(
        FileEntry(path.relative_to(source).as_posix(), path.stat().st_size, sha256_file(path))
        for path in _portable_files(source, profile)
    )
    manifest = SnapshotManifest(
        version_id=version_id,
        parent_version=parent_version,
        source_device=device_id,
        profile=profile.name,
        created_at=datetime.now(timezone.utc).isoformat(),
        files=entries,
    )
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr("manifest.json", json.dumps(asdict(manifest), indent=2) + "\n")
        for entry in entries:
            archive.write(source / entry.path, f"data/{entry.path}")
    temporary.replace(destination)
    verify_artifact(destination)
    return manifest


def read_manifest(artifact: Path) -> SnapshotManifest:
    with zipfile.ZipFile(artifact, "r") as archive:
        raw = json.loads(archive.read("manifest.json"))
    return SnapshotManifest(
        version_id=str(raw["version_id"]),
        parent_version=raw.get("parent_version"),
        source_device=str(raw["source_device"]),
        profile=str(raw["profile"]),
        created_at=str(raw["created_at"]),
        files=tuple(FileEntry(str(item["path"]), int(item["size"]), str(item["sha256"])) for item in raw["files"]),
    )


def _safe_member(relative: str) -> str:
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or not relative or relative.startswith(("/", "\\")):
        raise IntegrityError(f"Unsafe path in snapshot: {relative}")
    return path.as_posix()


def verify_artifact(artifact: Path) -> SnapshotManifest:
    manifest = read_manifest(artifact)
    with zipfile.ZipFile(artifact, "r") as archive:
        names = set(archive.namelist())
        for entry in manifest.files:
            relative = _safe_member(entry.path)
            member = f"data/{relative}"
            if member not in names:
                raise IntegrityError(f"Missing snapshot file: {relative}")
            payload = archive.read(member)
            if len(payload) != entry.size or hashlib.sha256(payload).hexdigest() != entry.sha256:
                raise IntegrityError(f"Snapshot verification failed: {relative}")
    return manifest


def preview_artifact(artifact: Path, target: Path) -> ApplyPreview:
    manifest = verify_artifact(artifact)
    added: list[str] = []
    changed: list[str] = []
    unchanged: list[str] = []
    for entry in manifest.files:
        path = target / _safe_member(entry.path)
        if not path.is_file():
            added.append(entry.path)
        elif path.stat().st_size == entry.size and sha256_file(path) == entry.sha256:
            unchanged.append(entry.path)
        else:
            changed.append(entry.path)
    return ApplyPreview(manifest.version_id, manifest.source_device, tuple(added), tuple(changed), tuple(unchanged))


def apply_artifact(artifact: Path, target: Path, staging_root: Path) -> SnapshotManifest:
    manifest = verify_artifact(artifact)
    staging = staging_root / f"apply-{uuid.uuid4().hex}"
    staging.mkdir(parents=True)
    try:
        with zipfile.ZipFile(artifact, "r") as archive:
            for entry in manifest.files:
                relative = _safe_member(entry.path)
                staged = staging / relative
                staged.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(f"data/{relative}") as source, staged.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                if sha256_file(staged) != entry.sha256:
                    raise IntegrityError(f"Staged file verification failed: {relative}")
        snapshot_paths = {entry.path for entry in manifest.files}
        for current in _portable_files(target, DEFAULT_PROFILE):
            if current.relative_to(target).as_posix() not in snapshot_paths:
                current.unlink()
        for entry in manifest.files:
            relative = _safe_member(entry.path)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            (staging / relative).replace(destination)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return manifest
