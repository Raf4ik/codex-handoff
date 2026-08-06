from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

from .exceptions import ConfigurationError


@dataclass(frozen=True, slots=True)
class AppConfig:
    device_id: str
    source_dir: Path
    workspace_dir: Path
    provider: str = "local"
    local_storage_dir: Path | None = None
    google_client_secrets: Path | None = None
    encryption_key_file: Path | None = None

    @property
    def state_path(self) -> Path:
        return self.workspace_dir / "device-state.json"

    @property
    def token_path(self) -> Path:
        suffix = "default"
        if self.google_client_secrets and self.google_client_secrets.is_file():
            suffix = hashlib.sha256(self.google_client_secrets.read_bytes()).hexdigest()[:12]
        return Path(user_config_dir("Codex Handoff")) / f"google-token-{suffix}.json"


def default_config_path() -> Path:
    return Path(user_config_dir("Codex Handoff")) / "config.json"


def default_workspace() -> Path:
    return Path(user_data_dir("Codex Handoff"))


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    destination = path or default_config_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(config)
    for key, value in tuple(payload.items()):
        if isinstance(value, Path):
            payload[key] = str(value)
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
    try:
        destination.chmod(0o600)
    except OSError:
        pass
    return destination


def load_config(path: Path | None = None) -> AppConfig:
    source = path or default_config_path()
    if not source.is_file():
        raise ConfigurationError(f"Configuration not found: {source}")
    raw = json.loads(source.read_text(encoding="utf-8"))
    return AppConfig(
        device_id=str(raw["device_id"]),
        source_dir=Path(raw["source_dir"]).expanduser(),
        workspace_dir=Path(raw["workspace_dir"]).expanduser(),
        provider=str(raw.get("provider", "local")),
        local_storage_dir=Path(raw["local_storage_dir"]).expanduser() if raw.get("local_storage_dir") else None,
        google_client_secrets=Path(raw["google_client_secrets"]).expanduser() if raw.get("google_client_secrets") else None,
        encryption_key_file=Path(raw["encryption_key_file"]).expanduser() if raw.get("encryption_key_file") else None,
    )


def validate_config(config: AppConfig) -> None:
    if not config.device_id.strip():
        raise ConfigurationError("Device ID is required")
    if not config.source_dir.is_dir():
        raise ConfigurationError(f"Codex state directory not found: {config.source_dir}")
    if config.provider == "local" and config.local_storage_dir is None:
        raise ConfigurationError("Local storage directory is required")
    if config.provider == "google_drive" and (
        config.google_client_secrets is None or not config.google_client_secrets.is_file()
    ):
        raise ConfigurationError("Google OAuth client secrets JSON is required")
    if config.provider not in {"local", "google_drive"}:
        raise ConfigurationError(f"Unsupported provider: {config.provider}")
    if config.encryption_key_file is None or not config.encryption_key_file.is_file():
        raise ConfigurationError("Encryption recovery key file is required")
