from __future__ import annotations

import base64
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from pacific_bioarchive.application.management import MediaManagementService
from pacific_bioarchive.application.notifications import NotificationService
from pacific_bioarchive.application.queries import MediaQueryService
from pacific_bioarchive.application.temp_queries import TemporaryQueryService
from pacific_bioarchive.application.uploads import UploadService
from pacific_bioarchive.domain.media import MediaRecord, ProcessingStatus
from pacific_bioarchive.domain.notifications import SubscriptionStatus
from pacific_bioarchive.domain.repositories import DedupReservation
from pacific_bioarchive.domain.storage import ObjectInfo, PresignedPut
from pacific_bioarchive.handlers.api import CoreApiApplication, CoreApiServices
from pacific_bioarchive.handlers.temp_query import handle_with_service
from pacific_bioarchive.media.checksum import sha256_bytes
from pacific_bioarchive.media.validation import MediaType
from pacific_bioarchive.ml.types import InferenceResult
from pacific_bioarchive.persistence.memory import (
    InMemoryDedupRepository,
    InMemoryMediaRepository,
)
from pacific_bioarchive.persistence.notifications import (
    InMemoryNotificationEventRepository,
    InMemorySubscriptionRepository,
)
from PIL import Image

BUCKET = "private-media-bucket"


def image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (120, 80), "brown").save(output, "JPEG")
    return output.getvalue()


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str, dict[str, str], str]] = {}
        self.deleted: list[str] = []

    def create_presigned_put(
        self,
        *,
        key: str,
        content_type: str,
        checksum_hex: str,
        file_id: str,
        expires_in: int,
    ) -> PresignedPut:
        checksum_base64 = base64.b64encode(bytes.fromhex(checksum_hex)).decode("ascii")
        return PresignedPut(
            url=f"https://signed.example/put/{key}",
            headers={
                "Content-Type": content_type,
                "x-amz-checksum-sha256": checksum_base64,
                "x-amz-meta-file-id": file_id,
                "x-amz-meta-checksum-sha256": checksum_hex,
            },
            expires_in=expires_in,
        )

    def create_presigned_get(self, key: str, *, expires_in: int) -> str:
        return f"https://signed.example/get/{key}?expires={expires_in}"

    def head(self, key: str) -> ObjectInfo:
        data, content_type, metadata, checksum_base64 = self.objects[key]
        return ObjectInfo(len(data), content_type, checksum_base64, metadata)

    def download_file(self, key: str, destination: str | Path) -> None:
        Path(destination).write_bytes(self.objects[key][0])

    def upload_bytes(self, key: str, data: bytes, *, content_type: str) -> None:
        checksum = sha256_bytes(data)
        self.objects[key] = (
            data,
            content_type,
            {},
            base64.b64encode(bytes.fromhex(checksum)).decode("ascii"),
        )

    def delete(self, key: str) -> None:
        self.deleted.append(key)
        self.objects.pop(key, None)

    def put_query(self, key: str, query_id: str, data: bytes) -> None:
        checksum = sha256_bytes(data)
        self.objects[key] = (
            data,
            "image/jpeg",
            {"file-id": query_id, "checksum-sha256": checksum},
            base64.b64encode(bytes.fromhex(checksum)).decode("ascii"),
        )


class FakeTopic:
    def __init__(self) -> None:
        self.published: list[dict[str, object]] = []

    def subscribe_email(self, email: str, *, tags: tuple[str, ...]) -> str:
        return "arn:subscription"

    def set_filter(self, subscription_arn: str, *, tags: tuple[str, ...]) -> None:
        pass

    def get_status(self, subscription_arn: str) -> SubscriptionStatus:
        return SubscriptionStatus.PENDING

    def unsubscribe(self, subscription_arn: str) -> None:
        pass

    def publish(self, **kwargs: object) -> None:
        self.published.append(kwargs)


class FakeInference:
    def classify_image(self, image_path: str | Path) -> InferenceResult:
        with Image.open(image_path) as image:
            image.verify()
        return InferenceResult({"dingo": 1}, (), "test-v1")


