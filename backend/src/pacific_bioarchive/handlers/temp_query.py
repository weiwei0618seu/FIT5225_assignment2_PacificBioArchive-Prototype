"""ML-container Lambda route for ephemeral query-image inference."""

from __future__ import annotations

import os
import re
from typing import Any

from pacific_bioarchive.application.temp_queries import TemporaryQueryResult
from pacific_bioarchive.handlers.http import HttpApiError, HttpRequest, dispatch_http

TEMP_ROUTE = re.compile(r"^/queries/file/([^/]+)$")
_service: Any | None = None
_storage: Any | None = None


def _record_payload(record: Any, storage: Any) -> dict[str, object]:
    payload = {
        "file_id": record.file_id,
        "filename": record.filename,
        "file_type": record.file_type.value,
        "species_counts": dict(record.species_counts or {}),
        "auto_tags": list(record.auto_tags),
        "manual_tags": list(record.manual_tags),
        "all_tags": list(record.all_tags),
        "processing_status": record.processing_status.value,
        "model_version": record.model_version,
        "created_at": record.created_at,
        "original_url": storage.create_presigned_get(record.original_key, expires_in=900),
        "thumbnail_url": (
            storage.create_presigned_get(record.thumbnail_key, expires_in=900)
            if record.thumbnail_key
            else None
        ),
    }
    return payload


def handle_with_service(
    event: object, *, service: Any, storage: Any
) -> dict[str, object]:
    def route(request: HttpRequest) -> tuple[int, object]:
        match = TEMP_ROUTE.fullmatch(request.path)
        if request.method != "POST" or match is None:
            raise HttpApiError(404, "ROUTE_NOT_FOUND", "The API route was not found")
        result: TemporaryQueryResult = service.execute(
            actor_sub=request.auth.subject,
            query_id=match.group(1),
            temp_reference=str(request.body.get("temp_key", "")),
            limit=int(request.query.get("limit", "50")),
        )
        return 200, {
            "detected_species_counts": dict(result.inference.species_counts),
            "model_version": result.inference.model_version,
            "media": [
                _record_payload(record, storage) for record in result.matches.records
            ],
            "total": result.matches.total,
            "truncated": result.matches.truncated,
        }

    return dispatch_http(event, route)


def _build_service() -> tuple[Any, Any]:
    import boto3

    from pacific_bioarchive.application.queries import MediaQueryService
    from pacific_bioarchive.application.temp_queries import TemporaryQueryService
    from pacific_bioarchive.ml.runtime import RuntimeConfig, build_inference_service
    from pacific_bioarchive.persistence.dynamodb import DynamoMediaRepository
    from pacific_bioarchive.persistence.s3 import S3ObjectStorage

    bucket = os.environ["PBA_MEDIA_BUCKET"]
    storage = S3ObjectStorage(boto3.client("s3"), bucket_name=bucket)
    media = DynamoMediaRepository(
        boto3.resource("dynamodb").Table(os.environ["PBA_MEDIA_TABLE"])
    )
    service = TemporaryQueryService(
        storage=storage,
        query_service=MediaQueryService(media, bucket_name=bucket),
        image_inference=build_inference_service(RuntimeConfig.from_environment()),
        bucket_name=bucket,
    )
    return service, storage


def lambda_handler(event: object, context: Any) -> dict[str, object]:
    del context
    global _service, _storage
    if _service is None or _storage is None:
        _service, _storage = _build_service()
    return handle_with_service(event, service=_service, storage=_storage)
