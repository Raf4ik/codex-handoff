from datetime import datetime, timezone
from pathlib import Path

from codex_handoff.models import RemoteHead, SnapshotManifest
from codex_handoff.providers.google_drive import GoogleDriveProvider


class Request:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class DownloadRequest:
    def __init__(self, payload: bytes):
        self.payload = payload


class Downloader:
    def __init__(self, stream, request: DownloadRequest):
        self.stream = stream
        self.request = request
        self.done = False

    def next_chunk(self):
        if not self.done:
            self.stream.write(self.request.payload)
            self.done = True
        return None, True


class Files:
    def __init__(self):
        self.items: list[dict] = []
        self.queries: list[str] = []

    def list(self, **kwargs):
        self.queries.append(kwargs.get("q", ""))
        return Request({"files": [{key: value for key, value in item.items() if key != "data"} for item in self.items]})

    def create(self, body, media_body=None, fields=None):
        item = dict(body)
        item["id"] = f"id-{len(self.items) + 1}"
        item["createdTime"] = datetime.now(timezone.utc).isoformat()
        item["data"] = media_body.getbytes(0, media_body.size()) if media_body else b""
        self.items.append(item)
        return Request(item)

    def update(self, fileId, media_body, fields=None):
        item = next(value for value in self.items if value["id"] == fileId)
        item["data"] = media_body.getbytes(0, media_body.size())
        return Request(item)

    def get_media(self, fileId):
        item = next(value for value in self.items if value["id"] == fileId)
        return DownloadRequest(item["data"])


class Service:
    def __init__(self):
        self.resource = Files()

    def files(self):
        return self.resource


def test_google_drive_provider_upload_head_list_and_download(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("codex_handoff.providers.google_drive.MediaIoBaseDownload", Downloader)
    provider = GoogleDriveProvider.__new__(GoogleDriveProvider)
    provider.service = Service()
    provider.folder_id = provider._ensure_folder()
    artifact = tmp_path / "version.chandoff"
    artifact.write_bytes(b"encrypted")
    manifest = SnapshotManifest("version-1", None, "mac", "safe", "2026-08-07T00:00:00Z", ())

    provider.upload_version(artifact, manifest)
    head = RemoteHead("version-1", None, "mac", manifest.created_at)
    provider.update_head(None, head)
    assert provider.read_head() == head
    assert provider.list_versions() == [head]

    destination = tmp_path / "download.chandoff"
    provider.download_artifact("version-1", destination)
    assert destination.read_bytes() == b"encrypted"


def test_read_head_uses_exact_named_file_query(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("codex_handoff.providers.google_drive.MediaIoBaseDownload", Downloader)
    provider = GoogleDriveProvider.__new__(GoogleDriveProvider)
    provider.service = Service()
    provider.folder_id = provider._ensure_folder()
    provider.service.resource.queries.clear()

    assert provider.read_head() is None

    assert len(provider.service.resource.queries) == 1
    assert "name='head.json'" in provider.service.resource.queries[0]
