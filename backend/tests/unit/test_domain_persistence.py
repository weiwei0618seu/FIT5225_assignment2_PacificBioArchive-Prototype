from __future__ import annotations

import unittest
from decimal import Decimal
from typing import ClassVar

from pacific_bioarchive.domain.media import MediaRecord, ProcessingStatus
from pacific_bioarchive.domain.repositories import (
    ConflictError,
    DedupReservation,
    DuplicateFileError,
)
from pacific_bioarchive.media.validation import MediaType
from pacific_bioarchive.persistence.dynamodb import (
    DynamoDedupRepository,
    DynamoMediaRepository,
    media_from_item,
    media_to_item,
)
from pacific_bioarchive.persistence.memory import (
    InMemoryDedupRepository,
    InMemoryMediaRepository,
)


def make_record(
    *,
    file_id: str = "file-1",
    file_type: MediaType = MediaType.IMAGE,
    status: ProcessingStatus = ProcessingStatus.RESERVED,
) -> MediaRecord:
    kwargs: dict[str, object] = {}
    if status == ProcessingStatus.READY and file_type == MediaType.IMAGE:
        kwargs["thumbnail_key"] = f"thumbnails/{file_id}.jpg"
    return MediaRecord(
        file_id=file_id,
        owner_sub="user-1",
        filename="camera.jpg" if file_type == MediaType.IMAGE else "clip.mp4",
        checksum=("a" if file_id == "file-1" else "b") * 64,
        file_type=file_type,
        content_type="image/jpeg" if file_type == MediaType.IMAGE else "video/mp4",
        size_bytes=100,
        original_key=f"originals/{file_id}/media",
        processing_status=status,
        created_at="2026-08-23T00:00:00Z",
        updated_at="2026-08-23T00:00:00Z",
        **kwargs,
    )


class MediaDomainTests(unittest.TestCase):
    def test_ready_transition_normalizes_counts_and_tags(self) -> None:
        reserved = make_record()
        processing = reserved.mark_processing(now="2026-08-23T00:01:00Z")
        ready = processing.mark_ready(
            species_counts={"Dingo": 2, "Australian_Magpie": 1},
            detections=({"confidence": 0.8125},),
            thumbnail_key="thumbnails/file-1.jpg",
            now="2026-08-23T00:02:00Z",
        )
        edited = ready.with_manual_tags(
            [" Night ", "DINGO", "night"], now="2026-08-23T00:03:00Z"
        )

        self.assertEqual(processing.version, 2)
        self.assertEqual(ready.processing_status, ProcessingStatus.READY)
        self.assertEqual(ready.species_counts, {"australian magpie": 1, "dingo": 2})
        self.assertEqual(edited.manual_tags, ("dingo", "night"))
        self.assertEqual(edited.all_tags, ("australian magpie", "dingo", "night"))
        self.assertEqual(edited.effective_count("night"), 1)
        self.assertEqual(edited.effective_count("dingo"), 2)
        self.assertEqual(edited.version, 4)

    def test_ready_image_requires_thumbnail_and_failed_requires_code(self) -> None:
        with self.assertRaisesRegex(ValueError, "thumbnail"):
            make_record(status=ProcessingStatus.READY).mark_ready(
                species_counts={}, detections=(), thumbnail_key=None
            )
        with self.assertRaises(ValueError):
            make_record().mark_failed("  ")
        failed = make_record().mark_failed("MODEL_ERROR", now="now")
        self.assertEqual(failed.error_code, "MODEL_ERROR")
        self.assertEqual(failed.processing_status, ProcessingStatus.FAILED)


