from __future__ import annotations

import unittest

from pacific_bioarchive.application.management import (
    AuthorizationError,
    ManagementValidationError,
    MediaManagementService,
)
from pacific_bioarchive.domain.media import MediaRecord, ProcessingStatus
from pacific_bioarchive.domain.repositories import DedupReservation, RecordNotFoundError
from pacific_bioarchive.media.validation import MediaType
from pacific_bioarchive.persistence.memory import (
    InMemoryDedupRepository,
    InMemoryMediaRepository,
)

BUCKET = "pacific-media-bucket"


def record(
    file_id: str,
    *,
    owner: str = "owner-1",
    file_type: MediaType = MediaType.IMAGE,
    manual_tags: tuple[str, ...] = (),
) -> MediaRecord:
    return MediaRecord(
        file_id=file_id,
        owner_sub=owner,
        filename=f"{file_id}.jpg" if file_type == MediaType.IMAGE else f"{file_id}.mp4",
        checksum=("a" if file_id == "file-a" else "b") * 64,
        file_type=file_type,
        content_type="image/jpeg" if file_type == MediaType.IMAGE else "video/mp4",
        size_bytes=100,
        original_key=f"originals/{file_id}/media",
        thumbnail_key=f"thumbnails/{file_id}.jpg" if file_type == MediaType.IMAGE else None,
        species_counts={"dingo": 1},
        manual_tags=manual_tags,
        processing_status=ProcessingStatus.READY,
        created_at="2026-08-23T00:00:00Z",
        updated_at="2026-08-23T00:00:00Z",
    )


class FakeStorage:
    def __init__(self, keys: set[str], *, fail_on: str | None = None) -> None:
        self.keys = set(keys)
        self.fail_on = fail_on
        self.deleted: list[str] = []

    def delete(self, key: str) -> None:
        if key == self.fail_on:
            raise RuntimeError("simulated storage failure")
        self.deleted.append(key)
        self.keys.discard(key)


class FakeNotifications:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def publish_for_record(self, item: MediaRecord, *, tags: set[str] | None = None) -> bool:
        self.calls.append((item.file_id, tuple(sorted(tags or ()))))
        return True


class ManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.media = InMemoryMediaRepository()
        self.dedup = InMemoryDedupRepository(epoch_seconds=lambda: 100)
        self.records = [
            record("file-a", manual_tags=("night",)),
            record("file-b", file_type=MediaType.VIDEO),
        ]
        for item in self.records:
            self.media.create(item)
            self.dedup.reserve(
                DedupReservation(
                    item.checksum, item.file_id, item.owner_sub, "RESERVED", 200
                )
            )
            self.dedup.commit(item.checksum, file_id=item.file_id)
        keys = {
            key
            for item in self.records
            for key in (item.original_key, item.thumbnail_key)
            if key
        }
        self.storage = FakeStorage(keys)
        self.notifications = FakeNotifications()
        self.service = MediaManagementService(
            media_repository=self.media,
            dedup_repository=self.dedup,
            storage=self.storage,
            bucket_name=BUCKET,
            notification_publisher=self.notifications,
        )

    def test_bulk_add_tags_accepts_ids_and_signed_urls(self) -> None:
        url = (
            f"https://{BUCKET}.s3.ap-southeast-2.amazonaws.com/"
            "thumbnails/file-a.jpg?X-Amz-Signature=x"
        )
        result = self.service.edit_tags(
            actor_sub="owner-1",
            tags=[" Research ", "NIGHT"],
            operation=1,
            urls=[url],
            file_ids=["file-b"],
        )

        self.assertEqual({item.file_id for item in result.records}, {"file-a", "file-b"})
        self.assertEqual(self.media.get("file-a").manual_tags, ("night", "research"))
        self.assertEqual(self.media.get("file-b").manual_tags, ("night", "research"))
        self.assertEqual(result.changed_tags["file-a"], ("research",))
        self.assertEqual(result.changed_tags["file-b"], ("night", "research"))
        self.assertEqual(
            self.notifications.calls,
            [("file-a", ("night", "research")), ("file-b", ("night", "research"))],
        )

    def test_bulk_remove_ignores_absent_tags_without_extra_version(self) -> None:
        result = self.service.edit_tags(
            actor_sub="owner-1",
            tags=["night", "absent"],
            operation=0,
            file_ids=["file-a", "file-b"],
        )

        first, second = result.records
        self.assertEqual(first.manual_tags, ())
        self.assertEqual(first.version, 2)
        self.assertEqual(second.manual_tags, ())
        self.assertEqual(second.version, 1)
        self.assertEqual(result.changed_tags["file-a"], ("night",))
        self.assertEqual(result.changed_tags["file-b"], ())

    def test_validation_missing_records_and_owner_are_preflighted(self) -> None:
        invalid_calls = [
            {"tags": ["x"], "operation": 2, "file_ids": ["file-a"]},
            {"tags": [], "operation": 1, "file_ids": ["file-a"]},
            {"tags": ["x"], "operation": 1, "file_ids": []},
        ]
        for kwargs in invalid_calls:
            with self.subTest(kwargs=kwargs), self.assertRaises(ManagementValidationError):
                self.service.edit_tags(actor_sub="owner-1", **kwargs)
        with self.assertRaises(RecordNotFoundError):
            self.service.edit_tags(
                actor_sub="owner-1", tags=["x"], operation=1, file_ids=["missing"]
            )
        with self.assertRaises(AuthorizationError):
            self.service.edit_tags(
                actor_sub="other", tags=["x"], operation=1, file_ids=["file-a"]
            )
        self.assertEqual(self.media.get("file-a").manual_tags, ("night",))

    def test_delete_removes_image_video_thumbnail_records_and_checksums(self) -> None:
        result = self.service.delete_media(
            actor_sub="owner-1", file_ids=["file-a", "file-b"]
        )

        self.assertTrue(result.complete)
        self.assertTrue(all(outcome.deleted for outcome in result.outcomes))
        self.assertEqual(
            set(self.storage.deleted),
            {
                "originals/file-a/media",
                "thumbnails/file-a.jpg",
                "originals/file-b/media",
            },
        )
        self.assertIsNone(self.media.get("file-a"))
        self.assertIsNone(self.media.get("file-b"))
        self.assertIsNone(self.dedup.get("a" * 64))
        self.assertIsNone(self.dedup.get("b" * 64))

    def test_repeated_delete_is_idempotent(self) -> None:
        first = self.service.delete_media(actor_sub="owner-1", file_ids=["file-a"])
        second = self.service.delete_media(actor_sub="owner-1", file_ids=["file-a"])
        self.assertTrue(first.outcomes[0].deleted)
        self.assertTrue(second.outcomes[0].already_absent)
        self.assertTrue(second.complete)

    def test_storage_failure_keeps_metadata_and_reports_incomplete(self) -> None:
        failing_storage = FakeStorage(self.storage.keys, fail_on="originals/file-a/media")
        service = MediaManagementService(
            media_repository=self.media,
            dedup_repository=self.dedup,
            storage=failing_storage,
            bucket_name=BUCKET,
        )
        result = service.delete_media(actor_sub="owner-1", file_ids=["file-a"])
        self.assertFalse(result.complete)
        self.assertEqual(result.outcomes[0].error_code, "DELETE_INCOMPLETE")
        self.assertIsNotNone(self.media.get("file-a"))
        self.assertIsNotNone(self.dedup.get("a" * 64))


if __name__ == "__main__":
    unittest.main()
