from pathlib import Path
import json
import zipfile

import pytest

from codex_handoff.artifacts import apply_artifact, build_artifact, preview_artifact, read_manifest, verify_artifact
from codex_handoff.exceptions import IntegrityError


def state(root: Path, value: str) -> Path:
    root.mkdir(parents=True)
    (root / "sessions").mkdir()
    (root / "sessions" / "one.json").write_text(value, encoding="utf-8")
    (root / "auth.json").write_text("secret", encoding="utf-8")
    return root


def test_artifact_excludes_credentials_and_applies_portable_files(tmp_path: Path) -> None:
    source = state(tmp_path / "source", "from-mac")
    target = state(tmp_path / "target", "old-windows")
    (source / "archived_sessions").mkdir()
    (source / "archived_sessions" / "old.jsonl").write_text("archived", encoding="utf-8")
    (source / "AGENTS.md").write_text("portable instructions", encoding="utf-8")
    artifact = tmp_path / "snapshot.zip"
    manifest = build_artifact(source, artifact, version_id="v1", parent_version=None, device_id="mac")

    assert [entry.path for entry in manifest.files] == ["AGENTS.md", "archived_sessions/old.jsonl", "sessions/one.json"]
    preview = preview_artifact(artifact, target)
    assert preview.changed == ("sessions/one.json",)
    apply_artifact(artifact, target, tmp_path / "staging")
    assert (target / "sessions/one.json").read_text() == "from-mac"
    assert (target / "auth.json").read_text() == "secret"


def test_apply_removes_portable_file_absent_from_snapshot(tmp_path: Path) -> None:
    source = state(tmp_path / "source", "source")
    target = state(tmp_path / "target", "target")
    (target / "sessions" / "obsolete.json").write_text("obsolete", encoding="utf-8")
    artifact = tmp_path / "snapshot.zip"
    build_artifact(source, artifact, version_id="v1", parent_version=None, device_id="mac")
    apply_artifact(artifact, target, tmp_path / "staging")
    assert not (target / "sessions" / "obsolete.json").exists()


def test_preview_reports_removed_portable_file(tmp_path: Path) -> None:
    source = state(tmp_path / "source", "source")
    target = state(tmp_path / "target", "target")
    (target / "sessions" / "obsolete.json").write_text("obsolete", encoding="utf-8")
    artifact = tmp_path / "snapshot.zip"
    build_artifact(source, artifact, version_id="v1", parent_version=None, device_id="mac")

    preview = preview_artifact(artifact, target)

    assert preview.removed == ("sessions/obsolete.json",)
    assert preview.source_platform
    assert preview.created_at


def test_manifest_without_source_platform_remains_readable(tmp_path: Path) -> None:
    source = state(tmp_path / "source", "source")
    artifact = tmp_path / "snapshot.zip"
    expected = build_artifact(source, artifact, version_id="v1", parent_version=None, device_id="old-device")
    with zipfile.ZipFile(artifact, "r") as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    raw = json.loads(members["manifest.json"])
    raw.pop("source_platform", None)
    members["manifest.json"] = (json.dumps(raw) + "\n").encode()
    with zipfile.ZipFile(artifact, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)

    loaded = read_manifest(artifact)

    assert loaded.version_id == expected.version_id
    assert loaded.source_platform is None


def test_macos_source_platform_uses_cross_platform_protocol_name(tmp_path: Path, monkeypatch) -> None:
    source = state(tmp_path / "source", "source")
    artifact = tmp_path / "snapshot.zip"
    monkeypatch.setattr("codex_handoff.artifacts.platform.system", lambda: "Darwin")

    manifest = build_artifact(source, artifact, version_id="v1", parent_version=None, device_id="mac")

    assert manifest.source_platform == "macos"


def test_artifact_rejects_path_traversal(tmp_path: Path) -> None:
    artifact = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr(
            "manifest.json",
            '{"version_id":"v1","parent_version":null,"source_device":"x","profile":"safe","created_at":"now","files":[{"path":"../escape","size":1,"sha256":"x"}]}'
        )
        archive.writestr("data/../escape", "x")
    with pytest.raises(IntegrityError):
        verify_artifact(artifact)
