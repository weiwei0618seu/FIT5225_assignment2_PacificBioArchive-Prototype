from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

from pacific_bioarchive.application.uploads import UploadService
from pacific_bioarchive.domain.repositories import DuplicateFileError
from pacific_bioarchive.domain.storage import ObjectInfo, PresignedPut
from pacific_bioarchive.media.validation import MediaValidationError
from pacific_bioarchive.persistence.memory import (
    InMemoryDedupRepository,
    InMemoryMediaRepository,
)
from pacific_bioarchive.persistence.s3 import S3ObjectStorage


class FakePrivateStorage:
    def __init__(self, *, fail_presign: bool = False) -> None:
        self.fail_presign = fail_presign
        self.calls: list[dict[str, object]] = []

    def create_presigned_put(self, **kwargs: object) -> PresignedPut:
        self.calls.append(kwargs)
        if self.fail_presign:
            raise RuntimeError("presign failed")
        return PresignedPut(
            url="https://signed.example/upload",
            headers={"Content-Type": str(kwargs["content_type"])},
            expires_in=int(kwargs["expires_in"]),
        )

    def create_presigned_get(self, key: str, *, expires_in: int) -> str:
        return f"https://signed.example/{key}"

    def head(self, key: str) -> ObjectInfo:
        raise NotImplementedError

    def download_file(self, key: str, destination: str | Path) -> None:
        raise NotImplementedError

    def upload_bytes(self, key: str, data: bytes, *, content_type: str) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        pass


class UploadServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.media = InMemoryMediaRepository()
        self.dedup = InMemoryDedupRepository(epoch_seconds=lambda: 100)
        self.storage = FakePrivateStorage()
        self.identifiers = iter(["file-1", "file-2", "file-3"])
        self.service = UploadService(
            media_repository=self.media,
            dedup_repository=self.dedup,
            storage=self.storage,
            id_factory=lambda: next(self.identifiers),
            epoch_seconds=lambda: 100,
            now_iso=lambda: "2026-08-23T00:00:00Z",
        )

    def test_success_reserves_checksum_creates_record_and_presigns_private_put(self) -> None:
        ticket = self.service.initiate(
            actor_sub="user-1",
            filename="../camera one.JPG",
            content_type="image/jpeg",
            size_bytes=1234,
            checksum="A" * 64,
        )

        self.assertEqual(ticket.file_id, "file-1")
        self.assertEqual(ticket.object_key, "originals/file-1/camera one.JPG")
        self.assertEqual(ticket.record.owner_sub, "user-1")
        self.assertEqual(self.media.get("file-1"), ticket.record)
        reservation = self.dedup.get("a" * 64)
        self.assertEqual(reservation.file_id, "file-1")
        self.assertEqual(reservation.expires_at, 3700)
        self.assertEqual(self.storage.calls[0]["checksum_hex"], "a" * 64)
        self.assertEqual(ticket.upload.expires_in, 900)

    def test_duplicate_content_is_rejected_before_second_record_or_url(self) -> None:
        arguments = {
            "actor_sub": "user-1",
            "filename": "first.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 50,
            "checksum": "b" * 64,
        }
        self.service.initiate(**arguments)
        with self.assertRaises(DuplicateFileError) as duplicate:
            self.service.initiate(**{**arguments, "filename": "renamed.jpg"})
        self.assertEqual(duplicate.exception.file_id, "file-1")
        self.assertEqual(len(self.storage.calls), 1)
        self.assertIsNone(self.media.get("file-2"))

    def test_invalid_upload_fails_before_reservation(self) -> None:
        with self.assertRaises(MediaValidationError):
            self.service.initiate(
                actor_sub="user-1",
                filename="fake.jpg",
                content_type="video/mp4",
                size_bytes=10,
                checksum="c" * 64,
            )
        self.assertEqual(self.dedup.get("c" * 64), None)
        self.assertEqual(self.storage.calls, [])

    def test_presign_failure_rolls_back_record_and_reservation(self) -> None:
        failing = UploadService(
            media_repository=self.media,
            dedup_repository=self.dedup,
            storage=FakePrivateStorage(fail_presign=True),
            id_factory=lambda: "file-fail",
            epoch_seconds=lambda: 100,
            now_iso=lambda: "now",
        )
        with self.assertRaisesRegex(RuntimeError, "presign failed"):
            failing.initiate(
                actor_sub="user-1",
                filename="camera.jpg",
                content_type="image/jpeg",
                size_bytes=10,
                checksum="d" * 64,
            )
        self.assertIsNone(self.media.get("file-fail"))
        self.assertIsNone(self.dedup.get("d" * 64))


class FakeS3Client:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def generate_presigned_url(self, operation: str, **kwargs: object) -> str:
        self.calls.append(("generate_presigned_url", {"operation": operation, **kwargs}))
        return f"https://signed.example/{operation}"

    def head_object(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("head_object", kwargs))
        return {
            "ContentLength": 25,
            "ContentType": "image/jpeg",
            "ChecksumSHA256": "base64checksum",
            "Metadata": {"file-id": "file-1"},
        }

    def download_file(self, bucket: str, key: str, destination: str) -> None:
        self.calls.append(
            ("download_file", {"bucket": bucket, "key": key, "destination": destination})
        )

    def put_object(self, **kwargs: object) -> None:
        self.calls.append(("put_object", kwargs))

    def delete_object(self, **kwargs: object) -> None:
        self.calls.append(("delete_object", kwargs))


class S3AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeS3Client()
        self.storage = S3ObjectStorage(self.client, bucket_name="private-bucket")

    def test_presigned_put_binds_checksum_content_type_and_metadata_headers(self) -> None:
        ticket = self.storage.create_presigned_put(
            key="originals/file-1/camera.jpg",
            content_type="image/jpeg",
            checksum_hex="a" * 64,
            file_id="file-1",
            expires_in=600,
        )
        call = self.client.calls[-1][1]
        params = call["Params"]
        expected_base64 = base64.b64encode(bytes.fromhex("a" * 64)).decode("ascii")
        self.assertEqual(params["ChecksumSHA256"], expected_base64)
        self.assertEqual(params["ContentType"], "image/jpeg")
        self.assertEqual(params["Metadata"]["file-id"], "file-1")
        self.assertEqual(ticket.headers["x-amz-checksum-sha256"], expected_base64)
        self.assertEqual(call["HttpMethod"], "PUT")

    def test_private_get_head_upload_download_and_delete_are_scoped_to_bucket(self) -> None:
        self.assertIn(
            "get_object", self.storage.create_presigned_get("thumbnails/a.jpg", expires_in=60)
        )
        info = self.storage.head("originals/a")
        self.assertEqual(info.size_bytes, 25)
        self.storage.upload_bytes("thumbnails/a.jpg", b"jpeg", content_type="image/jpeg")
        with tempfile.TemporaryDirectory() as directory:
            self.storage.download_file("originals/a", Path(directory) / "a.jpg")
        self.storage.delete("originals/a")
        for operation, call in self.client.calls:
            if "Bucket" in call:
                self.assertEqual(call["Bucket"], "private-bucket")


if __name__ == "__main__":
    unittest.main()
