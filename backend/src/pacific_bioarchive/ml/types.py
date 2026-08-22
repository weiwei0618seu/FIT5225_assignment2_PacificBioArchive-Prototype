"""Typed, serializable ML inference contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from PIL import Image


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Normalized MegaDetector `x, y, width, height` coordinates."""

    x: float
    y: float
    width: float
    height: float

    def clamped(self) -> BoundingBox:
        original_left = float(self.x)
        original_top = float(self.y)
        original_right = original_left + max(float(self.width), 0.0)
        original_bottom = original_top + max(float(self.height), 0.0)
        left = min(max(original_left, 0.0), 1.0)
        top = min(max(original_top, 0.0), 1.0)
        right = min(max(original_right, 0.0), 1.0)
        bottom = min(max(original_bottom, 0.0), 1.0)
        return BoundingBox(
            x=left,
            y=top,
            width=max(right - left, 0.0),
            height=max(bottom - top, 0.0),
        )


@dataclass(frozen=True, slots=True)
class DetectionCandidate:
    bbox: BoundingBox
    confidence: float


@dataclass(frozen=True, slots=True)
class ClassifierPrediction:
    class_name: str
    confidence: float


@dataclass(frozen=True, slots=True)
class SpeciesDetection:
    species: str
    scientific_name: str
    detection_confidence: float
    classification_confidence: float
    combined_confidence: float
    bbox_pixels: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class InferenceResult:
    species_counts: dict[str, int]
    detections: tuple[SpeciesDetection, ...]
    model_version: str

    def to_dict(self) -> dict[str, object]:
        return {
            "species_counts": dict(self.species_counts),
            "detections": [asdict(detection) for detection in self.detections],
            "model_version": self.model_version,
        }


class AnimalDetector(Protocol):
    def detect(self, image: Image.Image, *, image_id: str) -> Sequence[DetectionCandidate]:
        """Return normalized animal bounding boxes."""


class SpeciesClassifier(Protocol):
    def classify(self, image: Image.Image) -> ClassifierPrediction:
        """Classify a cropped animal image."""


ImagePath = str | Path
