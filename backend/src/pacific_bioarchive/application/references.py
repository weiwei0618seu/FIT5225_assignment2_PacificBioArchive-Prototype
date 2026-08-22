"""Normalize assignment URL inputs into private S3 object keys."""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit


class ReferenceValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def normalize_s3_reference(
    reference: str,
    *,
    bucket_name: str | None,
    allowed_prefixes: tuple[str, ...],
) -> str:
    value = str(reference).strip()
    if not value:
        raise ReferenceValidationError("INVALID_MEDIA_URL", "A media URL/key is required")
    parsed = urlsplit(value)
    if parsed.scheme:
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise ReferenceValidationError(
                "INVALID_MEDIA_URL", "Only HTTP(S) media URLs are supported"
            )
        path = unquote(parsed.path).lstrip("/")
        host = parsed.netloc.split(":", 1)[0].lower()
        if bucket_name:
            expected_bucket = bucket_name.lower()
            if host.startswith(f"{expected_bucket}.s3"):
                key = path
            elif host.startswith("s3") and path.startswith(f"{bucket_name}/"):
                key = path[len(bucket_name) + 1 :]
            else:
                raise ReferenceValidationError(
                    "INVALID_MEDIA_URL", "Media URL does not belong to the configured bucket"
                )
        else:
            key = path
    else:
        key = unquote(value).lstrip("/")

    pure_key = PurePosixPath(key)
    if any(part in {"", ".", ".."} for part in pure_key.parts):
        raise ReferenceValidationError("INVALID_MEDIA_URL", "Media key is unsafe")
    normalized_key = pure_key.as_posix()
    if normalized_key.endswith("/") or not any(
        normalized_key.startswith(prefix) for prefix in allowed_prefixes
    ):
        raise ReferenceValidationError(
            "INVALID_MEDIA_URL", "Media URL/key has an unsupported object prefix"
        )
    return normalized_key

