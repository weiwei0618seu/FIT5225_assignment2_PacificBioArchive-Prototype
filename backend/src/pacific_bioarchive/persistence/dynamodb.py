"""Boto3 DynamoDB resource adapters with optimistic/conditional writes."""

from __future__ import annotations

from decimal import Decimal
from collections.abc import Callable
from typing import Any, Sequence

from pacific_bioarchive.domain.media import MediaRecord, ProcessingStatus
from pacific_bioarchive.domain.repositories import (
    ConflictError,
    DedupReservation,
    DuplicateFileError,
)
from pacific_bioarchive.media.validation import MediaType


def _is_conditional_failure(exc: Exception) -> bool:
    response = getattr(exc, "response", {})
    return response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


def to_dynamo(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: to_dynamo(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_dynamo(item) for item in value]
    return value


def from_dynamo(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {key: from_dynamo(item) for key, item in value.items()}
    if isinstance(value, list):
        return [from_dynamo(item) for item in value]
    return value


def media_to_item(record: MediaRecord) -> dict[str, Any]:
    item = {
        "file_id": record.file_id,
        "owner_sub": record.owner_sub,
        "filename": record.filename,
        "checksum": record.checksum,
        "file_type": record.file_type.value,
        "content_type": record.content_type,
        "size_bytes": record.size_bytes,
        "original_key": record.original_key,
        "species_counts": dict(record.species_counts or {}),
        "auto_tags": list(record.auto_tags),
        "manual_tags": list(record.manual_tags),
        "all_tags": list(record.all_tags),
        "detections": list(record.detections),
        "processing_status": record.processing_status.value,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "version": record.version,
    }
    optional = {
        "thumbnail_key": record.thumbnail_key,
        "video_samples": record.video_samples,
        "error_code": record.error_code,
    }
    item.update({key: value for key, value in optional.items() if value is not None})
    return to_dynamo(item)


def media_from_item(raw_item: dict[str, Any]) -> MediaRecord:
    item = from_dynamo(raw_item)
    return MediaRecord(
        file_id=item["file_id"],
        owner_sub=item["owner_sub"],
        filename=item["filename"],
        checksum=item["checksum"],
        file_type=MediaType(item["file_type"]),
        content_type=item["content_type"],
        size_bytes=int(item["size_bytes"]),
        original_key=item["original_key"],
        thumbnail_key=item.get("thumbnail_key"),
        species_counts=item.get("species_counts", {}),
        manual_tags=tuple(item.get("manual_tags", [])),
        detections=tuple(item.get("detections", [])),
        video_samples=item.get("video_samples"),
        processing_status=ProcessingStatus(item["processing_status"]),
        error_code=item.get("error_code"),
        created_at=item["created_at"],
        updated_at=item["updated_at"],
        version=int(item["version"]),
    )


class DynamoMediaRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def create(self, record: MediaRecord) -> None:
        try:
            self._table.put_item(
                Item=media_to_item(record),
                ConditionExpression="attribute_not_exists(file_id)",
            )
        except Exception as exc:
            if _is_conditional_failure(exc):
                raise ConflictError(f"Media {record.file_id} already exists") from exc
            raise

    def get(self, file_id: str) -> MediaRecord | None:
        response = self._table.get_item(Key={"file_id": file_id}, ConsistentRead=True)
        item = response.get("Item")
        return media_from_item(item) if item else None

    def save(self, record: MediaRecord, *, expected_version: int) -> None:
        try:
            self._table.put_item(
                Item=media_to_item(record),
                ConditionExpression="#version = :expected",
                ExpressionAttributeNames={"#version": "version"},
                ExpressionAttributeValues={":expected": expected_version},
            )
        except Exception as exc:
            if _is_conditional_failure(exc):
                raise ConflictError(f"Media {record.file_id} version conflict") from exc
            raise

    def list_all(self) -> Sequence[MediaRecord]:
        records: list[MediaRecord] = []
        exclusive_start_key: dict[str, Any] | None = None
        while True:
            kwargs = {"ExclusiveStartKey": exclusive_start_key} if exclusive_start_key else {}
            response = self._table.scan(**kwargs)
            records.extend(media_from_item(item) for item in response.get("Items", []))
            exclusive_start_key = response.get("LastEvaluatedKey")
            if not exclusive_start_key:
                break
        return tuple(records)

    def delete(self, file_id: str) -> MediaRecord | None:
        response = self._table.delete_item(
            Key={"file_id": file_id}, ReturnValues="ALL_OLD"
        )
        attributes = response.get("Attributes")
        return media_from_item(attributes) if attributes else None


class DynamoDedupRepository:
    def __init__(self, table: Any, *, epoch_seconds: Callable[[], int] | None = None) -> None:
        import time

        self._table = table
        self._epoch_seconds = epoch_seconds or (lambda: int(time.time()))

    def reserve(self, reservation: DedupReservation) -> None:
        if reservation.status != "RESERVED" or reservation.expires_at is None:
            raise ValueError("New checksum entries must be expiring RESERVED entries")
        item = {
            "checksum": reservation.checksum,
            "file_id": reservation.file_id,
            "owner_sub": reservation.owner_sub,
            "status": reservation.status,
            "expires_at": reservation.expires_at,
        }
        try:
            self._table.put_item(
                Item=item,
                ConditionExpression=(
                    "attribute_not_exists(checksum) OR "
                    "(#status = :reserved AND expires_at < :now)"
                ),
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":reserved": "RESERVED",
                    ":now": self._epoch_seconds(),
                },
            )
        except Exception as exc:
            if _is_conditional_failure(exc):
                existing = self.get(reservation.checksum)
                raise DuplicateFileError(
                    reservation.checksum, existing.file_id if existing else None
                ) from exc
            raise

    def get(self, checksum: str) -> DedupReservation | None:
        response = self._table.get_item(Key={"checksum": checksum}, ConsistentRead=True)
        item = response.get("Item")
        if not item:
            return None
        return DedupReservation(
            checksum=item["checksum"],
            file_id=item["file_id"],
            owner_sub=item["owner_sub"],
            status=item["status"],
            expires_at=int(item["expires_at"]) if "expires_at" in item else None,
        )

    def commit(self, checksum: str, *, file_id: str) -> None:
        try:
            self._table.update_item(
                Key={"checksum": checksum},
                UpdateExpression="SET #status = :committed REMOVE expires_at",
                ConditionExpression="file_id = :file_id AND #status = :reserved",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":committed": "COMMITTED",
                    ":reserved": "RESERVED",
                    ":file_id": file_id,
                },
            )
        except Exception as exc:
            if _is_conditional_failure(exc):
                raise ConflictError("Checksum reservation commit conflict") from exc
            raise

    def release(self, checksum: str, *, file_id: str) -> None:
        try:
            self._table.delete_item(
                Key={"checksum": checksum},
                ConditionExpression="file_id = :file_id AND #status = :reserved",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":file_id": file_id,
                    ":reserved": "RESERVED",
                },
            )
        except Exception as exc:
            if _is_conditional_failure(exc):
                existing = self.get(checksum)
                if existing is None:
                    return
                raise ConflictError("Checksum reservation release conflict") from exc
            raise

    def remove(self, checksum: str, *, file_id: str) -> None:
        try:
            self._table.delete_item(
                Key={"checksum": checksum},
                ConditionExpression="file_id = :file_id",
                ExpressionAttributeValues={":file_id": file_id},
            )
        except Exception as exc:
            if _is_conditional_failure(exc):
                existing = self.get(checksum)
                if existing is None:
                    return
                raise ConflictError("Checksum deletion conflict") from exc
            raise
