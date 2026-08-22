"""Untrusted upload metadata validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
import re
import unicodedata


MIB = 1024 * 1024
DEFAULT_MAX_IMAGE_BYTES = 10 * MIB
DEFAULT_MAX_VIDEO_BYTES = 50 * MIB
MAX_FILENAME_LENGTH = 120
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
UNSAFE_FILENAME_CHARS = re.compile(r"[^\w.()\- ]+", flags=re.UNICODE)


class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"


IMAGE_CONTENT_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}
VIDEO_CONTENT_TYPES = {
    "video/mp4": {".mp4"},
    "video/quicktime": {".mov"},
    "video/x-msvideo": {".avi"},
}


class MediaValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class UploadMetadata:
    filename: str
    content_type: str
    size_bytes: int
    file_type: MediaType


def sanitize_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(filename)).replace("\\", "/")
    basename = PurePosixPath(normalized).name
    basename = CONTROL_CHARS.sub("", basename).strip().strip(".")
    basename = UNSAFE_FILENAME_CHARS.sub("_", basename)
    basename = re.sub(r"\s+", " ", basename).strip()
    if not basename:
        raise MediaValidationError("INVALID_FILENAME", "A valid filename is required")
    if len(basename) > MAX_FILENAME_LENGTH:
        stem, separator, extension = basename.rpartition(".")
        if separator and extension:
            keep = MAX_FILENAME_LENGTH - len(extension) - 1
            basename = f"{stem[:keep]}.{extension}"
        else:
            basename = basename[:MAX_FILENAME_LENGTH]
    return basename


def validate_checksum(checksum: str) -> str:
    normalized = str(checksum).strip().lower()
    if not SHA256_PATTERN.fullmatch(normalized):
        raise MediaValidationError(
            "INVALID_CHECKSUM", "checksum must be a 64-character SHA-256 hex value"
        )
    return normalized


def validate_upload_metadata(
    *,
    filename: str,
    content_type: str,
    size_bytes: int,
    max_image_bytes: int = DEFAULT_MAX_IMAGE_BYTES,
    max_video_bytes: int = DEFAULT_MAX_VIDEO_BYTES,
) -> UploadMetadata:
    safe_name = sanitize_filename(filename)
    normalized_content_type = str(content_type).split(";", 1)[0].strip().lower()
    extension = "." + safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""

    if normalized_content_type in IMAGE_CONTENT_TYPES:
        file_type = MediaType.IMAGE
        allowed_extensions = IMAGE_CONTENT_TYPES[normalized_content_type]
        maximum = max_image_bytes
    elif normalized_content_type in VIDEO_CONTENT_TYPES:
        file_type = MediaType.VIDEO
        allowed_extensions = VIDEO_CONTENT_TYPES[normalized_content_type]
        maximum = max_video_bytes
    else:
        raise MediaValidationError(
            "UNSUPPORTED_MEDIA_TYPE", "Only supported image and video formats can be uploaded"
        )

    if extension not in allowed_extensions:
        raise MediaValidationError(
            "CONTENT_TYPE_MISMATCH",
            "The file extension does not match the declared content type",
        )
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 1:
        raise MediaValidationError("INVALID_FILE_SIZE", "size_bytes must be a positive integer")
    if size_bytes > maximum:
        raise MediaValidationError(
            "FILE_TOO_LARGE", f"The {file_type.value} exceeds the {maximum}-byte limit"
        )
    return UploadMetadata(
        filename=safe_name,
        content_type=normalized_content_type,
        size_bytes=size_bytes,
        file_type=file_type,
    )

