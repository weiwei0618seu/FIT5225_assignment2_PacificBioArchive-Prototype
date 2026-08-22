"""Thread-safe deterministic repositories for tests and local workflows."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from threading import RLock

from pacific_bioarchive.domain.media import MediaRecord
from pacific_bioarchive.domain.repositories import (
    ConflictError,
    DedupReservation,
    DuplicateFileError,
)


class InMemoryMediaRepository:
    def __init__(self) -> None:
        self._records: dict[str, MediaRecord] = {}
        self._lock = RLock()

    def create(self, record: MediaRecord) -> None:
        with self._lock:
            if record.file_id in self._records:
                raise ConflictError(f"Media {record.file_id} already exists")
            self._records[record.file_id] = record

    def get(self, file_id: str) -> MediaRecord | None:
        with self._lock:
            return self._records.get(file_id)

    def save(self, record: MediaRecord, *, expected_version: int) -> None:
        with self._lock:
            current = self._records.get(record.file_id)
            if current is None:
                raise ConflictError(f"Media {record.file_id} does not exist")
            if current.version != expected_version:
                raise ConflictError(
                    f"Media {record.file_id} version conflict: expected {expected_version}, "
                    f"found {current.version}"
                )
            if record.version <= expected_version:
                raise ConflictError("Saved record version must increase")
            self._records[record.file_id] = record

    def list_all(self) -> Sequence[MediaRecord]:
        with self._lock:
            return tuple(sorted(self._records.values(), key=lambda record: record.created_at))

    def delete(self, file_id: str) -> MediaRecord | None:
        with self._lock:
            return self._records.pop(file_id, None)


class InMemoryDedupRepository:
    def __init__(self, *, epoch_seconds: Callable[[], int] | None = None) -> None:
        self._reservations: dict[str, DedupReservation] = {}
        self._epoch_seconds = epoch_seconds or (lambda: int(time.time()))
        self._lock = RLock()

    def reserve(self, reservation: DedupReservation) -> None:
        with self._lock:
            current = self._reservations.get(reservation.checksum)
            if current is not None:
                expired = (
                    current.status == "RESERVED"
                    and current.expires_at is not None
                    and current.expires_at < self._epoch_seconds()
                )
                if not expired:
                    raise DuplicateFileError(current.checksum, current.file_id)
            if reservation.status != "RESERVED" or reservation.expires_at is None:
                raise ValueError("New checksum entries must be expiring RESERVED entries")
            self._reservations[reservation.checksum] = reservation

    def get(self, checksum: str) -> DedupReservation | None:
        with self._lock:
            return self._reservations.get(checksum)

    def commit(self, checksum: str, *, file_id: str) -> None:
        with self._lock:
            current = self._reservations.get(checksum)
            if current is None or current.file_id != file_id:
                raise ConflictError("Checksum reservation does not belong to this file")
            self._reservations[checksum] = DedupReservation(
                checksum=checksum,
                file_id=file_id,
                owner_sub=current.owner_sub,
                status="COMMITTED",
                expires_at=None,
            )

    def release(self, checksum: str, *, file_id: str) -> None:
        with self._lock:
            current = self._reservations.get(checksum)
            if current is None:
                return
            if current.file_id != file_id:
                raise ConflictError("Checksum reservation does not belong to this file")
            if current.status == "COMMITTED":
                raise ConflictError("Committed checksum cannot be released")
            del self._reservations[checksum]

    def remove(self, checksum: str, *, file_id: str) -> None:
        with self._lock:
            current = self._reservations.get(checksum)
            if current is None:
                return
            if current.file_id != file_id:
                raise ConflictError("Checksum entry does not belong to this file")
            del self._reservations[checksum]
