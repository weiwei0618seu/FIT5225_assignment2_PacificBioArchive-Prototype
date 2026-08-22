from __future__ import annotations

import tempfile
import unittest
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from pacific_bioarchive.media.checksum import sha256_bytes, sha256_file, sha256_stream
from pacific_bioarchive.media.image_processing import build_thumbnail
from pacific_bioarchive.media.validation import (
    MediaType,
    MediaValidationError,
    sanitize_filename,
    validate_checksum,
    validate_upload_metadata,
)
from PIL import Image


class ChecksumTests(unittest.TestCase):
    def test_same_content_has_same_checksum_independent_of_filename(self) -> None:
        content = b"same wildlife bytes" * 1000
        expected = sha256(content).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.jpg"
            second = Path(directory) / "renamed.jpg"
            first.write_bytes(content)
            second.write_bytes(content)
            self.assertEqual(sha256_file(first, chunk_size=17), expected)
            self.assertEqual(sha256_file(second), expected)
        self.assertEqual(sha256_bytes(content), expected)
        self.assertEqual(sha256_stream(BytesIO(content), chunk_size=3), expected)

    def test_invalid_chunk_size_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            sha256_stream(BytesIO(b"x"), chunk_size=0)


class UploadValidationTests(unittest.TestCase):
    def test_sanitizes_paths_and_control_characters(self) -> None:
        self.assertEqual(sanitize_filename("../unsafe\\camera\x00 name.JPG"), "camera name.JPG")

    def test_valid_image_metadata_is_normalized(self) -> None:
        result = validate_upload_metadata(
            filename="Camera.JPG",
            content_type="Image/JPEG; charset=binary",
            size_bytes=123,
        )
        self.assertEqual(result.file_type, MediaType.IMAGE)
        self.assertEqual(result.content_type, "image/jpeg")

    def test_content_type_mismatch_and_limits_are_rejected(self) -> None:
        with self.assertRaisesRegex(MediaValidationError, "extension") as mismatch:
            validate_upload_metadata(
                filename="fake.jpg", content_type="video/mp4", size_bytes=10
            )
        self.assertEqual(mismatch.exception.code, "CONTENT_TYPE_MISMATCH")
        with self.assertRaises(MediaValidationError) as too_large:
            validate_upload_metadata(
                filename="large.png",
                content_type="image/png",
                size_bytes=11,
                max_image_bytes=10,
            )
        self.assertEqual(too_large.exception.code, "FILE_TOO_LARGE")

    def test_checksum_is_case_normalized_and_strict(self) -> None:
        checksum = "A" * 64
        self.assertEqual(validate_checksum(checksum), "a" * 64)
        with self.assertRaises(MediaValidationError):
            validate_checksum("not-a-checksum")


class ThumbnailTests(unittest.TestCase):
    @staticmethod
    def encoded_image(size: tuple[int, int], mode: str = "RGB", fmt: str = "PNG") -> bytes:
        color: object = (40, 100, 180, 128) if mode == "RGBA" else (40, 100, 180)
        image = Image.new(mode, size, color)
        buffer = BytesIO()
        image.save(buffer, format=fmt)
        return buffer.getvalue()

    def test_landscape_thumbnail_preserves_aspect_ratio_and_compresses(self) -> None:
        original = self.encoded_image((4000, 2000))
        result = build_thumbnail(original, max_width=320, max_height=320, quality=75)
        self.assertEqual((result.width, result.height), (320, 160))
        self.assertLess(len(result.data), len(original))
        with Image.open(BytesIO(result.data)) as decoded:
            self.assertEqual(decoded.format, "JPEG")
            self.assertEqual(decoded.mode, "RGB")

    def test_portrait_and_small_images_are_not_distorted_or_upscaled(self) -> None:
        portrait = build_thumbnail(self.encoded_image((1000, 2000)))
        small = build_thumbnail(self.encoded_image((100, 50)))
        self.assertEqual((portrait.width, portrait.height), (160, 320))
        self.assertEqual((small.width, small.height), (100, 50))

    def test_transparency_is_composited_and_invalid_images_fail_safely(self) -> None:
        transparent = build_thumbnail(self.encoded_image((200, 100), mode="RGBA"))
        with Image.open(BytesIO(transparent.data)) as decoded:
            self.assertEqual(decoded.mode, "RGB")
        with self.assertRaises(MediaValidationError) as invalid:
            build_thumbnail(b"not an image")
        self.assertEqual(invalid.exception.code, "INVALID_IMAGE")


if __name__ == "__main__":
    unittest.main()

