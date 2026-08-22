"""Correct logical-AND/count/media-reference query behavior."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Mapping
from urllib.parse import unquote, urlsplit

from pacific_bioarchive.domain.media import MediaRecord, ProcessingStatus
from pacific_bioarchive.domain.repositories import ConflictError, MediaRepository
from pacific_bioarchive.ml.labels import normalize_tag
from pacific_bioarchive.ml.types import InferenceResult


class QueryValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class QueryResult:
    records: tuple[MediaRecord, ...]
    total: int
    truncated: bool


def normalize_requirements(
    requirements: Mapping[str, int], *, max_tags: int = 20
) -> dict[str, int]:
    if not isinstance(requirements, Mapping) or not requirements:
        raise QueryValidationError(
            "INVALID_QUERY", "At least one species/tag requirement is required"
        )
    if len(requirements) > max_tags:
        raise QueryValidationError(
            "TOO_MANY_TAGS", f"At most {max_tags} tags can be queried at once"
        )
    normalized: dict[str, int] = {}
    for raw_tag, raw_count in requirements.items():
        tag = normalize_tag(str(raw_tag))
        if not tag:
            raise QueryValidationError("INVALID_TAG", "Tags cannot be empty")
        if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 1:
            raise QueryValidationError(
                "INVALID_MINIMUM_COUNT", "Every minimum count must be an integer of at least 1"
            )
        normalized[tag] = max(normalized.get(tag, 0), raw_count)
    return dict(sorted(normalized.items()))


def normalize_thumbnail_reference(reference: str, *, bucket_name: str | None = None) -> str:
    value = str(reference).strip()
    if not value:
        raise QueryValidationError("INVALID_THUMBNAIL_URL", "Thumbnail URL is required")
    parsed = urlsplit(value)
    if parsed.scheme:
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise QueryValidationError(
                "INVALID_THUMBNAIL_URL", "Only HTTP(S) thumbnail URLs are supported"
            )
        path = unquote(parsed.path).lstrip("/")
        host = parsed.netloc.split(":", 1)[0].lower()
        if bucket_name:
            expected_bucket = bucket_name.lower()
            if host.startswith(f"{expected_bucket}.s3"):
                key = path
            elif host.startswith("s3") and path.startswith(f"{bucket_name}/"):
                key = path[len(bucket_name) + 1 :]
            else:
                raise QueryValidationError(
                    "INVALID_THUMBNAIL_URL", "Thumbnail URL does not belong to the media bucket"
                )
        else:
            key = path
    else:
        key = unquote(value).lstrip("/")

    pure_key = PurePosixPath(key)
    if any(part in {"", ".", ".."} for part in pure_key.parts):
        raise QueryValidationError("INVALID_THUMBNAIL_URL", "Thumbnail key is unsafe")
    normalized_key = pure_key.as_posix()
    if not normalized_key.startswith("thumbnails/") or normalized_key.endswith("/"):
        raise QueryValidationError(
            "INVALID_THUMBNAIL_URL", "Reference must identify a thumbnail object"
        )
    return normalized_key


class MediaQueryService:
    def __init__(self, repository: MediaRepository, *, bucket_name: str | None = None) -> None:
        self._repository = repository
        self._bucket_name = bucket_name

    def find_by_requirements(
        self, requirements: Mapping[str, int], *, limit: int = 50
    ) -> QueryResult:
        normalized = normalize_requirements(requirements)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise QueryValidationError("INVALID_LIMIT", "limit must be between 1 and 100")
        matches = [
            record
            for record in self._repository.list_all()
            if record.processing_status == ProcessingStatus.READY
            and all(record.effective_count(tag) >= count for tag, count in normalized.items())
        ]
        matches.sort(key=lambda record: (record.created_at, record.file_id), reverse=True)
        return QueryResult(
            records=tuple(matches[:limit]),
            total=len(matches),
            truncated=len(matches) > limit,
        )

    def find_by_species(self, tag: str, *, limit: int = 50) -> QueryResult:
        normalized = normalize_tag(str(tag))
        if not normalized:
            raise QueryValidationError("INVALID_TAG", "A species/tag is required")
        return self.find_by_requirements({normalized: 1}, limit=limit)

    def find_by_inference(self, result: InferenceResult, *, limit: int = 50) -> QueryResult:
        if not result.species_counts:
            raise QueryValidationError(
                "NO_SPECIES_DETECTED", "No species were detected in the temporary query file"
            )
        return self.find_by_requirements(
            {tag: 1 for tag in result.species_counts}, limit=limit
        )

    def find_by_thumbnail(self, reference: str) -> MediaRecord | None:
        key = normalize_thumbnail_reference(reference, bucket_name=self._bucket_name)
        matches = [
            record
            for record in self._repository.list_all()
            if record.processing_status == ProcessingStatus.READY
            and record.thumbnail_key == key
        ]
        if len(matches) > 1:
            raise ConflictError(f"Multiple media records use thumbnail key {key}")
        return matches[0] if matches else None

