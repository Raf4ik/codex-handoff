from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .exceptions import ConfigurationError, IntegrityError

MAGIC = b"CODEX-HANDOFF\x01"
NONCE_SIZE = 12
TAG_SIZE = 16
CHUNK_SIZE = 1024 * 1024


def generate_recovery_key(path: Path) -> Path:
    if path.exists():
        raise ConfigurationError(f"Refusing to overwrite recovery key: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(base64.urlsafe_b64encode(AESGCM.generate_key(bit_length=256)).decode("ascii") + "\n", encoding="ascii")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def load_recovery_key(path: Path) -> bytes:
    try:
        key = base64.urlsafe_b64decode(path.read_text(encoding="ascii").strip().encode("ascii"))
    except Exception as exc:
        raise ConfigurationError(f"Invalid recovery key file: {path}") from exc
    if len(key) != 32:
        raise ConfigurationError(f"Recovery key must contain a 256-bit key: {path}")
    return key


def encrypt_file(source: Path, destination: Path, key: bytes) -> None:
    nonce = os.urandom(NONCE_SIZE)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(MAGIC)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with source.open("rb") as input_stream, temporary.open("wb+") as output_stream:
        output_stream.write(MAGIC + nonce + (b"\0" * TAG_SIZE))
        for chunk in iter(lambda: input_stream.read(CHUNK_SIZE), b""):
            output_stream.write(encryptor.update(chunk))
        output_stream.write(encryptor.finalize())
        output_stream.seek(len(MAGIC) + NONCE_SIZE)
        output_stream.write(encryptor.tag)
    temporary.replace(destination)


def decrypt_file(source: Path, destination: Path, key: bytes) -> None:
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        with source.open("rb") as input_stream:
            if input_stream.read(len(MAGIC)) != MAGIC:
                raise IntegrityError("Invalid encrypted artifact header")
            nonce = input_stream.read(NONCE_SIZE)
            tag = input_stream.read(TAG_SIZE)
            if len(nonce) != NONCE_SIZE or len(tag) != TAG_SIZE:
                raise IntegrityError("Truncated encrypted artifact header")
            decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
            decryptor.authenticate_additional_data(MAGIC)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("wb") as output_stream:
                for chunk in iter(lambda: input_stream.read(CHUNK_SIZE), b""):
                    output_stream.write(decryptor.update(chunk))
                output_stream.write(decryptor.finalize())
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        if isinstance(exc, IntegrityError):
            raise
        raise IntegrityError("Unable to decrypt artifact; the recovery key may be wrong") from exc
    temporary.replace(destination)
