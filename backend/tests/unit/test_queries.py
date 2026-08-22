from __future__ import annotations

import unittest

from pacific_bioarchive.application.queries import (
    MediaQueryService,
    QueryValidationError,
    normalize_requirements,
    normalize_thumbnail_reference,
)
from pacific_bioarchive.domain.media import MediaRecord, ProcessingStatus
from pacific_bioarchive.media.validation import MediaType
from pacific_bioarchive.ml.types import InferenceResult
from pacific_bioarchive.persistence.memory import InMemoryMediaRepository


def ready_record(
    file_id: str,
    counts: dict[str, int],
    *,
    manual_tags: tuple[str, ...] = (),
    status: ProcessingStatus = ProcessingStatus.READY,
    created_at: str = "2026-08-23T00:00:00Z",
) -> MediaRecord:
    return MediaRecord(
        file_id=file_id,
        owner_sub="user",
        filename=f"{file_id}.jpg",
        checksum=(file_id[0] if file_id[0] in "abcdef" else "a") * 64,
        file_type=MediaType.IMAGE,
        content_type="image/jpeg",
        size_bytes=100,
        original_key=f"originals/{file_id}/media.jpg",
        thumbnail_key=f"thumbnails/{file_id}.jpg" if status == ProcessingStatus.READY else None,
        species_counts=counts,
        manual_tags=manual_tags,
        processing_status=status,
        created_at=created_at,
        updated_at=created_at,
    )


class QueryServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryMediaRepository()
        records = [
            ready_record("a-one", {"dingo": 3, "wombat": 2, "magpie": 1}),
            ready_record("b-two", {"dingo": 2, "wombat": 5}),
            ready_record("c-three", {"dingo": 1}, manual_tags=("night", "wombat")),
            ready_record(
                "d-pending", {"dingo": 99}, status=ProcessingStatus.PROCESSING
            ),
        ]
        for record in records:
            self.repository.create(record)
        self.service = MediaQueryService(
            self.repository, bucket_name="pacific-media-bucket"
        )

    def test_minimum_count_includes_equality(self) -> None:
        result = self.service.find_by_requirements({"dingo": 3})
        self.assertEqual([record.file_id for record in result.records], ["a-one"])

    def test_multiple_requirements_are_strict_logical_and_not_or(self) -> None:
        result = self.service.find_by_requirements({"wombat": 2, "magpie": 1})
        self.assertEqual([record.file_id for record in result.records], ["a-one"])

    def test_manual_tag_counts_as_presence_but_not_larger_count(self) -> None:
        present = self.service.find_by_species(" NIGHT ")
        two_or_more = self.service.find_by_requirements({"night": 2})
        wombat_present = self.service.find_by_species("wombat")
        self.assertEqual([record.file_id for record in present.records], ["c-three"])
        self.assertEqual(two_or_more.records, ())
        self.assertEqual(
            {record.file_id for record in wombat_present.records},
            {"a-one", "b-two", "c-three"},
        )

    def test_processing_media_is_excluded_and_empty_results_are_valid(self) -> None:
        result = self.service.find_by_requirements({"dingo": 50})
        self.assertEqual(result.records, ())
        self.assertEqual(result.total, 0)
        self.assertFalse(result.truncated)

    def test_limit_reports_truncation(self) -> None:
        result = self.service.find_by_species("dingo", limit=2)
        self.assertEqual(len(result.records), 2)
        self.assertEqual(result.total, 3)
        self.assertTrue(result.truncated)

    def test_temporary_inference_uses_all_detected_tags_with_minimum_one(self) -> None:
        inference = InferenceResult(
            species_counts={"dingo": 4, "wombat": 7},
            detections=(),
            model_version="v1",
        )
        result = self.service.find_by_inference(inference)
        self.assertEqual(
            {record.file_id for record in result.records}, {"a-one", "b-two", "c-three"}
        )
        with self.assertRaises(QueryValidationError) as empty:
            self.service.find_by_inference(InferenceResult({}, (), "v1"))
        self.assertEqual(empty.exception.code, "NO_SPECIES_DETECTED")

    def test_thumbnail_signed_url_maps_to_record(self) -> None:
        url = (
            "https://pacific-media-bucket.s3.ap-southeast-2.amazonaws.com/"
            "thumbnails/a-one.jpg?X-Amz-Signature=secret"
        )
        self.assertEqual(self.service.find_by_thumbnail(url).file_id, "a-one")
        self.assertIsNone(self.service.find_by_thumbnail("thumbnails/missing.jpg"))


class QueryValidationTests(unittest.TestCase):
    def test_invalid_counts_empty_queries_and_limits_are_rejected(self) -> None:
        for requirements in ({}, {"dingo": 0}, {"dingo": True}, {"": 1}):
            with self.subTest(requirements=requirements), self.assertRaises(
                QueryValidationError
            ):
                normalize_requirements(requirements)
        repository = InMemoryMediaRepository()
        with self.assertRaises(QueryValidationError):
            MediaQueryService(repository).find_by_species(" ")
        with self.assertRaises(QueryValidationError):
            MediaQueryService(repository).find_by_species("dingo", limit=0)

    def test_thumbnail_reference_normalizes_virtual_and_path_style_urls(self) -> None:
        virtual = (
            "https://pacific-media-bucket.s3.ap-southeast-2.amazonaws.com/"
            "thumbnails/a%20b.jpg?X-Amz-Signature=x"
        )
        path_style = (
            "https://s3.ap-southeast-2.amazonaws.com/pacific-media-bucket/"
            "thumbnails/a.jpg"
        )
        self.assertEqual(
            normalize_thumbnail_reference(virtual, bucket_name="pacific-media-bucket"),
            "thumbnails/a b.jpg",
        )
        self.assertEqual(
            normalize_thumbnail_reference(path_style, bucket_name="pacific-media-bucket"),
            "thumbnails/a.jpg",
        )

    def test_wrong_bucket_non_thumbnail_and_traversal_are_rejected(self) -> None:
        invalid = [
            "https://wrong.s3.amazonaws.com/thumbnails/a.jpg",
            "https://pacific-media-bucket.s3.amazonaws.com/originals/a.jpg",
            "thumbnails/../originals/a.jpg",
            "ftp://pacific-media-bucket/thumbnails/a.jpg",
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(QueryValidationError):
                normalize_thumbnail_reference(value, bucket_name="pacific-media-bucket")


if __name__ == "__main__":
    unittest.main()

