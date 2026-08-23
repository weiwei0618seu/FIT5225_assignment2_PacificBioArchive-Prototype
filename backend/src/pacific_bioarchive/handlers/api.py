"""Authenticated REST routes for the lightweight core API Lambda."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any

from pacific_bioarchive.application.management import MediaManagementService
from pacific_bioarchive.application.notifications import NotificationService
from pacific_bioarchive.application.queries import MediaQueryService, QueryResult
from pacific_bioarchive.application.temp_queries import TemporaryQueryService
from pacific_bioarchive.application.uploads import UploadService
from pacific_bioarchive.domain.media import MediaRecord, ProcessingStatus
from pacific_bioarchive.domain.query_jobs import TemporaryQueryJob, TemporaryQueryStatus
from pacific_bioarchive.domain.repositories import (
    MediaRepository,
    RecordNotFoundError,
    TemporaryQueryRepository,
)
from pacific_bioarchive.domain.storage import PrivateObjectStorage
from pacific_bioarchive.handlers.http import (
    HttpApiError,
    HttpRequest,
    dispatch_http,
    require_list,
    require_object,
)

FILE_ROUTE = re.compile(r"^/media/([^/]+)$")
TEMP_QUERY_ROUTE = re.compile(r"^/queries/file/([^/]+)$")


@dataclass(frozen=True, slots=True)
class CoreApiServices:
    upload: UploadService
    media_repository: MediaRepository
    storage: PrivateObjectStorage
    queries: MediaQueryService
    management: MediaManagementService
    notifications: NotificationService
    temp_queries: TemporaryQueryService
    temp_query_jobs: TemporaryQueryRepository


class CoreApiApplication:
    def __init__(self, services: CoreApiServices, *, version: str = "0.1.0") -> None:
        self._services = services
        self._version = version

    def handle(self, event: object) -> dict[str, object]:
        return dispatch_http(event, self._route)

    def _route(self, request: HttpRequest) -> tuple[int, object]:
        route = (request.method, request.path)
        if route == ("GET", "/health"):
            return 200, {"status": "ok", "version": self._version}
        if route == ("POST", "/uploads/init"):
            return self._upload(request)
        if request.method == "GET" and (match := FILE_ROUTE.fullmatch(request.path)):
            return self._get_media(request, match.group(1))
        if route == ("POST", "/queries/tags"):
            requirements = require_object(request.body, "requirements")
            result = self._services.queries.find_by_requirements(
                requirements, limit=self._limit(request)
            )
            return 200, self._query_payload(result)
        if route == ("GET", "/queries/species"):
            result = self._services.queries.find_by_species(
                request.query.get("tag", ""), limit=self._limit(request)
            )
            return 200, self._query_payload(result)
        if route == ("POST", "/queries/thumbnail"):
            record = self._services.queries.find_by_thumbnail(
                str(request.body.get("thumbnail_url", ""))
            )
            if record is None:
                raise RecordNotFoundError("Thumbnail was not found")
            return 200, {
                "file_id": record.file_id,
                "original_url": self._services.storage.create_presigned_get(
                    record.original_key, expires_in=900
                ),
            }
        if route == ("POST", "/queries/file/init"):
            return self._temp_init(request)
        if request.method in {"GET", "POST"} and (
            match := TEMP_QUERY_ROUTE.fullmatch(request.path)
        ):
            return self._temp_status(request, match.group(1))
        if route == ("POST", "/media/tags"):
            return self._edit_tags(request)
        if route == ("POST", "/media/delete"):
            return self._delete(request)
        if request.path == "/notifications/subscription":
            return self._subscription(request)
        raise HttpApiError(404, "ROUTE_NOT_FOUND", "The API route was not found")

    def _upload(self, request: HttpRequest) -> tuple[int, object]:
        ticket = self._services.upload.initiate(
            actor_sub=request.auth.subject,
            filename=str(request.body["filename"]),
            content_type=str(request.body["content_type"]),
            size_bytes=request.body["size_bytes"],
            checksum=str(request.body["checksum"]),
        )
        return 201, {
            "file_id": ticket.file_id,
            "object_key": ticket.object_key,
            "upload_url": ticket.upload.url,
            "required_headers": ticket.upload.headers,
            "expires_in": ticket.upload.expires_in,
            "processing_status": ticket.record.processing_status.value,
        }

    def _get_media(self, request: HttpRequest, file_id: str) -> tuple[int, object]:
        record = self._services.media_repository.get(file_id)
        if record is None or (
            record.processing_status != ProcessingStatus.READY
            and record.owner_sub != request.auth.subject
        ):
            raise RecordNotFoundError(file_id)
        return 200, self._record_payload(record)

    def _temp_init(self, request: HttpRequest) -> tuple[int, object]:
        ticket = self._services.temp_queries.initiate(
            actor_sub=request.auth.subject,
            filename=str(request.body["filename"]),
            content_type=str(request.body["content_type"]),
            size_bytes=request.body["size_bytes"],
            checksum=str(request.body["checksum"]),
        )
        self._services.temp_query_jobs.create(
            TemporaryQueryJob(
                query_id=ticket.query_id,
                owner_sub=request.auth.subject,
                temp_key=ticket.temp_key,
                expires_at=int(time.time()) + 3600,
            )
        )
        return 201, {
            "query_id": ticket.query_id,
            "temp_key": ticket.temp_key,
            "upload_url": ticket.upload.url,
            "required_headers": ticket.upload.headers,
            "expires_in": ticket.upload.expires_in,
        }

    def _temp_status(self, request: HttpRequest, query_id: str) -> tuple[int, object]:
        normalized_query_id = query_id.strip()
        if not normalized_query_id or any(
            token in normalized_query_id for token in ("/", "\\", "..")
        ):
            raise HttpApiError(400, "INVALID_QUERY_ID", "query_id is invalid")
        job = self._services.temp_query_jobs.get(normalized_query_id)
        if job is None or job.owner_sub != request.auth.subject:
            raise HttpApiError(
                404, "TEMP_QUERY_NOT_FOUND", "The temporary query was not found"
            )
        if job.status in {
            TemporaryQueryStatus.AWAITING_UPLOAD,
            TemporaryQueryStatus.PROCESSING,
        }:
            return 202, {
                "query_id": job.query_id,
                "processing_status": job.status.value,
                "retry_after_seconds": 3,
            }
        if job.status == TemporaryQueryStatus.FAILED:
            messages = {
                "NO_SPECIES_DETECTED": "No species were detected in the temporary query image",
                "TEMP_QUERY_CHECKSUM_MISMATCH": "The temporary query upload failed integrity checks",
            }
            code = job.error_code or "TEMP_QUERY_PROCESSING_FAILED"
            raise HttpApiError(
                422,
                code,
                messages.get(code, "The temporary query image could not be analysed"),
            )

        records = []
        for file_id in job.matched_file_ids:
            record = self._services.media_repository.get(file_id)
            if record is not None and record.processing_status == ProcessingStatus.READY:
                records.append(record)
        payload = self._query_payload(
            QueryResult(
                records=tuple(records),
                total=job.total,
                truncated=job.truncated,
            )
        )
        payload.update(
            {
                "query_id": job.query_id,
                "processing_status": job.status.value,
                "detected_species_counts": dict(job.species_counts or {}),
                "model_version": job.model_version,
            }
        )
        return 200, payload

    def _edit_tags(self, request: HttpRequest) -> tuple[int, object]:
        result = self._services.management.edit_tags(
            actor_sub=request.auth.subject,
            tags=require_list(request.body, "tags"),
            operation=request.body.get("operation"),
            urls=require_list(request.body, "urls"),
            file_ids=require_list(request.body, "file_ids"),
        )
        return 200, {
            "operation": result.operation,
            "changed_tags": result.changed_tags,
            "media": [self._record_payload(record) for record in result.records],
        }

    def _delete(self, request: HttpRequest) -> tuple[int, object]:
        result = self._services.management.delete_media(
            actor_sub=request.auth.subject,
            urls=require_list(request.body, "urls"),
            file_ids=require_list(request.body, "file_ids"),
        )
        payload = {
            "complete": result.complete,
            "outcomes": [
                {
                    "identifier": item.identifier,
                    "file_id": item.file_id,
                    "deleted": item.deleted,
                    "already_absent": item.already_absent,
                    "error_code": item.error_code,
                }
                for item in result.outcomes
            ],
        }
        return (200 if result.complete else 500), payload

    def _subscription(self, request: HttpRequest) -> tuple[int, object]:
        if request.method == "POST":
            subscription = self._services.notifications.set_subscription(
                actor_sub=request.auth.subject,
                verified_email=request.auth.email,
                email_verified=request.auth.email_verified,
                tags=require_list(request.body, "tags"),
            )
            return 202, self._subscription_payload(subscription)
        if request.method == "GET":
            subscription = self._services.notifications.get_subscription(
                actor_sub=request.auth.subject
            )
            return 200, {
                "subscription": (
                    self._subscription_payload(subscription) if subscription else None
                )
            }
        if request.method == "DELETE":
            deleted = self._services.notifications.delete_subscription(
                actor_sub=request.auth.subject
            )
            return 200, {"deleted": deleted}
        raise HttpApiError(405, "METHOD_NOT_ALLOWED", "Method is not allowed for this route")

    def _query_payload(self, result: QueryResult) -> dict[str, object]:
        return {
            "media": [self._record_payload(record) for record in result.records],
            "total": result.total,
            "truncated": result.truncated,
        }

    def _record_payload(self, record: MediaRecord) -> dict[str, object]:
        payload: dict[str, object] = {
            "file_id": record.file_id,
            "filename": record.filename,
            "file_type": record.file_type.value,
            "species_counts": dict(record.species_counts or {}),
            "auto_tags": list(record.auto_tags),
            "manual_tags": list(record.manual_tags),
            "all_tags": list(record.all_tags),
            "processing_status": record.processing_status.value,
            "error_code": record.error_code,
            "detections": list(record.detections),
            "model_version": record.model_version,
            "video_samples": record.video_samples,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "version": record.version,
        }
        if record.processing_status == ProcessingStatus.READY:
            payload["original_url"] = self._services.storage.create_presigned_get(
                record.original_key, expires_in=900
            )
            payload["thumbnail_url"] = (
                self._services.storage.create_presigned_get(
                    record.thumbnail_key, expires_in=900
                )
                if record.thumbnail_key
                else None
            )
        return payload

    @staticmethod
    def _subscription_payload(subscription: Any) -> dict[str, object]:
        return {
            "email": subscription.email,
            "tags": list(subscription.tags),
            "status": subscription.status.value,
            "updated_at": subscription.updated_at,
        }

    @staticmethod
    def _limit(request: HttpRequest) -> int:
        return int(request.query.get("limit", "50"))


_application: CoreApiApplication | None = None


def _build_application() -> CoreApiApplication:
    import boto3

    from pacific_bioarchive.application.notifications import NotificationService
    from pacific_bioarchive.persistence.dynamodb import (
        DynamoDedupRepository,
        DynamoMediaRepository,
    )
    from pacific_bioarchive.persistence.notifications import (
        DynamoNotificationEventRepository,
        DynamoSubscriptionRepository,
    )
    from pacific_bioarchive.persistence.query_jobs import (
        DynamoTemporaryQueryRepository,
    )
    from pacific_bioarchive.persistence.s3 import S3ObjectStorage
    from pacific_bioarchive.persistence.sns import SnsNotificationTopic

    dynamodb = boto3.resource("dynamodb")
    media = DynamoMediaRepository(dynamodb.Table(os.environ["PBA_MEDIA_TABLE"]))
    dedup = DynamoDedupRepository(dynamodb.Table(os.environ["PBA_DEDUP_TABLE"]))
    bucket = os.environ["PBA_MEDIA_BUCKET"]
    storage = S3ObjectStorage(boto3.client("s3"), bucket_name=bucket)
    notifications = NotificationService(
        subscription_repository=DynamoSubscriptionRepository(
            dynamodb.Table(os.environ["PBA_SUBSCRIPTIONS_TABLE"])
        ),
        event_repository=DynamoNotificationEventRepository(
            dynamodb.Table(os.environ["PBA_NOTIFICATION_EVENTS_TABLE"])
        ),
        topic=SnsNotificationTopic(
            boto3.client("sns"), topic_arn=os.environ["PBA_NOTIFICATION_TOPIC_ARN"]
        ),
    )
    queries = MediaQueryService(media, bucket_name=bucket)
    temp_query_jobs = DynamoTemporaryQueryRepository(
        dynamodb.Table(os.environ["PBA_TEMP_QUERIES_TABLE"])
    )
    services = CoreApiServices(
        upload=UploadService(media_repository=media, dedup_repository=dedup, storage=storage),
        media_repository=media,
        storage=storage,
        queries=queries,
        management=MediaManagementService(
            media_repository=media,
            dedup_repository=dedup,
            storage=storage,
            bucket_name=bucket,
            notification_publisher=notifications,
        ),
        notifications=notifications,
        temp_queries=TemporaryQueryService(
            storage=storage,
            query_service=queries,
            image_inference=None,
            bucket_name=bucket,
        ),
        temp_query_jobs=temp_query_jobs,
    )
    return CoreApiApplication(services, version=os.getenv("PBA_APP_VERSION", "0.1.0"))


def lambda_handler(event: object, context: Any) -> dict[str, object]:
    del context
    global _application
    if _application is None:
        _application = _build_application()
    return _application.handle(event)
