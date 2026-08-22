"""S3 ObjectCreated Lambda entry point for asynchronous media processing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote_plus

from pacific_bioarchive.application.processing import MediaProcessingService


class StorageEventError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class StorageEvent:
    bucket_name: str
    object_key: str


def parse_s3_created_events(event: object) -> tuple[StorageEvent, ...]:
    if not isinstance(event, dict) or not isinstance(event.get("Records"), list):
        raise StorageEventError("INVALID_S3_EVENT", "S3 event Records are required")
    if not event["Records"]:
        raise StorageEventError("INVALID_S3_EVENT", "S3 event Records cannot be empty")
    parsed: list[StorageEvent] = []
    for record in event["Records"]:
        try:
            source = record["eventSource"]
            name = record["eventName"]
            bucket = record["s3"]["bucket"]["name"]
            encoded_key = record["s3"]["object"]["key"]
        except (KeyError, TypeError) as exc:
            raise StorageEventError("INVALID_S3_EVENT", "S3 event fields are missing") from exc
        if source != "aws:s3" or not str(name).startswith("ObjectCreated:"):
            raise StorageEventError(
                "UNSUPPORTED_S3_EVENT", "Only aws:s3 ObjectCreated events are supported"
            )
        if not str(bucket).strip() or not str(encoded_key).strip():
            raise StorageEventError("INVALID_S3_EVENT", "S3 bucket and object key are required")
        parsed.append(StorageEvent(str(bucket), unquote_plus(str(encoded_key))))
    return tuple(parsed)


def handle_s3_event(
    event: object,
    *,
    processor: MediaProcessingService,
    expected_bucket: str,
) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for created in parse_s3_created_events(event):
        if created.bucket_name != expected_bucket:
            raise StorageEventError("WRONG_S3_BUCKET", "S3 event came from an unexpected bucket")
        results.append(processor.process_object(created.object_key).to_dict())
    return {"processed": len(results), "results": results}


_processor: MediaProcessingService | None = None


def _build_processor() -> MediaProcessingService:
    import boto3

    from pacific_bioarchive.media.video_processing import (
        OpenCVFrameSampler,
        VideoInferenceService,
    )
    from pacific_bioarchive.ml.runtime import RuntimeConfig, build_inference_service
    from pacific_bioarchive.persistence.dynamodb import (
        DynamoDedupRepository,
        DynamoMediaRepository,
    )
    from pacific_bioarchive.persistence.s3 import S3ObjectStorage

    bucket = os.environ["PBA_MEDIA_BUCKET"]
    dynamodb = boto3.resource("dynamodb")
    inference = build_inference_service(RuntimeConfig.from_environment())
    return MediaProcessingService(
        media_repository=DynamoMediaRepository(dynamodb.Table(os.environ["PBA_MEDIA_TABLE"])),
        dedup_repository=DynamoDedupRepository(dynamodb.Table(os.environ["PBA_DEDUP_TABLE"])),
        storage=S3ObjectStorage(boto3.client("s3"), bucket_name=bucket),
        image_inference=inference,
        video_inference=VideoInferenceService(
            sampler=OpenCVFrameSampler(
                max_samples=int(os.getenv("PBA_MAX_VIDEO_SAMPLES", "30"))
            ),
            image_inference=inference,
        ),
    )


def lambda_handler(event: object, context: Any) -> dict[str, object]:
    del context
    global _processor
    if _processor is None:
        _processor = _build_processor()
    return handle_s3_event(
        event,
        processor=_processor,
        expected_bucket=os.environ["PBA_MEDIA_BUCKET"],
    )
