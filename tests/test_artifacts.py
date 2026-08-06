from pathlib import Path
import zipfile

import pytest

from codex_handoff.artifacts import apply_artifact, build_artifact, preview_artifact, verify_artifact
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
