from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil

from ..exceptions import BaselineExistsError, ConcurrentUpdateError, VersionNotFoundError
from ..models import RemoteHead, SnapshotManifest


class LocalProvider:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.baselines = self.root / "baselines"
        self.versions = self.root / "versions"
        self.head_path = self.root / "head.json"
        self.lock_path = self.root / ".publish.lock"
        self.baselines.mkdir(parents=True, exist_ok=True)
        self.versions.mkdir(parents=True, exist_ok=True)

    def baseline_ids(self) -> list[str]:
        return sorted(path.stem for path in self.baselines.glob("*.chandoff"))

    def upload_baseline(self, artifact: Path, manifest: SnapshotManifest) -> None:
        if self.baseline_ids():
            raise BaselineExistsError("An immutable baseline already exists")
        self._copy_immutable(artifact, self.baselines / f"{manifest.version_id}.chandoff")
        self._write_metadata(self.baselines, manifest)

    def upload_version(self, artifact: Path, manifest: SnapshotManifest) -> None:
        self._copy_immutable(artifact, self.versions / f"{manifest.version_id}.chandoff")
        self._write_metadata(self.versions, manifest)

    @staticmethod
    def _write_metadata(directory: Path, manifest: SnapshotManifest) -> None:
        destination = directory / f"{manifest.version_id}.json"
        destination.write_text(json.dumps(asdict(manifest), indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _copy_immutable(source: Path, destination: Path) -> None:
        if destination.exists():
            raise FileExistsError(destination)
        temporary = destination.with_suffix(".tmp")
        shutil.copy2(source, temporary)
        os.link(temporary, destination)
        temporary.unlink()

    def download_artifact(self, artifact_id: str, destination: Path) -> None:
        candidates = (self.versions / f"{artifact_id}.chandoff", self.baselines / f"{artifact_id}.chandoff")
        source = next((path for path in candidates if path.is_file()), None)
        if source is None:
            raise VersionNotFoundError(f"Artifact not found: {artifact_id}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    def read_head(self) -> RemoteHead | None:
        if not self.head_path.is_file():
            return None
        raw = json.loads(self.head_path.read_text(encoding="utf-8"))
        return RemoteHead(**raw)

    @contextmanager
    def _lock(self):
        try:
            descriptor = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise ConcurrentUpdateError("Another publish operation is in progress") from exc
        os.close(descriptor)
        try:
            yield
        finally:
            self.lock_path.unlink(missing_ok=True)

    def update_head(self, expected_version: str | None, head: RemoteHead) -> None:
        with self._lock():
            current = self.read_head()
            current_id = current.version_id if current else None
            if current_id != expected_version:
                raise ConcurrentUpdateError(f"Remote head changed: expected {expected_version}, found {current_id}")
            temporary = self.head_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(asdict(head), indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.head_path)

    def list_versions(self) -> list[RemoteHead]:
        result: list[RemoteHead] = []
        for path in sorted(self.versions.glob("*.json"), reverse=True):
            raw = json.loads(path.read_text(encoding="utf-8"))
            result.append(RemoteHead(raw["version_id"], raw.get("parent_version"), raw["source_device"], raw["created_at"]))
        return result
