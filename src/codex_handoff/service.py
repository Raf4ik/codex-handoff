from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from .artifacts import apply_artifact, build_artifact, new_identifier, preview_artifact, read_manifest, verify_artifact
from .config import AppConfig, validate_config
from .crypto import decrypt_file, encrypt_file, load_recovery_key
from .exceptions import BaselineExistsError, CodexRunningError, DeviceNotInitializedError, StaleDeviceError
from .models import ApplyPreview, DeviceState, RemoteHead, SnapshotManifest
from .processes import is_codex_running
from .providers.base import StorageProvider


class HandoffService:
    def __init__(self, config: AppConfig, provider: StorageProvider) -> None:
        validate_config(config)
        self.config = config
        self.provider = provider
        self.config.workspace_dir.mkdir(parents=True, exist_ok=True)
        assert self.config.encryption_key_file is not None
        self.key = load_recovery_key(self.config.encryption_key_file)
        (self.config.workspace_dir / "artifacts").mkdir(exist_ok=True)
        (self.config.workspace_dir / "baselines").mkdir(exist_ok=True)
        (self.config.workspace_dir / "backups").mkdir(exist_ok=True)
        (self.config.workspace_dir / "staging").mkdir(exist_ok=True)

    def _require_stopped(self) -> None:
        if is_codex_running():
            raise CodexRunningError("Codex is running. Close Codex before continuing.")

    def _state(self) -> DeviceState:
        baselines = self.provider.baseline_ids()
        baseline_id = baselines[0] if baselines else ""
        if not self.config.state_path.is_file():
            return DeviceState(self.config.device_id, baseline_id, None)
        raw = json.loads(self.config.state_path.read_text(encoding="utf-8"))
        return DeviceState(str(raw["device_id"]), str(raw.get("baseline_id", baseline_id)), raw.get("last_applied_version"))

    def _save_state(self, state: DeviceState) -> None:
        temporary = self.config.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(state), indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.config.state_path)

    def status(self) -> dict[str, object]:
        state = self._state()
        head = self.provider.read_head()
        initialized = self.config.state_path.is_file()
        update_available = bool(head and head.version_id != state.last_applied_version)
        local_baseline_available = bool(state.baseline_id and self._baseline_cache_path(state.baseline_id).is_file())
        return {
            "device_id": state.device_id,
            "baseline_id": state.baseline_id or None,
            "last_applied_version": state.last_applied_version,
            "remote_head": head.version_id if head else None,
            "remote_source": head.source_device if head else None,
            "update_available": update_available,
            "requires_initial_sync": bool(state.baseline_id and not initialized),
            "can_publish": bool(state.baseline_id and initialized and not update_available),
            "local_baseline_available": local_baseline_available,
            "codex_running": is_codex_running(),
        }

    def remote_head(self) -> RemoteHead | None:
        return self.provider.read_head()

    def create_baseline(self) -> SnapshotManifest:
        self._require_stopped()
        if self.provider.baseline_ids():
            raise BaselineExistsError("Protected parent baseline already exists")
        identifier = new_identifier("baseline")
        plain = self.config.workspace_dir / "staging" / f"{identifier}.zip"
        artifact = self.config.workspace_dir / "artifacts" / f"{identifier}.chandoff"
        manifest = build_artifact(
            self.config.source_dir,
            plain,
            version_id=identifier,
            parent_version=None,
            device_id=self.config.device_id,
        )
        encrypt_file(plain, artifact, self.key)
        plain.unlink(missing_ok=True)
        self.provider.upload_baseline(artifact, manifest)
        self._cache_baseline(manifest.version_id, artifact)
        state = self._state()
        self._save_state(DeviceState(state.device_id, identifier, state.last_applied_version))
        return manifest

    def push(self) -> SnapshotManifest:
        self._require_stopped()
        state = self._state()
        if not state.baseline_id:
            raise BaselineExistsError("Create or connect to a protected baseline first")
        if not self.config.state_path.is_file():
            raise DeviceNotInitializedError(
                "This is a new device. Sync from cloud or restore the protected baseline before publishing."
            )
        remote = self.provider.read_head()
        remote_id = remote.version_id if remote else None
        if remote_id != state.last_applied_version:
            raise StaleDeviceError(
                f"This device has {state.last_applied_version or 'no applied version'}, remote has {remote_id}. Pull first."
            )
        identifier = new_identifier("version")
        plain = self.config.workspace_dir / "staging" / f"{identifier}.zip"
        artifact = self.config.workspace_dir / "artifacts" / f"{identifier}.chandoff"
        manifest = build_artifact(
            self.config.source_dir,
            plain,
            version_id=identifier,
            parent_version=remote_id,
            device_id=self.config.device_id,
        )
        encrypt_file(plain, artifact, self.key)
        plain.unlink(missing_ok=True)
        self.provider.upload_version(artifact, manifest)
        head = RemoteHead(
            identifier,
            remote_id,
            self.config.device_id,
            manifest.created_at,
            manifest.source_platform,
        )
        self.provider.update_head(remote_id, head)
        self._save_state(DeviceState(state.device_id, state.baseline_id, identifier))
        return manifest

    def _download(self, artifact_id: str) -> Path:
        encrypted = self.config.workspace_dir / "artifacts" / f"{artifact_id}.chandoff"
        destination = self.config.workspace_dir / "staging" / f"{artifact_id}.zip"
        self.provider.download_artifact(artifact_id, encrypted)
        decrypt_file(encrypted, destination, self.key)
        verify_artifact(destination)
        return destination

    def _baseline_cache_path(self, baseline_id: str) -> Path:
        return self.config.workspace_dir / "baselines" / f"{baseline_id}.chandoff"

    def _cache_baseline(self, baseline_id: str, source: Path | None = None) -> Path:
        destination = self._baseline_cache_path(baseline_id)
        if destination.is_file():
            return destination
        if source is None:
            self.provider.download_artifact(baseline_id, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
        return destination

    def _cache_remote_baseline(self) -> None:
        baseline_ids = self.provider.baseline_ids()
        if baseline_ids:
            self._cache_baseline(baseline_ids[0])

    def _prepare_cached_baseline(self, baseline_id: str) -> Path:
        encrypted = self._cache_baseline(baseline_id)
        destination = self.config.workspace_dir / "staging" / f"{baseline_id}.zip"
        decrypt_file(encrypted, destination, self.key)
        verify_artifact(destination)
        return destination

    def preview_pull(self) -> ApplyPreview | None:
        head = self.provider.read_head()
        if head is None or head.version_id == self._state().last_applied_version:
            return None
        return preview_artifact(self._download(head.version_id), self.config.source_dir)

    def _backup_current(self) -> Path:
        identifier = new_identifier("backup")
        plain = self.config.workspace_dir / "staging" / f"{identifier}.zip"
        destination = self.config.workspace_dir / "backups" / f"{identifier}.chandoff"
        build_artifact(
            self.config.source_dir,
            plain,
            version_id=identifier,
            parent_version=self._state().last_applied_version,
            device_id=self.config.device_id,
        )
        encrypt_file(plain, destination, self.key)
        plain.unlink(missing_ok=True)
        return destination

    def pull(self) -> SnapshotManifest | None:
        self._require_stopped()
        head = self.provider.read_head()
        state = self._state()
        if head is None or head.version_id == state.last_applied_version:
            self._cache_remote_baseline()
            return None
        artifact = self._download(head.version_id)
        self._cache_remote_baseline()
        backup = self._backup_current()
        try:
            manifest = apply_artifact(artifact, self.config.source_dir, self.config.workspace_dir / "staging")
        except Exception:
            backup_plain = self.config.workspace_dir / "staging" / "rollback.zip"
            decrypt_file(backup, backup_plain, self.key)
            apply_artifact(backup_plain, self.config.source_dir, self.config.workspace_dir / "staging")
            backup_plain.unlink(missing_ok=True)
            raise
        self._save_state(DeviceState(state.device_id, state.baseline_id, head.version_id))
        return manifest

    def restore(self, artifact_id: str) -> SnapshotManifest:
        self._require_stopped()
        was_initialized = self.config.state_path.is_file()
        if artifact_id in self.provider.baseline_ids() or self._baseline_cache_path(artifact_id).is_file():
            artifact = self._prepare_cached_baseline(artifact_id)
        else:
            artifact = self._download(artifact_id)
        backup = self._backup_current()
        try:
            manifest = apply_artifact(artifact, self.config.source_dir, self.config.workspace_dir / "staging")
        except Exception:
            backup_plain = self.config.workspace_dir / "staging" / "rollback.zip"
            decrypt_file(backup, backup_plain, self.key)
            apply_artifact(backup_plain, self.config.source_dir, self.config.workspace_dir / "staging")
            backup_plain.unlink(missing_ok=True)
            raise
        if not was_initialized:
            state = self._state()
            head = self.provider.read_head()
            applied_head = artifact_id if head and head.version_id == artifact_id else None
            self._save_state(DeviceState(self.config.device_id, state.baseline_id, applied_head))
        return manifest

    def list_versions(self) -> list[RemoteHead]:
        return self.provider.list_versions()


def create_provider(config: AppConfig) -> StorageProvider:
    if config.provider == "local":
        from .providers.local import LocalProvider
        assert config.local_storage_dir is not None
        return LocalProvider(config.local_storage_dir)
    from .providers.google_drive import GoogleDriveProvider
    assert config.google_client_secrets is not None
    return GoogleDriveProvider(config.google_client_secrets, config.token_path)
