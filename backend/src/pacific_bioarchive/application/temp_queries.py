"""Ephemeral image-query upload and guaranteed-cleanup inference workflow."""

from __future__ import annotations

import base64
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Protocol
from uuid import uuid4

from pacific_bioarchive.application.queries import MediaQueryService, QueryResult
from pacific_bioarchive.application.references import (
    ReferenceValidationError,
    normalize_s3_reference,
)
from pacific_bioarchive.domain.storage import PresignedPut, PrivateObjectStorage
from pacific_bioarchive.media.checksum import sha256_file
from pacific_bioarchive.media.validation import (
    MediaType,
    validate_checksum,
    validate_upload_metadata,
)
from pacific_bioarchive.ml.types import InferenceResult


class ImageInference(Protocol):
    def classify_image(self, image_path: str | Path) -> InferenceResult: ...


class TemporaryQueryError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class TemporaryQueryTicket:
    query_id: str
    temp_key: str
    upload: PresignedPut


@dataclass(frozen=True, slots=True)
class TemporaryQueryResult:
    inference: InferenceResult
    matches: QueryResult


class TemporaryQueryService:
    def __init__(
        self,
        *,
        storage: PrivateObjectStorage,
        query_service: MediaQueryService,
        image_inference: ImageInference | None,
        bucket_name: str,
        id_factory: Callable[[], object] = uuid4,
        upload_url_seconds: int = 300,
        temp_root: str | Path | None = None,
    ) -> None:
        self._storage = storage
        self._queries = query_service
        self._inference = image_inference
        self._bucket_name = bucket_name
        self._id_factory = id_factory
        self._upload_url_seconds = upload_url_seconds
        self._temp_root = Path(temp_root) if temp_root is not None else None

    def initiate(
        self,
        *,
        actor_sub: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        checksum: str,
    ) -> TemporaryQueryTicket:
        actor = actor_sub.strip()
        if not actor:
            raise TemporaryQueryError("UNAUTHENTICATED", "A Cognito subject is required")
        metadata = validate_upload_metadata(
            filename=filename, content_type=content_type, size_bytes=size_bytes
        )
        if metadata.file_type != MediaType.IMAGE:
            raise TemporaryQueryError(
                "TEMP_QUERY_IMAGE_REQUIRED", "Temporary queries accept images only"
            )
        normalized_checksum = validate_checksum(checksum)
        query_id = str(self._id_factory())
        if not query_id or "/" in query_id or "\\" in query_id:
            raise TemporaryQueryError("INVALID_QUERY_ID", "Generated query ID is unsafe")
        actor_hash = sha256(actor.encode("utf-8")).hexdigest()[:32]
        key = f"query-temp/{actor_hash}/{query_id}/{metadata.filename}"
        upload = self._storage.create_presigned_put(
            key=key,
            content_type=metadata.content_type,
            checksum_hex=normalized_checksum,
            file_id=query_id,
            expires_in=self._upload_url_seconds,
        )
        return TemporaryQueryTicket(query_id=query_id, temp_key=key, upload=upload)

    def execute(
        self,
        *,
        actor_sub: str,
        query_id: str,
        temp_reference: str,
        limit: int = 50,
    ) -> TemporaryQueryResult:
        if self._inference is None:
            raise TemporaryQueryError(
                "TEMP_QUERY_RUNTIME_UNAVAILABLE",
                "Temporary query inference runs in the ML function",
            )
        if not actor_sub.strip():
            raise TemporaryQueryError("UNAUTHENTICATED", "A Cognito subject is required")
        normalized_query_id = str(query_id).strip()
        if not normalized_query_id or any(
            token in normalized_query_id for token in ("/", "\\", "..")
        ):
            raise TemporaryQueryError("INVALID_QUERY_ID", "query_id is invalid")
        actor_hash = sha256(actor_sub.strip().encode("utf-8")).hexdigest()[:32]
        try:
            key = normalize_s3_reference(
                temp_reference,
                bucket_name=self._bucket_name,
                allowed_prefixes=("query-temp/",),
            )
        except ReferenceValidationError as exc:
            raise TemporaryQueryError("INVALID_TEMP_KEY", str(exc)) from exc
        prefix = f"query-temp/{actor_hash}/{normalized_query_id}/"
        if not key.startswith(prefix):
            raise TemporaryQueryError(
                "TEMP_QUERY_FORBIDDEN", "Temporary query object does not belong to this user"
            )

        try:
            info = self._storage.head(key)
            filename = PurePosixPath(key).name
            metadata = validate_upload_metadata(
                filename=filename,
                content_type=info.content_type,
                size_bytes=info.size_bytes,
            )
            if metadata.file_type != MediaType.IMAGE:
                raise TemporaryQueryError(
                    "TEMP_QUERY_IMAGE_REQUIRED", "Temporary queries accept images only"
                )
            checksum = self._verified_metadata_checksum(info.metadata, normalized_query_id)
            expected_base64 = base64.b64encode(bytes.fromhex(checksum)).decode("ascii")
            if info.checksum_sha256_base64 != expected_base64:
                raise TemporaryQueryError(
                    "TEMP_QUERY_CHECKSUM_MISMATCH", "S3 checksum header is invalid"
                )
            with tempfile.TemporaryDirectory(dir=self._temp_directory()) as directory:
                local_path = Path(directory) / f"query{Path(metadata.filename).suffix.lower()}"
                self._storage.download_file(key, local_path)
                if local_path.stat().st_size != metadata.size_bytes:
                    raise TemporaryQueryError(
                        "TEMP_QUERY_SIZE_MISMATCH", "Downloaded query image size changed"
                    )
                if sha256_file(local_path) != checksum:
                    raise TemporaryQueryError(
                        "TEMP_QUERY_CHECKSUM_MISMATCH",
                        "Downloaded query image failed SHA-256 verification",
                    )
                inference = self._inference.classify_image(local_path)
            matches = self._queries.find_by_inference(inference, limit=limit)
            return TemporaryQueryResult(inference=inference, matches=matches)
        finally:
            self._storage.delete(key)

    @staticmethod
    def _verified_metadata_checksum(metadata: dict[str, str], query_id: str) -> str:
        normalized = {str(key).lower(): str(value) for key, value in metadata.items()}
        if normalized.get("file-id") != query_id:
            raise TemporaryQueryError(
                "TEMP_QUERY_ID_MISMATCH", "S3 query ID metadata is invalid"
            )
        try:
            return validate_checksum(normalized.get("checksum-sha256", ""))
        except ValueError as exc:
            raise TemporaryQueryError(
                "TEMP_QUERY_CHECKSUM_MISMATCH", "S3 checksum metadata is invalid"
            ) from exc

    def _temp_directory(self) -> str | None:
        if self._temp_root is not None:
            self._temp_root.mkdir(parents=True, exist_ok=True)
            return str(self._temp_root)
        lambda_tmp = Path("/tmp")
        return str(lambda_tmp) if lambda_tmp.is_dir() else None
