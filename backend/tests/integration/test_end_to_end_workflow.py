from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

from pacific_bioarchive.application.management import MediaManagementService
from pacific_bioarchive.application.notifications import NotificationService
from pacific_bioarchive.application.processing import MediaProcessingService
from pacific_bioarchive.application.queries import MediaQueryService
from pacific_bioarchive.application.temp_queries import TemporaryQueryService
from pacific_bioarchive.application.uploads import UploadService
from pacific_bioarchive.domain.notifications import SubscriptionStatus
from pacific_bioarchive.domain.storage import ObjectInfo, PresignedPut
from pacific_bioarchive.handlers.api import CoreApiApplication, CoreApiServices
from pacific_bioarchive.handlers.media_processor import handle_s3_event
from pacific_bioarchive.media.checksum import sha256_bytes
from pacific_bioarchive.ml.types import InferenceResult, SpeciesDetection
from pacific_bioarchive.persistence.memory import (
    InMemoryDedupRepository,
    InMemoryMediaRepository,
)
from pacific_bioarchive.persistence.notifications import (
    InMemoryNotificationEventRepository,
    InMemorySubscriptionRepository,
)
from pacific_bioarchive.persistence.query_jobs import InMemoryTemporaryQueryRepository
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "fixtures" / "images" / "Alectura_lathami_1.JPG"


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str, dict[str, str], str]] = {}

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
            f"https://storage.test/{key}",
            {
                "Content-Type": content_type,
                "x-amz-checksum-sha256": checksum_base64,
                "x-amz-meta-file-id": file_id,
                "x-amz-meta-checksum-sha256": checksum_hex,
            },
            expires_in,
        )

    def accept_presigned_put(
        self, key: str, data: bytes, required_headers: dict[str, str]
    ) -> None:
        self.objects[key] = (
            data,
            required_headers["Content-Type"],
            {
                "file-id": required_headers["x-amz-meta-file-id"],
                "checksum-sha256": required_headers["x-amz-meta-checksum-sha256"],
            },
            required_headers["x-amz-checksum-sha256"],
        )

    def create_presigned_get(self, key: str, *, expires_in: int) -> str:
        return f"https://storage.test/{key}?expires={expires_in}"

    def head(self, key: str) -> ObjectInfo:
        data, content_type, metadata, checksum = self.objects[key]
        return ObjectInfo(len(data), content_type, checksum, metadata)

    def download_file(self, key: str, destination: str | Path) -> None:
        Path(destination).write_bytes(self.objects[key][0])

    def upload_bytes(self, key: str, data: bytes, *, content_type: str) -> None:
        checksum = base64.b64encode(bytes.fromhex(sha256_bytes(data))).decode("ascii")
        self.objects[key] = (data, content_type, {}, checksum)

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


class DeterministicInference:
    result = InferenceResult(
        {"australian brushturkey": 1},
        (
            SpeciesDetection(
                species="australian brushturkey",
                scientific_name="alectura_lathami",
                detection_confidence=0.96,
                classification_confidence=0.99,
                combined_confidence=0.9504,
                bbox_pixels=(10, 20, 100, 120),
            ),
        ),
        "integration-v1",
    )

    def classify_image(self, image_path: str | Path) -> InferenceResult:
        with Image.open(image_path) as image:
            image.verify()
        return self.result


class UnsupportedVideoInference:
    def classify_video(self, video_path: str | Path) -> object:
        raise AssertionError(f"Unexpected video path {video_path}")


class MemoryTopic:
    def __init__(self) -> None:
        self.published: list[dict[str, object]] = []

    def subscribe_email(self, email: str, *, tags: tuple[str, ...]) -> str:
        return "arn:aws:sns:ap-southeast-2:123456789012:topic:subscription"

    def set_filter(self, subscription_arn: str, *, tags: tuple[str, ...]) -> None:
        del subscription_arn, tags

    def get_status(self, subscription_arn: str) -> SubscriptionStatus:
        del subscription_arn
        return SubscriptionStatus.CONFIRMED

    def unsubscribe(self, subscription_arn: str) -> None:
        del subscription_arn

    def publish(self, **kwargs: object) -> None:
        self.published.append(kwargs)


