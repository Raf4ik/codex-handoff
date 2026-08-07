from __future__ import annotations

from dataclasses import asdict
import io
import json
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload

from ..exceptions import BaselineExistsError, ConcurrentUpdateError, VersionNotFoundError
from ..models import RemoteHead, SnapshotManifest

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
APP_FOLDER_NAME = "Codex Handoff"


def authorize(client_secrets: Path, token_path: Path):
    credentials = None
    if token_path.is_file():
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except RefreshError:
            credentials = None
    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
        credentials = flow.run_local_server(port=0, open_browser=True)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    try:
        token_path.chmod(0o600)
    except OSError:
        pass
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


class GoogleDriveProvider:
    def __init__(self, client_secrets: Path, token_path: Path) -> None:
        self.service = authorize(client_secrets, token_path)
        self.folder_id = self._ensure_folder()

    def _ensure_folder(self) -> str:
        query = (
            f"name='{APP_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' "
            "and appProperties has { key='codex_handoff' and value='root' } and trashed=false"
        )
        response = self.service.files().list(q=query, spaces="drive", fields="files(id,name)").execute()
        files = response.get("files", [])
        if files:
            return str(files[0]["id"])
        created = self.service.files().create(
            body={
                "name": APP_FOLDER_NAME,
                "mimeType": "application/vnd.google-apps.folder",
                "appProperties": {"codex_handoff": "root"},
            },
            fields="id",
        ).execute()
        return str(created["id"])

    def _files(self) -> list[dict]:
        query = f"'{self.folder_id}' in parents and trashed=false"
        result: list[dict] = []
        page_token = None
        while True:
            response = self.service.files().list(
                q=query,
                spaces="drive",
                fields="nextPageToken,files(id,name,createdTime,appProperties)",
                pageSize=1000,
                pageToken=page_token,
            ).execute()
            result.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                return result

    def _find_named_file(self, name: str) -> dict | None:
        escaped = name.replace("\\", "\\\\").replace("'", "\\'")
        query = f"'{self.folder_id}' in parents and name='{escaped}' and trashed=false"
        response = self.service.files().list(
            q=query,
            spaces="drive",
            fields="files(id,name,createdTime,appProperties)",
            pageSize=10,
        ).execute()
        return next((item for item in response.get("files", []) if item.get("name") == name), None)

    def baseline_ids(self) -> list[str]:
        return sorted(
            path["name"][:-4]
            for path in self._files()
            if path.get("name", "").startswith("baseline-") and path["name"].endswith(".chandoff")
        )

    def upload_baseline(self, artifact: Path, manifest: SnapshotManifest) -> None:
        if self.baseline_ids():
            raise BaselineExistsError("An immutable baseline already exists in Google Drive")
        self._upload_artifact(artifact, manifest, "baseline")

    def upload_version(self, artifact: Path, manifest: SnapshotManifest) -> None:
        self._upload_artifact(artifact, manifest, "version")

    def _upload_artifact(self, artifact: Path, manifest: SnapshotManifest, kind: str) -> None:
        name = f"{manifest.version_id}.chandoff"
        if any(item.get("name") == name for item in self._files()):
            raise FileExistsError(name)
        media = MediaFileUpload(str(artifact), mimetype="application/octet-stream", resumable=True)
        self.service.files().create(
            body={
                "name": name,
                "parents": [self.folder_id],
                "appProperties": {
                    "kind": kind,
                    "version_id": manifest.version_id,
                    "parent_version": manifest.parent_version or "",
                    "source_device": manifest.source_device,
                    "created_at": manifest.created_at,
                    "source_platform": manifest.source_platform or "",
                },
            },
            media_body=media,
            fields="id,name,size",
        ).execute()

    def download_artifact(self, artifact_id: str, destination: Path) -> None:
        name = f"{artifact_id}.chandoff"
        match = next((item for item in self._files() if item.get("name") == name), None)
        if match is None:
            raise VersionNotFoundError(f"Google Drive artifact not found: {artifact_id}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = self.service.files().get_media(fileId=match["id"])
        with destination.open("wb") as stream:
            downloader = MediaIoBaseDownload(stream, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

    def _head_file(self) -> dict | None:
        return self._find_named_file("head.json")

    def read_head(self) -> RemoteHead | None:
        match = self._head_file()
        if match is None:
            return None
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, self.service.files().get_media(fileId=match["id"]))
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return RemoteHead(**json.loads(buffer.getvalue().decode("utf-8")))

    def update_head(self, expected_version: str | None, head: RemoteHead) -> None:
        current = self.read_head()
        current_id = current.version_id if current else None
        if current_id != expected_version:
            raise ConcurrentUpdateError(f"Remote head changed: expected {expected_version}, found {current_id}")
        payload = io.BytesIO((json.dumps(asdict(head), indent=2) + "\n").encode("utf-8"))
        media = MediaIoBaseUpload(payload, mimetype="application/json", resumable=False)
        existing = self._head_file()
        if existing:
            self.service.files().update(fileId=existing["id"], media_body=media, fields="id").execute()
        else:
            self.service.files().create(
                body={"name": "head.json", "parents": [self.folder_id], "appProperties": {"kind": "head"}},
                media_body=media,
                fields="id",
            ).execute()
        confirmed = self.read_head()
        if confirmed is None or confirmed.version_id != head.version_id:
            raise ConcurrentUpdateError("Google Drive head verification failed")

    def list_versions(self) -> list[RemoteHead]:
        result: list[RemoteHead] = []
        for item in self._files():
            properties = item.get("appProperties") or {}
            if properties.get("kind") != "version":
                continue
            result.append(
                RemoteHead(
                    version_id=properties["version_id"],
                    parent_version=properties.get("parent_version") or None,
                    source_device=properties.get("source_device", "unknown"),
                    created_at=properties.get("created_at") or item.get("createdTime", ""),
                    source_platform=properties.get("source_platform") or None,
                )
            )
        return sorted(result, key=lambda item: item.created_at, reverse=True)
