"""Verified, idempotent processing of newly uploaded private media."""

from __future__ import annotations

import base64
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from pacific_bioarchive.domain.media import MediaRecord, ProcessingStatus
from pacific_bioarchive.domain.repositories import (
    ConflictError,
    DedupRepository,
    MediaRepository,
    RecordNotFoundError,
)
from pacific_bioarchive.domain.storage import ObjectInfo, PrivateObjectStorage
from pacific_bioarchive.media.checksum import sha256_file
from pacific_bioarchive.media.image_processing import build_thumbnail
from pacific_bioarchive.media.validation import MediaType, MediaValidationError
from pacific_bioarchive.media.video_processing import (
    VideoInferenceResult,
    VideoProcessingError,
)
from pacific_bioarchive.ml.types import InferenceResult

LOGGER = logging.getLogger(__name__)


class ProcessingError(RuntimeError):
    """A stable, non-sensitive media-processing failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ImageInference(Protocol):
    def classify_image(self, image_path: str | Path) -> InferenceResult: ...


class VideoInference(Protocol):
    def classify_video(self, video_path: str | Path) -> VideoInferenceResult: ...


class RecordNotificationPublisher(Protocol):
    def publish_for_record(self, record: MediaRecord, **kwargs: object) -> bool: ...


@dataclass(frozen=True, slots=True)
class ProcessingOutcome:
    file_id: str
    status: ProcessingStatus
    replay_ignored: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "file_id": self.file_id,
            "status": self.status.value,
            "replay_ignored": self.replay_ignored,
        }


def file_id_from_original_key(key: str) -> str:
    parts = PurePosixPath(key).parts
    if len(parts) != 3 or parts[0] != "originals" or not parts[1] or not parts[2]:
        raise ProcessingError(
            "INVALID_OBJECT_KEY", "S3 events must reference originals/<file_id>/<filename>"
        )
    if parts[1] in {".", ".."}:
        raise ProcessingError("INVALID_OBJECT_KEY", "The S3 object key is unsafe")
    return parts[1]


class MediaProcessingService:
    """Validate S3 bytes, run media inference, and persist a terminal state."""

    def __init__(
        self,
        *,
        media_repository: MediaRepository,
        dedup_repository: DedupRepository,
        storage: PrivateObjectStorage,
        image_inference: ImageInference,
        video_inference: VideoInference,
        notification_publisher: RecordNotificationPublisher | None = None,
        temp_root: str | Path | None = None,
    ) -> None:
        self._media = media_repository
        self._dedup = dedup_repository
        self._storage = storage
        self._image_inference = image_inference
        self._video_inference = video_inference
        self._notifications = notification_publisher
        self._temp_root = Path(temp_root) if temp_root is not None else None

    def process_object(self, key: str) -> ProcessingOutcome:
        file_id = file_id_from_original_key(key)
        record = self._media.get(file_id)
        if record is None:
            raise RecordNotFoundError(f"No media record exists for {file_id}")
        if record.original_key != key:
            raise ProcessingError(
                "OBJECT_KEY_MISMATCH", "The S3 event key does not match the media record"
            )
        if record.processing_status == ProcessingStatus.READY:
            # This is deliberately idempotent, including recovery from a prior
            # READY write followed by a transient checksum-commit failure.
            self._dedup.commit(record.checksum, file_id=record.file_id)
            self._publish_notification(record)
            return ProcessingOutcome(record.file_id, ProcessingStatus.READY, True)

        thumbnail_key: str | None = None
        processing_record: MediaRecord | None = None
        ready_saved = False
        try:
            with tempfile.TemporaryDirectory(dir=self._temp_directory()) as directory:
                local_path = Path(directory) / f"source{Path(record.filename).suffix.lower()}"
                object_info = self._storage.head(key)
                self._storage.download_file(key, local_path)
                self._verify_uploaded_object(record, object_info, local_path)

                processing_record = record.mark_processing()
                self._media.save(processing_record, expected_version=record.version)

                if record.file_type == MediaType.IMAGE:
                    thumbnail_key = f"thumbnails/{record.file_id}.jpg"
                    (
                        thumbnail_key,
                        counts,
                        detections,
                        video_samples,
                        model_version,
                    ) = self._process_image(processing_record, local_path)
                else:
                    counts, detections, video_samples, model_version = self._process_video(
                        local_path
                    )

                ready = processing_record.mark_ready(
                    species_counts=counts,
                    detections=detections,
                    model_version=model_version,
                    thumbnail_key=thumbnail_key,
                    video_samples=video_samples,
                )
                self._media.save(ready, expected_version=processing_record.version)
                ready_saved = True
                self._dedup.commit(ready.checksum, file_id=ready.file_id)
                self._publish_notification(ready)
                return ProcessingOutcome(ready.file_id, ProcessingStatus.READY)
        except ConflictError:
            # Another invocation owns the optimistic transition. Never replace
            # its newer state with FAILED.
            raise
        except Exception as exc:
            if ready_saved:
                code = (
                    exc.code
                    if isinstance(exc, ProcessingError)
                    else "DEDUP_COMMIT_FAILED"
                )
                raise ProcessingError(
                    code,
                    "Media is READY but post-processing must be retried",
                ) from exc
            if thumbnail_key:
                try:
                    self._storage.delete(thumbnail_key)
                except Exception:
                    LOGGER.exception("Unable to remove partial thumbnail for %s", record.file_id)
            code = self._safe_error_code(exc)
            current = processing_record or record
            failed = current.mark_failed(code)
            self._media.save(failed, expected_version=current.version)
            raise ProcessingError(code, "Media processing failed safely") from exc

    def _publish_notification(self, record: MediaRecord) -> None:
        if self._notifications is None:
            return
        try:
            self._notifications.publish_for_record(record)
        except Exception as exc:
            raise ProcessingError(
                "NOTIFICATION_PUBLISH_FAILED", "Notification publishing must be retried"
            ) from exc

    def _temp_directory(self) -> str | None:
        if self._temp_root is not None:
            self._temp_root.mkdir(parents=True, exist_ok=True)
            return str(self._temp_root)
        lambda_tmp = Path("/tmp")
        return str(lambda_tmp) if lambda_tmp.is_dir() else None

    @staticmethod
    def _verify_uploaded_object(
        record: MediaRecord, object_info: ObjectInfo, local_path: Path
    ) -> None:
        if object_info.size_bytes != record.size_bytes or local_path.stat().st_size != record.size_bytes:
            raise ProcessingError("FILE_SIZE_MISMATCH", "Uploaded size does not match the ticket")
        actual_type = object_info.content_type.split(";", 1)[0].strip().lower()
        if actual_type != record.content_type:
            raise ProcessingError("CONTENT_TYPE_MISMATCH", "Uploaded MIME type does not match")
        metadata = {str(key).lower(): str(value) for key, value in object_info.metadata.items()}
        if metadata.get("file-id") != record.file_id:
            raise ProcessingError("FILE_ID_METADATA_MISMATCH", "S3 file ID metadata is invalid")
        if metadata.get("checksum-sha256", "").lower() != record.checksum:
            raise ProcessingError("CHECKSUM_METADATA_MISMATCH", "S3 checksum metadata is invalid")
        expected_base64 = base64.b64encode(bytes.fromhex(record.checksum)).decode("ascii")
        if object_info.checksum_sha256_base64 != expected_base64:
            raise ProcessingError("S3_CHECKSUM_MISMATCH", "S3 checksum header is invalid")
        if sha256_file(local_path) != record.checksum:
            raise ProcessingError("CHECKSUM_MISMATCH", "Uploaded bytes failed SHA-256 verification")

    def _process_image(
        self, record: MediaRecord, local_path: Path
    ) -> tuple[str, dict[str, int], tuple[dict[str, object], ...], None, str]:
        thumbnail = build_thumbnail(local_path)
        thumbnail_key = f"thumbnails/{record.file_id}.jpg"
        try:
            self._storage.upload_bytes(
                thumbnail_key, thumbnail.data, content_type=thumbnail.content_type
            )
        except Exception as exc:
            raise ProcessingError(
                "THUMBNAIL_UPLOAD_FAILED", "The thumbnail could not be stored"
            ) from exc
        try:
            result = self._image_inference.classify_image(local_path)
        except Exception as exc:
            raise ProcessingError("MODEL_INFERENCE_FAILED", "Image inference failed") from exc
        payload = result.to_dict()
        return (
            thumbnail_key,
            dict(result.species_counts),
            tuple(dict(item) for item in payload["detections"]),
            None,
            result.model_version,
        )

    def _process_video(
        self, local_path: Path
    ) -> tuple[dict[str, int], tuple[dict[str, object], ...], int, str]:
        try:
            result = self._video_inference.classify_video(local_path)
        except VideoProcessingError:
            raise
        except Exception as exc:
            raise ProcessingError("MODEL_INFERENCE_FAILED", "Video inference failed") from exc
        payload = result.to_dict()
        return (
            dict(result.species_counts),
            tuple(dict(item) for item in payload["detections"]),
            len(result.sampled_timestamps),
            result.model_version,
        )

    @staticmethod
    def _safe_error_code(exc: Exception) -> str:
        if isinstance(exc, (ProcessingError, MediaValidationError, VideoProcessingError)):
            return exc.code
        return "PROCESSING_FAILED"
