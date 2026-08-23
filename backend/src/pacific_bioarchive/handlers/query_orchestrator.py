"""Asynchronous bridge between S3 query uploads and the supplied ML Lambda."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import PurePosixPath
from typing import Any

from pacific_bioarchive.domain.query_jobs import TemporaryQueryStatus
from pacific_bioarchive.domain.repositories import TemporaryQueryRepository
from pacific_bioarchive.handlers.media_processor import (
    StorageEventError,
    parse_s3_created_events,
)

LOGGER = logging.getLogger(__name__)
ACTOR_HASH_PATTERN = re.compile(r"^[0-9a-f]{32}$")
ERROR_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


class TemporaryQueryOrchestrationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _query_id_from_key(key: str) -> str:
    parts = PurePosixPath(key).parts
    if (
        len(parts) != 4
        or parts[0] != "query-temp"
        or not ACTOR_HASH_PATTERN.fullmatch(parts[1])
        or not parts[2]
        or any(token in parts[2] for token in ("/", "\\", ".."))
        or not parts[3]
    ):
        raise TemporaryQueryOrchestrationError(
            "INVALID_TEMP_QUERY_KEY", "Temporary query object key is invalid"
        )
    return parts[2]


def _invoke_event(*, owner_sub: str, query_id: str, temp_key: str) -> bytes:
    return json.dumps(
        {
            "version": "2.0",
            "rawPath": f"/queries/file/{query_id}",
            "body": json.dumps({"temp_key": temp_key}, separators=(",", ":")),
            "isBase64Encoded": False,
            "queryStringParameters": None,
            "requestContext": {
                "requestId": f"temporary-query-{query_id}",
                "http": {"method": "POST", "path": f"/queries/file/{query_id}"},
                "authorizer": {"jwt": {"claims": {"sub": owner_sub}}},
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _read_lambda_response(response: dict[str, object]) -> tuple[int, dict[str, object]]:
    payload_stream = response.get("Payload")
    if payload_stream is None or not hasattr(payload_stream, "read"):
        raise TemporaryQueryOrchestrationError(
            "TEMP_QUERY_INVALID_RESPONSE", "ML Lambda response payload is missing"
        )
    try:
        outer = json.loads(payload_stream.read().decode("utf-8"))
        status_code = int(outer["statusCode"])
        body = json.loads(outer["body"])
    except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TemporaryQueryOrchestrationError(
            "TEMP_QUERY_INVALID_RESPONSE", "ML Lambda response payload is invalid"
        ) from exc
    if not isinstance(body, dict):
        raise TemporaryQueryOrchestrationError(
            "TEMP_QUERY_INVALID_RESPONSE", "ML Lambda response body is invalid"
        )
    if response.get("FunctionError"):
        return 500, {"error": {"code": "TEMP_QUERY_PROCESSING_FAILED"}}
    return status_code, body


def _safe_error_code(body: dict[str, object]) -> str:
    error = body.get("error")
    raw = error.get("code") if isinstance(error, dict) else None
    code = str(raw or "TEMP_QUERY_PROCESSING_FAILED")
    return code if ERROR_CODE_PATTERN.fullmatch(code) else "TEMP_QUERY_PROCESSING_FAILED"


def _success_values(
    body: dict[str, object],
) -> tuple[dict[str, int], str, tuple[str, ...], int, bool]:
    raw_counts = body.get("detected_species_counts")
    raw_media = body.get("media")
    if not isinstance(raw_counts, dict) or not isinstance(raw_media, list):
        raise TemporaryQueryOrchestrationError(
            "TEMP_QUERY_INVALID_RESPONSE", "ML Lambda result fields are invalid"
        )
    counts: dict[str, int] = {}
    for tag, value in raw_counts.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise TemporaryQueryOrchestrationError(
                "TEMP_QUERY_INVALID_RESPONSE", "Detected species counts are invalid"
            )
        counts[str(tag)] = value
    model_version = str(body.get("model_version") or "").strip()
    if not model_version:
        raise TemporaryQueryOrchestrationError(
            "TEMP_QUERY_INVALID_RESPONSE", "ML model version is missing"
        )
    file_ids: list[str] = []
    for item in raw_media:
        if not isinstance(item, dict) or not str(item.get("file_id") or "").strip():
            raise TemporaryQueryOrchestrationError(
                "TEMP_QUERY_INVALID_RESPONSE", "ML result media identifiers are invalid"
            )
        file_id = str(item["file_id"]).strip()
        if file_id not in file_ids:
            file_ids.append(file_id)
    total = body.get("total")
    truncated = body.get("truncated")
    if (
        isinstance(total, bool)
        or not isinstance(total, int)
        or total < len(file_ids)
        or not isinstance(truncated, bool)
    ):
        raise TemporaryQueryOrchestrationError(
            "TEMP_QUERY_INVALID_RESPONSE", "ML result pagination fields are invalid"
        )
    return counts, model_version, tuple(file_ids), total, truncated


def handle_s3_event(
    event: object,
    *,
    jobs: TemporaryQueryRepository,
    lambda_client: Any,
    function_name: str,
    expected_bucket: str,
) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for created in parse_s3_created_events(event):
        if created.bucket_name != expected_bucket:
            raise StorageEventError(
                "WRONG_S3_BUCKET", "S3 event came from an unexpected bucket"
            )
        query_id = _query_id_from_key(created.object_key)
        job = jobs.get(query_id)
        if job is None or job.temp_key != created.object_key:
            raise TemporaryQueryOrchestrationError(
                "TEMP_QUERY_JOB_NOT_FOUND", "Temporary query job was not found"
            )
        if job.status in {TemporaryQueryStatus.READY, TemporaryQueryStatus.FAILED}:
            results.append(
                {"query_id": query_id, "processing_status": job.status.value, "replayed": True}
            )
            continue

        active = job.mark_processing()
        if active.version != job.version:
            jobs.save(active, expected_version=job.version)

        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=_invoke_event(
                owner_sub=active.owner_sub,
                query_id=active.query_id,
                temp_key=active.temp_key,
            ),
        )
        try:
            status_code, body = _read_lambda_response(response)
            if status_code == 200:
                counts, model_version, file_ids, total, truncated = _success_values(body)
                completed = active.mark_ready(
                    species_counts=counts,
                    model_version=model_version,
                    matched_file_ids=file_ids,
                    total=total,
                    truncated=truncated,
                )
            else:
                completed = active.mark_failed(_safe_error_code(body))
        except TemporaryQueryOrchestrationError as exc:
            completed = active.mark_failed(exc.code)

        jobs.save(completed, expected_version=active.version)
        if completed.status == TemporaryQueryStatus.FAILED:
            LOGGER.error("Temporary query failed with safe code %s", completed.error_code)
        results.append(
            {
                "query_id": query_id,
                "processing_status": completed.status.value,
                "error_code": completed.error_code,
            }
        )
    return {"processed": len(results), "results": results}


_jobs: TemporaryQueryRepository | None = None
_lambda_client: Any | None = None


def _build_dependencies() -> tuple[TemporaryQueryRepository, Any]:
    import boto3
    from botocore.config import Config

    from pacific_bioarchive.persistence.query_jobs import (
        DynamoTemporaryQueryRepository,
    )

    dynamodb = boto3.resource("dynamodb")
    repository = DynamoTemporaryQueryRepository(
        dynamodb.Table(os.environ["PBA_TEMP_QUERIES_TABLE"])
    )
    client = boto3.client(
        "lambda",
        config=Config(
            connect_timeout=5,
            read_timeout=310,
            retries={"max_attempts": 0},
        ),
    )
    return repository, client


def lambda_handler(event: object, context: Any) -> dict[str, object]:
    del context
    global _jobs, _lambda_client
    if _jobs is None or _lambda_client is None:
        _jobs, _lambda_client = _build_dependencies()
    return handle_s3_event(
        event,
        jobs=_jobs,
        lambda_client=_lambda_client,
        function_name=os.environ["PBA_TEMP_QUERY_FUNCTION"],
        expected_bucket=os.environ["PBA_MEDIA_BUCKET"],
    )