class CompleteLocalWorkflowTests(unittest.TestCase):
    def test_upload_process_query_tag_notify_and_delete(self) -> None:
        media = InMemoryMediaRepository()
        dedup = InMemoryDedupRepository(epoch_seconds=lambda: 100)
        storage = MemoryStorage()
        topic = MemoryTopic()
        notifications = NotificationService(
            subscription_repository=InMemorySubscriptionRepository(),
            event_repository=InMemoryNotificationEventRepository(),
            topic=topic,
        )
        queries = MediaQueryService(media, bucket_name="private-media")
        services = CoreApiServices(
            upload=UploadService(
                media_repository=media,
                dedup_repository=dedup,
                storage=storage,
                id_factory=lambda: "e2e-file",
                epoch_seconds=lambda: 100,
            ),
            media_repository=media,
            storage=storage,
            queries=queries,
            management=MediaManagementService(
                media_repository=media,
                dedup_repository=dedup,
                storage=storage,
                bucket_name="private-media",
                notification_publisher=notifications,
            ),
            notifications=notifications,
            temp_queries=TemporaryQueryService(
                storage=storage,
                query_service=queries,
                image_inference=None,
                bucket_name="private-media",
            ),
            temp_query_jobs=InMemoryTemporaryQueryRepository(),
        )
        app = CoreApiApplication(services, version="integration")
        processor = MediaProcessingService(
            media_repository=media,
            dedup_repository=dedup,
            storage=storage,
            image_inference=DeterministicInference(),
            video_inference=UnsupportedVideoInference(),
            notification_publisher=notifications,
            temp_root=tempfile.gettempdir(),
        )

        subscription = self.call(
            app,
            "POST",
            "/notifications/subscription",
            {"tags": ["australian brushturkey"]},
            expected_status=202,
        )
        self.assertEqual(subscription["status"], "CONFIRMED")

        source = FIXTURE.read_bytes()
        checksum = sha256_bytes(source)
        ticket = self.call(
            app,
            "POST",
            "/uploads/init",
            {
                "filename": FIXTURE.name,
                "content_type": "image/jpeg",
                "size_bytes": len(source),
                "checksum": checksum,
            },
            expected_status=201,
        )
        storage.accept_presigned_put(ticket["object_key"], source, ticket["required_headers"])
        outcome = handle_s3_event(
            {
                "Records": [
                    {
                        "eventSource": "aws:s3",
                        "eventName": "ObjectCreated:Put",
                        "s3": {
                            "bucket": {"name": "private-media"},
                            "object": {"key": ticket["object_key"]},
                        },
                    }
                ]
            },
            processor=processor,
            expected_bucket="private-media",
        )
        self.assertEqual(outcome["results"][0]["status"], "READY")
        self.assertEqual(len(topic.published), 1)

        detail = self.call(app, "GET", "/media/e2e-file")
        self.assertEqual(detail["species_counts"], {"australian brushturkey": 1})
        self.assertIn("thumbnails/e2e-file.jpg", detail["thumbnail_url"])
        found = self.call(
            app,
            "POST",
            "/queries/tags",
            {"requirements": {"australian brushturkey": 1}},
        )
        self.assertEqual(found["media"][0]["file_id"], "e2e-file")

        tagged = self.call(
            app,
            "POST",
            "/media/tags",
            {"file_ids": ["e2e-file"], "tags": ["night"], "operation": 1},
        )
        self.assertEqual(tagged["changed_tags"], {"e2e-file": ["night"]})
        manual = self.call(app, "GET", "/queries/species", query={"tag": "night"})
        self.assertEqual(manual["total"], 1)

        deleted = self.call(
            app, "POST", "/media/delete", {"file_ids": ["e2e-file"]}
        )
        self.assertTrue(deleted["complete"])
        self.assertTrue(deleted["outcomes"][0]["deleted"])
        self.assertIsNone(media.get("e2e-file"))
        self.assertIsNone(dedup.get(checksum))
        self.assertFalse(storage.objects)

    @staticmethod
    def call(
        app: CoreApiApplication,
        method: str,
        path: str,
        body: dict[str, object] | None = None,
        *,
        query: dict[str, str] | None = None,
        expected_status: int = 200,
    ) -> dict[str, object]:
        response = app.handle(
            {
                "version": "2.0",
                "rawPath": path,
                "queryStringParameters": query,
                "body": json.dumps(body) if body is not None else None,
                "isBase64Encoded": False,
                "requestContext": {
                    "requestId": "local-e2e",
                    "http": {"method": method, "path": path},
                    "authorizer": {
                        "jwt": {
                            "claims": {
                                "sub": "owner-1",
                                "email": "student@example.edu",
                                "email_verified": True,
                            }
                        }
                    },
                },
            }
        )
        if response["statusCode"] != expected_status:
            raise AssertionError(response)
        return json.loads(response["body"])


if __name__ == "__main__":
    unittest.main()
