"""Exact one-frame-per-second video sampling and inference aggregation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from math import ceil, isfinite
from pathlib import Path
from typing import Protocol

from PIL import Image

from pacific_bioarchive.ml.types import InferenceResult, SpeciesDetection


class VideoProcessingError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class VideoFrame:
    timestamp_seconds: int
    image: Image.Image


@dataclass(frozen=True, slots=True)
class TimedSpeciesDetection:
    timestamp_seconds: int
    detection: SpeciesDetection


@dataclass(frozen=True, slots=True)
class VideoInferenceResult:
    species_counts: dict[str, int]
    detections: tuple[TimedSpeciesDetection, ...]
    sampled_timestamps: tuple[int, ...]
    model_version: str

    def to_dict(self) -> dict[str, object]:
        return {
            "species_counts": dict(self.species_counts),
            "detections": [
                {
                    "timestamp_seconds": item.timestamp_seconds,
                    **asdict(item.detection),
                }
                for item in self.detections
            ],
            "sampled_timestamps": list(self.sampled_timestamps),
            "video_samples": len(self.sampled_timestamps),
            "model_version": self.model_version,
        }


class FrameSampler(Protocol):
    def sample(self, video_path: str | Path) -> Sequence[VideoFrame]:
        """Return exactly one decoded frame at each whole second."""


class ImageInference(Protocol):
    def classify_pil(self, image: Image.Image, *, image_id: str) -> InferenceResult:
        """Classify one decoded video frame."""


def whole_second_timestamps(duration_seconds: float, *, max_samples: int = 30) -> tuple[int, ...]:
    """Return `0, 1, ...` timestamps strictly below the video duration."""

    if not isfinite(duration_seconds) or duration_seconds <= 0:
        raise VideoProcessingError("INVALID_VIDEO_DURATION", "Video duration must be positive")
    required = ceil(duration_seconds)
    if required > max_samples:
        raise VideoProcessingError(
            "VIDEO_TOO_LONG",
            f"Video requires {required} samples, exceeding the {max_samples}-sample limit",
        )
    return tuple(range(required))


class OpenCVFrameSampler:
    def __init__(self, *, max_samples: int = 30) -> None:
        if max_samples < 1:
            raise ValueError("max_samples must be positive")
        self._max_samples = max_samples

    def sample(self, video_path: str | Path) -> tuple[VideoFrame, ...]:
        import cv2

        path = str(video_path)
        capture = cv2.VideoCapture(path)
        if not capture.isOpened():
            capture.release()
            raise VideoProcessingError("INVALID_VIDEO", "The uploaded video cannot be opened")
        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS))
            frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            if not isfinite(fps) or fps <= 0 or not isfinite(frame_count) or frame_count <= 0:
                raise VideoProcessingError(
                    "INVALID_VIDEO_METADATA", "Video frame rate or frame count is invalid"
                )
            timestamps = whole_second_timestamps(
                frame_count / fps, max_samples=self._max_samples
            )
            frames: list[VideoFrame] = []
            for timestamp in timestamps:
                capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
                success, bgr_frame = capture.read()
                if not success or bgr_frame is None:
                    raise VideoProcessingError(
                        "VIDEO_FRAME_READ_FAILED",
                        f"Unable to decode the frame at second {timestamp}",
                    )
                rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
                frames.append(
                    VideoFrame(timestamp_seconds=timestamp, image=Image.fromarray(rgb_frame))
                )
            return tuple(frames)
        finally:
            capture.release()


class VideoInferenceService:
    """Classify 1 fps samples and avoid counting one persistent animal repeatedly."""

    def __init__(self, *, sampler: FrameSampler, image_inference: ImageInference) -> None:
        self._sampler = sampler
        self._image_inference = image_inference

    def classify_video(self, video_path: str | Path) -> VideoInferenceResult:
        path = Path(video_path)
        frames = self._sampler.sample(path)
        if not frames:
            raise VideoProcessingError("NO_VIDEO_FRAMES", "Video produced no one-second samples")

        maximum_counts: dict[str, int] = {}
        timed_detections: list[TimedSpeciesDetection] = []
        model_version: str | None = None
        previous_timestamp = -1
        for frame in frames:
            if frame.timestamp_seconds <= previous_timestamp:
                raise VideoProcessingError(
                    "INVALID_SAMPLE_ORDER", "Video frame timestamps must be strictly increasing"
                )
            previous_timestamp = frame.timestamp_seconds
            result = self._image_inference.classify_pil(
                frame.image,
                image_id=f"{path}#t={frame.timestamp_seconds}",
            )
            if model_version is None:
                model_version = result.model_version
            elif model_version != result.model_version:
                raise RuntimeError("Model version changed during video inference")
            for species, count in result.species_counts.items():
                maximum_counts[species] = max(maximum_counts.get(species, 0), int(count))
            timed_detections.extend(
                TimedSpeciesDetection(frame.timestamp_seconds, detection)
                for detection in result.detections
            )

        return VideoInferenceResult(
            species_counts=dict(sorted(maximum_counts.items())),
            detections=tuple(timed_detections),
            sampled_timestamps=tuple(frame.timestamp_seconds for frame in frames),
            model_version=model_version or "unknown",
        )

