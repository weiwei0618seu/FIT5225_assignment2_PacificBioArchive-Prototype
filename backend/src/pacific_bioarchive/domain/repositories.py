"""Persistence ports used by application services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .media import MediaRecord


class DuplicateFileError(RuntimeError):
    def __init__(self, checksum: str, file_id: str | None = None) -> None:
        super().__init__("A file with this checksum already exists")
        self.checksum = checksum
        self.file_id = file_id


class RecordNotFoundError(LookupError):
    pass


class ConflictError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DedupReservation:
    checksum: str
    file_id: str
    owner_sub: str
    status: str
    expires_at: int | None = None


class MediaRepository(Protocol):
    def create(self, record: MediaRecord) -> None: ...

    def get(self, file_id: str) -> MediaRecord | None: ...

    def save(self, record: MediaRecord, *, expected_version: int) -> None: ...

    def list_all(self) -> Sequence[MediaRecord]: ...

    def delete(self, file_id: str) -> MediaRecord | None: ...


class DedupRepository(Protocol):
    def reserve(self, reservation: DedupReservation) -> None: ...

    def get(self, checksum: str) -> DedupReservation | None: ...

    def commit(self, checksum: str, *, file_id: str) -> None: ...

    def release(self, checksum: str, *, file_id: str) -> None: ...

