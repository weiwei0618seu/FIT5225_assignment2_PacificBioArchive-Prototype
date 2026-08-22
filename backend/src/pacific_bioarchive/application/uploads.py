"""Authenticated checksum-first S3 upload initiation."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from pacific_bioarchive.domain.media import MediaRecord
from pacific_bioarchive.domain.repositories import (
    DedupRepository,
    DedupReservation,
    MediaRepository,
)
from pacific_bioarchive.domain.storage import PresignedPut, PrivateObjectStorage
from pacific_bioarchive.media.validation import (
    UploadMetadata,
    validate_checksum,
    validate_upload_metadata,
)


@dataclass(frozen=True, slots=True)
class UploadTicket:
    file_id: str
    object_key: str
    upload: PresignedPut
    record: MediaRecord


class UploadService:
    def __init__(
        self,
        *,
        media_repository: MediaRepository,
        dedup_repository: DedupRepository,
        storage: PrivateObjectStorage,
        id_factory: Callable[[], object] = uuid4,
        epoch_seconds: Callable[[], int] | None = None,
        now_iso: Callable[[], str] | None = None,
        reservation_seconds: int = 3600,
        upload_url_seconds: int = 900,
    ) -> None:
        from pacific_bioarchive.domain.media import utc_now

        if reservation_seconds <= upload_url_seconds:
            raise ValueError("Reservation must outlive the presigned upload URL")
        self._media = media_repository
        self._dedup = dedup_repository
        self._storage = storage
        self._id_factory = id_factory
        self._epoch_seconds = epoch_seconds or (lambda: int(time.time()))
        self._now_iso = now_iso or utc_now
        self._reservation_seconds = reservation_seconds
        self._upload_url_seconds = upload_url_seconds

    def initiate(
        self,
        *,
        actor_sub: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        checksum: str,
    ) -> UploadTicket:
        if not actor_sub.strip():
            raise ValueError("Authenticated actor_sub is required")
        metadata: UploadMetadata = validate_upload_metadata(
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        normalized_checksum = validate_checksum(checksum)
        file_id = str(self._id_factory())
        if not file_id.strip() or "/" in file_id or "\\" in file_id:
            raise ValueError("id_factory returned an unsafe identifier")
        object_key = f"originals/{file_id}/{metadata.filename}"
        now = self._now_iso()
        reservation = DedupReservation(
            checksum=normalized_checksum,
            file_id=file_id,
            owner_sub=actor_sub,
            status="RESERVED",
            expires_at=self._epoch_seconds() + self._reservation_seconds,
        )
        record = MediaRecord(
            file_id=file_id,
            owner_sub=actor_sub,
            filename=metadata.filename,
            checksum=normalized_checksum,
            file_type=metadata.file_type,
            content_type=metadata.content_type,
            size_bytes=metadata.size_bytes,
            original_key=object_key,
            created_at=now,
            updated_at=now,
        )

        self._dedup.reserve(reservation)
        try:
            self._media.create(record)
        except Exception:
            self._dedup.release(normalized_checksum, file_id=file_id)
            raise
        try:
            presigned = self._storage.create_presigned_put(
                key=object_key,
                content_type=metadata.content_type,
                checksum_hex=normalized_checksum,
                file_id=file_id,
                expires_in=self._upload_url_seconds,
            )
        except Exception:
            self._media.delete(file_id)
            self._dedup.release(normalized_checksum, file_id=file_id)
            raise
        return UploadTicket(
            file_id=file_id,
            object_key=object_key,
            upload=presigned,
            record=record,
        )

