from pathlib import Path

import pytest

from codex_handoff.crypto import decrypt_file, encrypt_file, generate_recovery_key, load_recovery_key
from codex_handoff.exceptions import IntegrityError


def test_streaming_encryption_round_trip_and_wrong_key(tmp_path: Path) -> None:
    first_key_path = generate_recovery_key(tmp_path / "first.key")
    second_key_path = generate_recovery_key(tmp_path / "second.key")
    source = tmp_path / "large.zip"
    source.write_bytes((b"codex-handoff" * 100_000) + b"tail")
    encrypted = tmp_path / "snapshot.chandoff"
    restored = tmp_path / "restored.zip"

    encrypt_file(source, encrypted, load_recovery_key(first_key_path))
    assert b"codex-handoff" not in encrypted.read_bytes()
    decrypt_file(encrypted, restored, load_recovery_key(first_key_path))
    assert restored.read_bytes() == source.read_bytes()

    with pytest.raises(IntegrityError):
        decrypt_file(encrypted, tmp_path / "wrong.zip", load_recovery_key(second_key_path))