def ready_record() -> MediaRecord:
    return MediaRecord(
        file_id="ready-1",
        owner_sub="user-1",
        filename="ready.jpg",
        checksum="a" * 64,
        file_type=MediaType.IMAGE,
        content_type="image/jpeg",
        size_bytes=100,
        original_key="originals/ready-1/ready.jpg",
        thumbnail_key="thumbnails/ready-1.jpg",
        species_counts={"dingo": 2, "wombat": 1},
        processing_status=ProcessingStatus.READY,
        created_at="2026-08-23T00:00:00Z",
        updated_at="2026-08-23T00:00:00Z",
        version=3,
    )


class RestApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.media = InMemoryMediaRepository()
        self.dedup = InMemoryDedupRepository(epoch_seconds=lambda: 100)
        self.storage = FakeStorage()
        record = ready_record()
        self.media.create(record)
        self.dedup.reserve(
            DedupReservation(record.checksum, record.file_id, record.owner_sub, "RESERVED", 200)
        )
        self.dedup.commit(record.checksum, file_id=record.file_id)
        self.topic = FakeTopic()
        notifications = NotificationService(
            subscription_repository=InMemorySubscriptionRepository(),
            event_repository=InMemoryNotificationEventRepository(),
            topic=self.topic,
        )
        queries = MediaQueryService(self.media, bucket_name=BUCKET)
        self.temp_service = TemporaryQueryService(
            storage=self.storage,
            query_service=queries,
            image_inference=FakeInference(),
            bucket_name=BUCKET,
            id_factory=lambda: "query-1",
            temp_root=self.temp.name,
        )
        core_temp_service = TemporaryQueryService(
            storage=self.storage,
            query_service=queries,
            image_inference=None,
            bucket_name=BUCKET,
            id_factory=lambda: "query-1",
        )
        services = CoreApiServices(
            upload=UploadService(
                media_repository=self.media,
                dedup_repository=self.dedup,
                storage=self.storage,
                id_factory=lambda: "upload-1",
                epoch_seconds=lambda: 100,
            ),
            media_repository=self.media,
            storage=self.storage,
            queries=queries,
            management=MediaManagementService(
                media_repository=self.media,
                dedup_repository=self.dedup,
                storage=self.storage,
                bucket_name=BUCKET,
                notification_publisher=notifications,
            ),
            notifications=notifications,
            temp_queries=core_temp_service,
        )
        self.app = CoreApiApplication(services, version="test-version")

    def test_every_route_requires_cognito_subject(self) -> None:
        response = self.app.handle(self.event("GET", "/health", claims={}))
        self.assert_error(response, 401, "UNAUTHORIZED")

    def test_health_and_malformed_json_contract(self) -> None:
        response = self.app.handle(self.event("GET", "/health"))
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(self.payload(response), {"status": "ok", "version": "test-version"})
        malformed = self.app.handle(self.event("POST", "/uploads/init", raw_body="{"))
        self.assert_error(malformed, 400, "INVALID_JSON")

    def test_upload_init_returns_bound_ticket_and_duplicate_is_409(self) -> None:
        data = image_bytes()
        body = {
            "filename": "camera.jpg",
            "content_type": "image/jpeg",
            "size_bytes": len(data),
            "checksum": sha256_bytes(data),
        }
        created = self.app.handle(self.event("POST", "/uploads/init", body=body))
        payload = self.payload(created)
        self.assertEqual(created["statusCode"], 201)
        self.assertEqual(payload["file_id"], "upload-1")
        self.assertIn("x-amz-checksum-sha256", payload["required_headers"])
        duplicate = self.app.handle(self.event("POST", "/uploads/init", body=body))
        self.assert_error(duplicate, 409, "DUPLICATE_FILE")

    def test_media_detail_returns_short_lived_urls_and_hides_foreign_pending(self) -> None:
        ready = self.app.handle(self.event("GET", "/media/ready-1"))
        payload = self.payload(ready)
        self.assertIn("originals/ready-1", payload["original_url"])
        self.assertIn("thumbnails/ready-1", payload["thumbnail_url"])

        data = image_bytes()
        self.app.handle(
            self.event(
                "POST",
                "/uploads/init",
                body={
                    "filename": "private.jpg",
                    "content_type": "image/jpeg",
                    "size_bytes": len(data),
                    "checksum": sha256_bytes(data),
                },
            )
        )
        hidden = self.app.handle(
            self.event("GET", "/media/upload-1", claims=self.claims(sub="other-user"))
        )
        self.assert_error(hidden, 404, "MEDIA_NOT_FOUND")

    def test_tag_species_and_thumbnail_queries_return_ready_media(self) -> None:
        tags = self.app.handle(
            self.event(
                "POST", "/queries/tags", body={"requirements": {"dingo": 2, "wombat": 1}}
            )
        )
        self.assertEqual(self.payload(tags)["media"][0]["file_id"], "ready-1")
        species = self.app.handle(
            self.event("GET", "/queries/species", query={"tag": "dingo"})
        )
        self.assertEqual(self.payload(species)["total"], 1)
        thumbnail = self.app.handle(
            self.event(
                "POST",
                "/queries/thumbnail",
                body={"thumbnail_url": "thumbnails/ready-1.jpg"},
            )
        )
        self.assertIn("originals/ready-1", self.payload(thumbnail)["original_url"])

    def test_empty_query_and_unknown_route_have_stable_errors(self) -> None:
        empty = self.app.handle(
            self.event("POST", "/queries/tags", body={"requirements": {}})
        )
        self.assert_error(empty, 400, "INVALID_QUERY")
        missing = self.app.handle(self.event("GET", "/not-a-route"))
        self.assert_error(missing, 404, "ROUTE_NOT_FOUND")

    def test_unexpected_exception_is_redacted_from_response(self) -> None:
        def fail_presign(key: str, *, expires_in: int) -> str:
            raise RuntimeError("sensitive aws implementation detail")

        self.storage.create_presigned_get = fail_presign
        response = self.app.handle(self.event("GET", "/media/ready-1"))
        self.assert_error(response, 500, "INTERNAL_ERROR")
        self.assertNotIn("sensitive", response["body"])

    def test_temp_query_init_and_ml_handler_cleanup(self) -> None:
        data = image_bytes()
        checksum = sha256_bytes(data)
        init = self.app.handle(
            self.event(
                "POST",
                "/queries/file/init",
                body={
                    "filename": "query.jpg",
                    "content_type": "image/jpeg",
                    "size_bytes": len(data),
                    "checksum": checksum,
                },
            )
        )
        ticket = self.payload(init)
        self.storage.put_query(ticket["temp_key"], ticket["query_id"], data)
        result = handle_with_service(
            self.event(
                "POST",
                f"/queries/file/{ticket['query_id']}",
                body={"temp_key": ticket["temp_key"]},
            ),
            service=self.temp_service,
            storage=self.storage,
        )
        payload = self.payload(result)
        self.assertEqual(payload["detected_species_counts"], {"dingo": 1})
        self.assertEqual(payload["media"][0]["file_id"], "ready-1")
        self.assertNotIn(ticket["temp_key"], self.storage.objects)

    def test_temp_query_checksum_failure_still_deletes_object(self) -> None:
        data = image_bytes()
        ticket = self.temp_service.initiate(
            actor_sub="user-1",
            filename="query.jpg",
            content_type="image/jpeg",
            size_bytes=len(data),
            checksum=sha256_bytes(data),
        )
        self.storage.put_query(ticket.temp_key, ticket.query_id, data)
        stored = self.storage.objects[ticket.temp_key]
        self.storage.objects[ticket.temp_key] = (
            stored[0],
            stored[1],
            {**stored[2], "checksum-sha256": "b" * 64},
            stored[3],
        )
        response = handle_with_service(
            self.event(
                "POST",
                f"/queries/file/{ticket.query_id}",
                body={"temp_key": ticket.temp_key},
            ),
            service=self.temp_service,
            storage=self.storage,
        )
        self.assert_error(response, 400, "TEMP_QUERY_CHECKSUM_MISMATCH")
        self.assertNotIn(ticket.temp_key, self.storage.objects)

    def test_temp_ml_route_also_requires_cognito_subject(self) -> None:
        response = handle_with_service(
            self.event("POST", "/queries/file/query-1", claims={}),
            service=self.temp_service,
            storage=self.storage,
        )
        self.assert_error(response, 401, "UNAUTHORIZED")

    def test_temp_query_cannot_read_or_delete_another_users_object(self) -> None:
        data = image_bytes()
        ticket = self.temp_service.initiate(
            actor_sub="user-1",
            filename="query.jpg",
            content_type="image/jpeg",
            size_bytes=len(data),
            checksum=sha256_bytes(data),
        )
        self.storage.put_query(ticket.temp_key, ticket.query_id, data)
        response = handle_with_service(
            self.event(
                "POST",
                f"/queries/file/{ticket.query_id}",
                body={"temp_key": ticket.temp_key},
                claims=self.claims(sub="other-user"),
            ),
            service=self.temp_service,
            storage=self.storage,
        )
        self.assert_error(response, 400, "TEMP_QUERY_FORBIDDEN")
        self.assertIn(ticket.temp_key, self.storage.objects)

    def test_bulk_tag_add_and_owner_authorization(self) -> None:
        added = self.app.handle(
            self.event(
                "POST",
                "/media/tags",
                body={"file_ids": ["ready-1"], "tags": ["night"], "operation": 1},
            )
        )
        self.assertEqual(self.payload(added)["changed_tags"], {"ready-1": ["night"]})
        self.assertEqual(len(self.topic.published), 1)
        forbidden = self.app.handle(
            self.event(
                "POST",
                "/media/tags",
                body={"file_ids": ["ready-1"], "tags": ["x"], "operation": 1},
                claims=self.claims(sub="other-user"),
            )
        )
        self.assert_error(forbidden, 403, "FORBIDDEN")

    def test_delete_route_returns_outcomes_and_is_idempotent(self) -> None:
        first = self.app.handle(
            self.event("POST", "/media/delete", body={"file_ids": ["ready-1"]})
        )
        self.assertTrue(self.payload(first)["outcomes"][0]["deleted"])
        second = self.app.handle(
            self.event("POST", "/media/delete", body={"file_ids": ["ready-1"]})
        )
        self.assertTrue(self.payload(second)["outcomes"][0]["already_absent"])

    def test_notification_routes_use_verified_cognito_email(self) -> None:
        pending = self.app.handle(
            self.event("POST", "/notifications/subscription", body={"tags": ["dingo"]})
        )
        self.assertEqual(pending["statusCode"], 202)
        self.assertEqual(self.payload(pending)["email"], "student@example.edu")
        current = self.app.handle(self.event("GET", "/notifications/subscription"))
        self.assertEqual(self.payload(current)["subscription"]["status"], "PENDING")
        deleted = self.app.handle(self.event("DELETE", "/notifications/subscription"))
        self.assertTrue(self.payload(deleted)["deleted"])

        unverified = self.app.handle(
            self.event(
                "POST",
                "/notifications/subscription",
                body={"tags": ["dingo"]},
                claims=self.claims(verified=False),
            )
        )
        self.assert_error(unverified, 400, "EMAIL_NOT_VERIFIED")

    @staticmethod
    def claims(
        *, sub: str = "user-1", verified: bool = True
    ) -> dict[str, object]:
        return {
            "sub": sub,
            "email": "student@example.edu",
            "email_verified": verified,
        }

    def event(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, object] | None = None,
        raw_body: str | None = None,
        query: dict[str, str] | None = None,
        claims: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return {
            "version": "2.0",
            "rawPath": path,
            "queryStringParameters": query,
            "body": raw_body if raw_body is not None else (json.dumps(body) if body is not None else None),
            "isBase64Encoded": False,
            "requestContext": {
                "requestId": "request-123",
                "http": {"method": method, "path": path},
                "authorizer": {"jwt": {"claims": claims if claims is not None else self.claims()}},
            },
        }

    @staticmethod
    def payload(response: dict[str, object]) -> dict[str, object]:
        return json.loads(response["body"])

    def assert_error(self, response: dict[str, object], status: int, code: str) -> None:
        self.assertEqual(response["statusCode"], status)
        payload = self.payload(response)
        self.assertEqual(payload["error"]["code"], code)
        self.assertEqual(payload["error"]["request_id"], "request-123")


if __name__ == "__main__":
    unittest.main()
