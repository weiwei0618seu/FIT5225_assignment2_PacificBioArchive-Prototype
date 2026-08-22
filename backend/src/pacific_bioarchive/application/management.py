"""Bulk manual-tag mutation and complete idempotent media deletion."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from pacific_bioarchive.domain.media import MediaRecord
from pacific_bioarchive.domain.repositories import (
    DedupRepository,
    MediaRepository,
    RecordNotFoundError,
)
from pacific_bioarchive.domain.storage import ObjectStorage
from pacific_bioarchive.ml.labels import normalize_tag

from .references import normalize_s3_reference


class ManagementValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class AuthorizationError(PermissionError):
    pass


class RecordNotificationPublisher(Protocol):
    def publish_for_record(
        self, record: MediaRecord, *, tags: Iterable[str] | None = None
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class TagEditResult:
    records: tuple[MediaRecord, ...]
    changed_tags: dict[str, tuple[str, ...]]
    operation: int


@dataclass(frozen=True, slots=True)
class DeleteOutcome:
    identifier: str
    file_id: str | None
    deleted: bool
    already_absent: bool = False
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class BulkDeleteResult:
    outcomes: tuple[DeleteOutcome, ...]

    @property
    def complete(self) -> bool:
        return all(outcome.error_code is None for outcome in self.outcomes)


class MediaManagementService:
    def __init__(
        self,
        *,
        media_repository: MediaRepository,
        dedup_repository: DedupRepository,
        storage: ObjectStorage,
        bucket_name: str,
        notification_publisher: RecordNotificationPublisher | None = None,
        max_bulk_items: int = 25,
        max_tags: int = 20,
        max_tag_length: int = 50,
    ) -> None:
        self._media = media_repository
        self._dedup = dedup_repository
        self._storage = storage
        self._bucket_name = bucket_name
        self._notifications = notification_publisher
        self._max_bulk_items = max_bulk_items
        self._max_tags = max_tags
        self._max_tag_length = max_tag_length

    def _identifiers(
        self, *, urls: Iterable[str] = (), file_ids: Iterable[str] = ()
    ) -> tuple[str, ...]:
        values = tuple(dict.fromkeys([*(str(value) for value in urls), *(str(value) for value in file_ids)]))
        if not values:
            raise ManagementValidationError(
                "NO_MEDIA_IDENTIFIERS", "At least one URL or file_id is required"
            )
        if len(values) > self._max_bulk_items:
            raise ManagementValidationError(
                "TOO_MANY_MEDIA_ITEMS",
                f"At most {self._max_bulk_items} media items can be modified at once",
            )
        if any(not value.strip() for value in values):
            raise ManagementValidationError("INVALID_MEDIA_IDENTIFIER", "Identifiers cannot be empty")
        return values

    def _index(self) -> tuple[dict[str, MediaRecord], dict[str, MediaRecord]]:
        records = self._media.list_all()
        by_id = {record.file_id: record for record in records}
        by_key: dict[str, MediaRecord] = {}
        for record in records:
            by_key[record.original_key] = record
            if record.thumbnail_key:
                by_key[record.thumbnail_key] = record
        return by_id, by_key

    def _resolve(self, identifier: str, by_id: dict[str, MediaRecord], by_key: dict[str, MediaRecord]) -> MediaRecord | None:
        if identifier in by_id:
            return by_id[identifier]
        if "://" not in identifier and "/" not in identifier:
            return None
        key = normalize_s3_reference(
            identifier,
            bucket_name=self._bucket_name,
            allowed_prefixes=("originals/", "thumbnails/"),
        )
        return by_key.get(key)

    @staticmethod
    def _authorize(record: MediaRecord, actor_sub: str) -> None:
        if record.owner_sub != actor_sub:
            raise AuthorizationError("Only the uploader can modify or delete this media")

    def edit_tags(
        self,
        *,
        actor_sub: str,
        tags: Iterable[str],
        operation: int,
        urls: Iterable[str] = (),
        file_ids: Iterable[str] = (),
    ) -> TagEditResult:
        if isinstance(operation, bool) or operation not in {0, 1}:
            raise ManagementValidationError("INVALID_OPERATION", "operation must be 1 (add) or 0 (remove)")
        raw_tags = tuple(tags)
        if not raw_tags or len(raw_tags) > self._max_tags:
            raise ManagementValidationError(
                "INVALID_TAGS", f"Provide between 1 and {self._max_tags} tags"
            )
        normalized_tags: set[str] = set()
        for raw_tag in raw_tags:
            if not isinstance(raw_tag, str):
                raise ManagementValidationError("INVALID_TAG", "Every tag must be a string")
            tag = normalize_tag(raw_tag)
            if not tag or len(tag) > self._max_tag_length:
                raise ManagementValidationError(
                    "INVALID_TAG", f"Tags must contain 1–{self._max_tag_length} normalized characters"
                )
            normalized_tags.add(tag)

        identifiers = self._identifiers(urls=urls, file_ids=file_ids)
        by_id, by_key = self._index()
        resolved: list[MediaRecord] = []
        for identifier in identifiers:
            record = self._resolve(identifier, by_id, by_key)
            if record is None:
                raise RecordNotFoundError(f"Media not found: {identifier}")
            if record not in resolved:
                resolved.append(record)
        for record in resolved:
            self._authorize(record, actor_sub)

        updated_records: list[MediaRecord] = []
        changes: dict[str, tuple[str, ...]] = {}
        for record in resolved:
            current = set(record.manual_tags)
            next_tags = current.union(normalized_tags) if operation == 1 else current.difference(normalized_tags)
            changed = next_tags.difference(current) if operation == 1 else current.difference(next_tags)
            if changed:
                updated = record.with_manual_tags(next_tags)
                self._media.save(updated, expected_version=record.version)
            else:
                updated = record
            if operation == 1 and self._notifications is not None:
                self._notifications.publish_for_record(updated, tags=normalized_tags)
            updated_records.append(updated)
            changes[record.file_id] = tuple(sorted(changed))
        return TagEditResult(tuple(updated_records), changes, operation)

    def delete_media(
        self,
        *,
        actor_sub: str,
        urls: Iterable[str] = (),
        file_ids: Iterable[str] = (),
    ) -> BulkDeleteResult:
        identifiers = self._identifiers(urls=urls, file_ids=file_ids)
        by_id, by_key = self._index()
        resolved_pairs: list[tuple[str, MediaRecord | None]] = [
            (identifier, self._resolve(identifier, by_id, by_key))
            for identifier in identifiers
        ]
        for _, record in resolved_pairs:
            if record is not None:
                self._authorize(record, actor_sub)

        outcomes: list[DeleteOutcome] = []
        processed: set[str] = set()
        for identifier, record in resolved_pairs:
            if record is None:
                outcomes.append(DeleteOutcome(identifier, None, False, already_absent=True))
                continue
            if record.file_id in processed:
                outcomes.append(DeleteOutcome(identifier, record.file_id, False, already_absent=True))
                continue
            processed.add(record.file_id)
            try:
                self._storage.delete(record.original_key)
                if record.thumbnail_key:
                    self._storage.delete(record.thumbnail_key)
                self._media.delete(record.file_id)
                self._dedup.remove(record.checksum, file_id=record.file_id)
            # Every adapter failure must become a per-item incomplete outcome;
            # the API must never report a destructive batch as fully complete.
            except Exception:  # noqa: BLE001
                outcomes.append(
                    DeleteOutcome(
                        identifier,
                        record.file_id,
                        False,
                        error_code="DELETE_INCOMPLETE",
                    )
                )
            else:
                outcomes.append(DeleteOutcome(identifier, record.file_id, True))
        return BulkDeleteResult(tuple(outcomes))