class InMemoryRepositoryTests(unittest.TestCase):
    def test_create_save_delete_and_optimistic_conflict(self) -> None:
        repository = InMemoryMediaRepository()
        original = make_record()
        repository.create(original)
        with self.assertRaises(ConflictError):
            repository.create(original)

        processing = original.mark_processing(now="later")
        with self.assertRaises(ConflictError):
            repository.save(processing, expected_version=99)
        repository.save(processing, expected_version=1)
        self.assertEqual(repository.get(original.file_id), processing)
        self.assertEqual(repository.list_all(), (processing,))
        self.assertEqual(repository.delete(original.file_id), processing)
        self.assertIsNone(repository.delete(original.file_id))

    def test_dedup_reservation_duplicate_expiry_commit_and_release(self) -> None:
        clock = [100]
        repository = InMemoryDedupRepository(epoch_seconds=lambda: clock[0])
        first = DedupReservation("a" * 64, "file-1", "user-1", "RESERVED", 110)
        repository.reserve(first)
        with self.assertRaises(DuplicateFileError) as duplicate:
            repository.reserve(
                DedupReservation("a" * 64, "file-2", "user-2", "RESERVED", 120)
            )
        self.assertEqual(duplicate.exception.file_id, "file-1")

        clock[0] = 111
        replacement = DedupReservation("a" * 64, "file-2", "user-2", "RESERVED", 120)
        repository.reserve(replacement)
        repository.commit("a" * 64, file_id="file-2")
        self.assertEqual(repository.get("a" * 64).status, "COMMITTED")
        with self.assertRaises(ConflictError):
            repository.release("a" * 64, file_id="file-2")

        second = DedupReservation("b" * 64, "file-3", "user-3", "RESERVED", 130)
        repository.reserve(second)
        repository.release("b" * 64, file_id="file-3")
        self.assertIsNone(repository.get("b" * 64))


class ConditionalFailure(Exception):
    response: ClassVar[dict[str, dict[str, str]]] = {
        "Error": {"Code": "ConditionalCheckFailedException"}
    }


class FakeTable:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, object]] = {}
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.fail_condition = False

    def put_item(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("put_item", kwargs))
        if self.fail_condition:
            raise ConditionalFailure()
        item = dict(kwargs["Item"])
        key_name = "checksum" if item.get("status") in {"RESERVED", "COMMITTED"} else "file_id"
        key = str(item[key_name])
        self.items[key] = item
        return {}

    def get_item(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("get_item", kwargs))
        key_values = kwargs["Key"]
        key = str(next(iter(key_values.values())))
        return {"Item": self.items[key]} if key in self.items else {}

    def scan(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("scan", kwargs))
        return {"Items": list(self.items.values())}

    def delete_item(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("delete_item", kwargs))
        if self.fail_condition:
            raise ConditionalFailure()
        key = str(next(iter(kwargs["Key"].values())))
        old = self.items.pop(key, None)
        return {"Attributes": old} if old else {}

    def update_item(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("update_item", kwargs))
        if self.fail_condition:
            raise ConditionalFailure()
        key = str(next(iter(kwargs["Key"].values())))
        self.items[key]["status"] = "COMMITTED"
        self.items[key].pop("expires_at", None)
        return {}


class DynamoAdapterTests(unittest.TestCase):
    def test_media_serialization_round_trip_uses_decimal_not_float(self) -> None:
        ready = make_record().mark_ready(
            species_counts={"dingo": 2},
            detections=({"confidence": 0.8125},),
            thumbnail_key="thumbnails/file-1.jpg",
            now="later",
        )
        item = media_to_item(ready)
        self.assertIsInstance(item["detections"][0]["confidence"], Decimal)
        self.assertEqual(media_from_item(item), ready)

    def test_dynamo_media_conditions_and_delete_round_trip(self) -> None:
        table = FakeTable()
        repository = DynamoMediaRepository(table)
        record = make_record()
        repository.create(record)
        self.assertIn("attribute_not_exists", table.calls[-1][1]["ConditionExpression"])
        self.assertEqual(repository.get(record.file_id), record)
        self.assertEqual(repository.list_all(), (record,))
        self.assertEqual(repository.delete(record.file_id), record)

        table.fail_condition = True
        with self.assertRaises(ConflictError):
            repository.create(record)

    def test_dynamo_dedup_uses_expiry_condition_and_commits(self) -> None:
        table = FakeTable()
        repository = DynamoDedupRepository(table, epoch_seconds=lambda: 100)
        reservation = DedupReservation("a" * 64, "file-1", "user-1", "RESERVED", 110)
        repository.reserve(reservation)
        expression = table.calls[-1][1]["ConditionExpression"]
        self.assertIn("attribute_not_exists(checksum)", expression)
        self.assertIn("expires_at < :now", expression)
        repository.commit("a" * 64, file_id="file-1")
        expression = table.calls[-1][1]["ConditionExpression"]
        self.assertIn(":committed", expression)
        repository.commit("a" * 64, file_id="file-1")
        self.assertEqual(repository.get("a" * 64).status, "COMMITTED")


if __name__ == "__main__":
    unittest.main()
