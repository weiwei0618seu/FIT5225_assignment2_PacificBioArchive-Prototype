from __future__ import annotations

import base64
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus

from pacific_bioarchive.application.processing import (
    MediaProcessingService,
    ProcessingError,
)
from pacific_bioarchive.domain.media import MediaRecord, ProcessingStatus
from pacific_bioarchive.domain.repositories import ConflictError, DedupReservation
from pacific_bioarchive.domain.storage import ObjectInfo, PresignedPut
from pacific_bioarchive.handlers.media_processor import (
    StorageEventError,
    handle_s3_event,
    parse_s3_created_events,
)
from pacific_bioarchive.media.checksum import sha256_bytes
from pacific_bioarchive.media.validation import MediaType
from pacific_bioarchive.media.video_processing import VideoInferenceResult
from pacific_bioarchive.ml.types import InferenceResult, SpeciesDetection
from pacific_bioarchive.persistence.memory import (
    InMemoryDedupRepository,
    InMemoryMediaRepository,
)
from PIL import Image


def jpeg_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (640, 320), "green").save(output, "JPEG")
    return output.getvalue()


class FakeStorage:
    def __init__(self, data: bytes, *, fail_thumbnail: bool = False) -> None:
        self.data = data
        self.fail_thumbnail = fail_thumbnail
        self.record: MediaRecord | None = None
        self.downloads = 0
        self.uploads: list[tuple[str, bytes, str]] = []
        self.deleted: list[str] = []

    def bind(self, record: MediaRecord) -> None:
        self.record = record

    def create_presigned_put(self, **kwargs: object) -> PresignedPut:
        raise NotImplementedError

    def create_presigned_get(self, key: str, *, expires_in: int) -> str:
        raise NotImplementedError

    def head(self, key: str) -> ObjectInfo:
        assert self.record is not None
        checksum = base64.b64encode(bytes.fromhex(self.record.checksum)).decode("ascii")
        return ObjectInfo(
            size_bytes=len(self.data),
            content_type=self.record.content_type,
            checksum_sha256_base64=checksum,
            metadata={
                "file-id": self.record.file_id,
                "checksum-sha256": self.record.checksum,
            },
        )

    def download_file(self, key: str, destination: str | Path) -> None:
        self.downloads += 1
        Path(destination).write_bytes(self.data)

    def upload_bytes(self, key: str, data: bytes, *, content_type: str) -> None:
        if self.fail_thumbnail:
            raise RuntimeError("S3 put failed")
        self.uploads.append((key, data, content_type))

    def delete(self, key: str) -> None:
        self.deleted.append(key)


class FakeImageInference:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def classify_image(self, image_path: str | Path) -> InferenceResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("sensitive model details")
        return InferenceResult(
            species_counts={"dingo": 1},
            detections=(
                SpeciesDetection(
                    species="dingo",
                    scientific_name="Canis familiaris dingo",
                    detection_confidence=0.9,
                    classification_confidence=0.8,
                    combined_confidence=0.72,
                    bbox_pixels=(1, 2, 30, 40),
                ),
            ),
            model_version="test-v1",
        )


class FakeVideoInference:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def classify_video(self, video_path: str | Path) -> VideoInferenceResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("model failed")
        return VideoInferenceResult(
            species_counts={"koala": 2},
            detections=(),
            sampled_timestamps=(0, 1, 2),
            model_version="test-v1",
        )


class FakeNotifications:
    def __init__(self) -> None:
        self.fail = True
        self.calls = 0

    def publish_for_record(self, record: MediaRecord, **kwargs: object) -> bool:
        self.calls += 1
        if self.fail:
            raise RuntimeError("SNS unavailable")
        return True


class AlwaysConflictRepository(InMemoryMediaRepository):
    def save(self, record: MediaRecord, *, expected_version: int) -> None:
        raise ConflictError("simulated concurrent invocation")


class AsyncProcessingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def make_service(
        self,
        *,
        data: bytes,
        file_type: MediaType = MediaType.IMAGE,
        storage_data: bytes | None = None,
        fail_thumbnail: bool = False,
        fail_model: bool = False,
        repository: InMemoryMediaRepository | None = None,
        notifications: FakeNotifications | None = None,
    ) -> tuple[
        MediaProcessingService,
        InMemoryMediaRepository,
        InMemoryDedupRepository,
        FakeStorage,
        MediaRecord,
    ]:
        media = repository or InMemoryMediaRepository()
        dedup = InMemoryDedupRepository(epoch_seconds=lambda: 100)
        filename = "camera one.jpg" if file_type == MediaType.IMAGE else "clip.mp4"
        content_type = "image/jpeg" if file_type == MediaType.IMAGE else "video/mp4"
        record = MediaRecord(
            file_id="file-1",
            owner_sub="user-1",
            filename=filename,
            checksum=sha256_bytes(data),
            file_type=file_type,
            content_type=content_type,
            size_bytes=len(data),
            original_key=f"originals/file-1/{filename}",
            created_at="2026-08-23T00:00:00Z",
            updated_at="2026-08-23T00:00:00Z",
        )
        media.create(record)
        dedup.reserve(
            DedupReservation(record.checksum, record.file_id, record.owner_sub, "RESERVED", 200)
        )
        storage = FakeStorage(storage_data if storage_data is not None else data, fail_thumbnail=fail_thumbnail)
        storage.bind(record)
        service = MediaProcessingService(
            media_repository=media,
            dedup_repository=dedup,
            storage=storage,
            image_inference=FakeImageInference(fail=fail_model),
            video_inference=FakeVideoInference(fail=fail_model),
            notification_publisher=notifications,
            temp_root=self.temp.name,
        )
        return service, media, dedup, storage, record

    def test_image_success_uploads_thumbnail_persists_ready_and_commits_checksum(self) -> None:
        data = jpeg_bytes()
        service, media, dedup, storage, record = self.make_service(data=data)

        outcome = service.process_object(record.original_key)

        saved = media.get(record.file_id)
        self.assertEqual(outcome.status, ProcessingStatus.READY)
        self.assertEqual(saved.processing_status, ProcessingStatus.READY)
        self.assertEqual(saved.species_counts, {"dingo": 1})
        self.assertEqual(saved.thumbnail_key, "thumbnails/file-1.jpg")
        self.assertEqual(saved.model_version, "test-v1")
        self.assertEqual(saved.version, 3)
        self.assertEqual(storage.uploads[0][2], "image/jpeg")
        with Image.open(BytesIO(storage.uploads[0][1])) as thumbnail:
            self.assertEqual(thumbnail.size, (320, 160))
        self.assertEqual(dedup.get(record.checksum).status, "COMMITTED")

    def test_video_success_persists_one_fps_result_without_thumbnail(self) -> None:
        data = b"mock-video-content"
        service, media, dedup, storage, record = self.make_service(
            data=data, file_type=MediaType.VIDEO
        )

        service.process_object(record.original_key)

        saved = media.get(record.file_id)
        self.assertEqual(saved.species_counts, {"koala": 2})
        self.assertEqual(saved.video_samples, 3)
        self.assertIsNone(saved.thumbnail_key)
        self.assertEqual(storage.uploads, [])
        self.assertEqual(dedup.get(record.checksum).status, "COMMITTED")

    def test_ready_replay_is_idempotent_and_does_not_download_again(self) -> None:
        data = jpeg_bytes()
        service, _, _, storage, record = self.make_service(data=data)
        service.process_object(record.original_key)

        replay = service.process_object(record.original_key)

        self.assertTrue(replay.replay_ignored)
        self.assertEqual(storage.downloads, 1)
        self.assertEqual(len(storage.uploads), 1)

    def test_notification_failure_keeps_ready_and_replay_retries_without_ml(self) -> None:
        data = jpeg_bytes()
        notifications = FakeNotifications()
        service, media, dedup, storage, record = self.make_service(
            data=data, notifications=notifications
        )

        with self.assertRaises(ProcessingError) as failure:
            service.process_object(record.original_key)
        self.assertEqual(failure.exception.code, "NOTIFICATION_PUBLISH_FAILED")
        self.assertEqual(media.get(record.file_id).processing_status, ProcessingStatus.READY)
        self.assertEqual(dedup.get(record.checksum).status, "COMMITTED")

        notifications.fail = False
        replay = service.process_object(record.original_key)
        self.assertTrue(replay.replay_ignored)
        self.assertEqual(notifications.calls, 2)
        self.assertEqual(storage.downloads, 1)

    def test_recomputed_checksum_mismatch_is_failed_without_inference(self) -> None:
        expected = b"good"
        service, media, dedup, _, record = self.make_service(
            data=expected, storage_data=b"baad"
        )

        with self.assertRaisesRegex(ProcessingError, "failed safely") as failure:
            service.process_object(record.original_key)

        self.assertEqual(failure.exception.code, "CHECKSUM_MISMATCH")
        self.assertEqual(media.get(record.file_id).processing_status, ProcessingStatus.FAILED)
        self.assertEqual(media.get(record.file_id).error_code, "CHECKSUM_MISMATCH")
        self.assertEqual(dedup.get(record.checksum).status, "RESERVED")

    def test_thumbnail_upload_failure_persists_safe_code(self) -> None:
        data = jpeg_bytes()
        service, media, _, _, record = self.make_service(data=data, fail_thumbnail=True)
        with self.assertRaises(ProcessingError) as failure:
            service.process_object(record.original_key)
        self.assertEqual(failure.exception.code, "THUMBNAIL_UPLOAD_FAILED")
        self.assertEqual(media.get(record.file_id).error_code, "THUMBNAIL_UPLOAD_FAILED")

    def test_model_failure_deletes_uploaded_thumbnail_and_never_marks_ready(self) -> None:
        data = jpeg_bytes()
        service, media, _, storage, record = self.make_service(data=data, fail_model=True)
        with self.assertRaises(ProcessingError) as failure:
            service.process_object(record.original_key)
        self.assertEqual(failure.exception.code, "MODEL_INFERENCE_FAILED")
        self.assertEqual(storage.deleted, ["thumbnails/file-1.jpg"])
        self.assertEqual(media.get(record.file_id).processing_status, ProcessingStatus.FAILED)

    def test_initial_version_conflict_does_not_overwrite_newer_state_as_failed(self) -> None:
        data = jpeg_bytes()
        repository = AlwaysConflictRepository()
        service, media, _, _, record = self.make_service(data=data, repository=repository)
        with self.assertRaises(ConflictError):
            service.process_object(record.original_key)
        self.assertEqual(media.get(record.file_id).processing_status, ProcessingStatus.RESERVED)

    def test_event_parser_rejects_missing_wrong_type_and_wrong_bucket(self) -> None:
        with self.assertRaises(StorageEventError):
            parse_s3_created_events({})
        wrong_type = self.event("originals/file-1/camera.jpg", event_name="ObjectRemoved:Delete")
        with self.assertRaises(StorageEventError):
            parse_s3_created_events(wrong_type)

        data = jpeg_bytes()
        service, media, _, _, record = self.make_service(data=data)
        with self.assertRaises(StorageEventError):
            handle_s3_event(
                self.event(record.original_key, bucket="foreign-bucket"),
                processor=service,
                expected_bucket="private-bucket",
            )
        self.assertEqual(media.get(record.file_id).processing_status, ProcessingStatus.RESERVED)

    def test_handler_decodes_s3_key_and_returns_result(self) -> None:
        data = jpeg_bytes()
        service, _, _, _, record = self.make_service(data=data)
        response = handle_s3_event(
            self.event(record.original_key),
            processor=service,
            expected_bucket="private-bucket",
        )
        self.assertEqual(response["processed"], 1)
        self.assertEqual(response["results"][0]["file_id"], "file-1")

    @staticmethod
    def event(
        key: str,
        *,
        bucket: str = "private-bucket",
        event_name: str = "ObjectCreated:Put",
    ) -> dict[str, object]:
        return {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "eventName": event_name,
                    "s3": {
                        "bucket": {"name": bucket},
                        "object": {"key": quote_plus(key)},
                    },
                }
            ]
        }


if __name__ == "__main__":
    unittest.main()
