"""Media aggregate and valid processing transitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Mapping

from pacific_bioarchive.media.validation import MediaType, validate_checksum
from pacific_bioarchive.ml.labels import normalize_tag


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class ProcessingStatus(StrEnum):
    RESERVED = "RESERVED"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class MediaRecord:
    file_id: str
    owner_sub: str
    filename: str
    checksum: str
    file_type: MediaType
    content_type: str
    size_bytes: int
    original_key: str
    thumbnail_key: str | None = None
    species_counts: Mapping[str, int] | None = None
    manual_tags: tuple[str, ...] = ()
    detections: tuple[dict[str, object], ...] = ()
    video_samples: int | None = None
    processing_status: ProcessingStatus = ProcessingStatus.RESERVED
    error_code: str | None = None
    created_at: str = ""
    updated_at: str = ""
    version: int = 1

    def __post_init__(self) -> None:
        required = {
            "file_id": self.file_id,
            "owner_sub": self.owner_sub,
            "filename": self.filename,
            "checksum": self.checksum,
            "content_type": self.content_type,
            "original_key": self.original_key,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise ValueError(f"Missing required media fields: {', '.join(missing)}")
        if self.size_bytes < 1:
            raise ValueError("size_bytes must be positive")
        if self.version < 1:
            raise ValueError("version must be positive")
        if self.video_samples is not None and self.video_samples < 0:
            raise ValueError("video_samples cannot be negative")

        normalized_counts: dict[str, int] = {}
        object.__setattr__(self, "checksum", validate_checksum(self.checksum))
        for raw_tag, raw_count in (self.species_counts or {}).items():
            tag = normalize_tag(raw_tag)
            count = int(raw_count)
            if not tag or count < 1:
                raise ValueError("species_counts require non-empty tags and positive counts")
            normalized_counts[tag] = count
        normalized_manual = tuple(
            sorted({tag for raw in self.manual_tags if (tag := normalize_tag(raw))})
        )
        object.__setattr__(self, "species_counts", dict(sorted(normalized_counts.items())))
        object.__setattr__(self, "manual_tags", normalized_manual)
        object.__setattr__(self, "detections", tuple(dict(item) for item in self.detections))
        if not self.created_at:
            object.__setattr__(self, "created_at", utc_now())
        if not self.updated_at:
            object.__setattr__(self, "updated_at", self.created_at)

        if self.processing_status == ProcessingStatus.READY:
            if self.file_type == MediaType.IMAGE and not self.thumbnail_key:
                raise ValueError("READY images require a thumbnail_key")
            if self.error_code:
                raise ValueError("READY media cannot have an error_code")

    @property
    def auto_tags(self) -> tuple[str, ...]:
        return tuple(self.species_counts or {})

    @property
    def all_tags(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.auto_tags).union(self.manual_tags)))

    def effective_count(self, raw_tag: str) -> int:
        tag = normalize_tag(raw_tag)
        automatic = int((self.species_counts or {}).get(tag, 0))
        return max(automatic, 1 if tag in self.manual_tags else 0)

    def mark_processing(self, *, now: str | None = None) -> "MediaRecord":
        if self.processing_status == ProcessingStatus.READY:
            return self
        return replace(
            self,
            processing_status=ProcessingStatus.PROCESSING,
            error_code=None,
            updated_at=now or utc_now(),
            version=self.version + 1,
        )

    def mark_ready(
        self,
        *,
        species_counts: Mapping[str, int],
        detections: tuple[dict[str, object], ...],
        thumbnail_key: str | None = None,
        video_samples: int | None = None,
        now: str | None = None,
    ) -> "MediaRecord":
        return replace(
            self,
            species_counts=species_counts,
            detections=detections,
            thumbnail_key=thumbnail_key,
            video_samples=video_samples,
            processing_status=ProcessingStatus.READY,
            error_code=None,
            updated_at=now or utc_now(),
            version=self.version + 1,
        )

    def mark_failed(self, error_code: str, *, now: str | None = None) -> "MediaRecord":
        if not error_code.strip():
            raise ValueError("error_code is required")
        return replace(
            self,
            processing_status=ProcessingStatus.FAILED,
            error_code=error_code.strip(),
            updated_at=now or utc_now(),
            version=self.version + 1,
        )

    def with_manual_tags(
        self, tags: set[str] | tuple[str, ...] | list[str], *, now: str | None = None
    ) -> "MediaRecord":
        return replace(
            self,
            manual_tags=tuple(tags),
            updated_at=now or utc_now(),
            version=self.version + 1,
        )
