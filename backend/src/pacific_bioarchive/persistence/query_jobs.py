"""In-memory and DynamoDB adapters for short-lived query jobs."""

from __future__ import annotations

from threading import RLock
from typing import Any

from pacific_bioarchive.domain.query_jobs import (
    TemporaryQueryJob,
    TemporaryQueryStatus,
)
from pacific_bioarchive.domain.repositories import ConflictError
from pacific_bioarchive.persistence.dynamodb import (
    _is_conditional_failure,
    from_dynamo,
    to_dynamo,
)


def temporary_query_job_to_item(job: TemporaryQueryJob) -> dict[str, object]:
    return to_dynamo(
        {
            "query_id": job.query_id,
            "owner_sub": job.owner_sub,
            "temp_key": job.temp_key,
            "status": job.status.value,
            "species_counts": dict(job.species_counts or {}),
            "model_version": job.model_version,
            "matched_file_ids": list(job.matched_file_ids),
            "total": job.total,
            "truncated": job.truncated,
            "error_code": job.error_code,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "expires_at": job.expires_at,
            "version": job.version,
        }
    )


def temporary_query_job_from_item(raw_item: dict[str, Any]) -> TemporaryQueryJob:
    item = from_dynamo(raw_item)
    return TemporaryQueryJob(
        query_id=item["query_id"],
        owner_sub=item["owner_sub"],
        temp_key=item["temp_key"],
        status=TemporaryQueryStatus(item["status"]),
        species_counts=item.get("species_counts", {}),
        model_version=item.get("model_version"),
        matched_file_ids=tuple(item.get("matched_file_ids", [])),
        total=int(item.get("total", 0)),
        truncated=bool(item.get("truncated", False)),
        error_code=item.get("error_code"),
        created_at=item["created_at"],
        updated_at=item["updated_at"],
        expires_at=int(item["expires_at"]),
        version=int(item["version"]),
    )


class InMemoryTemporaryQueryRepository:
    def __init__(self) -> None:
        self._items: dict[str, TemporaryQueryJob] = {}
        self._lock = RLock()

    def create(self, job: TemporaryQueryJob) -> None:
        with self._lock:
            if job.query_id in self._items:
                raise ConflictError(f"Temporary query {job.query_id} already exists")
            self._items[job.query_id] = job

    def get(self, query_id: str) -> TemporaryQueryJob | None:
        with self._lock:
            return self._items.get(query_id)

    def save(self, job: TemporaryQueryJob, *, expected_version: int) -> None:
        with self._lock:
            current = self._items.get(job.query_id)
            if current is None or current.version != expected_version:
                raise ConflictError(f"Temporary query {job.query_id} version conflict")
            if job.version <= expected_version:
                raise ConflictError("Saved temporary query version must increase")
            self._items[job.query_id] = job


class DynamoTemporaryQueryRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def create(self, job: TemporaryQueryJob) -> None:
        try:
            self._table.put_item(
                Item=temporary_query_job_to_item(job),
                ConditionExpression="attribute_not_exists(query_id)",
            )
        except Exception as exc:
            if _is_conditional_failure(exc):
                raise ConflictError(
                    f"Temporary query {job.query_id} already exists"
                ) from exc
            raise

    def get(self, query_id: str) -> TemporaryQueryJob | None:
        response = self._table.get_item(Key={"query_id": query_id}, ConsistentRead=True)
        item = response.get("Item")
        return temporary_query_job_from_item(item) if item else None

    def save(self, job: TemporaryQueryJob, *, expected_version: int) -> None:
        try:
            self._table.put_item(
                Item=temporary_query_job_to_item(job),
                ConditionExpression="#version = :expected",
                ExpressionAttributeNames={"#version": "version"},
                ExpressionAttributeValues={":expected": expected_version},
            )
        except Exception as exc:
            if _is_conditional_failure(exc):
                raise ConflictError(
                    f"Temporary query {job.query_id} version conflict"
                ) from exc
            raise
