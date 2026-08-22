"""Streaming SHA-256 helpers used for upload deduplication."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import BinaryIO

DEFAULT_CHUNK_SIZE = 1024 * 1024


def sha256_stream(stream: BinaryIO, *, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    digest = sha256()
    while chunk := stream.read(chunk_size):
        digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: str | Path, *, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    with Path(path).open("rb") as stream:
        return sha256_stream(stream, chunk_size=chunk_size)


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()

