"""Private object-storage port."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PresignedPut:
    url: str
    headers: dict[str, str]
    expires_in: int


@dataclass(frozen=True, slots=True)
class ObjectInfo:
    size_bytes: int
    content_type: str
    checksum_sha256_base64: str | None
    metadata: dict[str, str]


class ObjectStorage(Protocol):
    def delete(self, key: str) -> None:
        """Delete an object; missing keys must be treated as success."""


class PrivateObjectStorage(ObjectStorage, Protocol):
    def create_presigned_put(
        self,
        *,
        key: str,
        content_type: str,
        checksum_hex: str,
        file_id: str,
        expires_in: int,
    ) -> PresignedPut: ...

    def create_presigned_get(self, key: str, *, expires_in: int) -> str: ...

    def head(self, key: str) -> ObjectInfo: ...

    def download_file(self, key: str, destination: str | Path) -> None: ...

    def upload_bytes(self, key: str, data: bytes, *, content_type: str) -> None: ...
