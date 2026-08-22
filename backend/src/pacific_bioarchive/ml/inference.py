"""Framework-neutral wildlife inference orchestration."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from PIL import Image, ImageOps

from .labels import SpeciesLabelMap
from .types import (
    AnimalDetector,
    ImagePath,
    InferenceResult,
    SpeciesClassifier,
    SpeciesDetection,
)


class WildlifeInferenceService:
    """Detect animals, classify each crop, and return structured counts."""

    def __init__(
        self,
        *,
        detector: AnimalDetector,
        classifier: SpeciesClassifier,
        labels: SpeciesLabelMap,
        model_version: str,
        detection_threshold: float = 0.05,
        classification_threshold: float = 0.0,
        max_detections: int = 100,
    ) -> None:
        if not 0.0 <= detection_threshold <= 1.0:
            raise ValueError("detection_threshold must be between 0 and 1")
        if not 0.0 <= classification_threshold <= 1.0:
            raise ValueError("classification_threshold must be between 0 and 1")
        if max_detections < 1:
            raise ValueError("max_detections must be positive")
        if not model_version.strip():
            raise ValueError("model_version is required")
        self._detector = detector
        self._classifier = classifier
        self._labels = labels
        self._model_version = model_version.strip()
        self._detection_threshold = detection_threshold
        self._classification_threshold = classification_threshold
        self._max_detections = max_detections

    def classify_image(self, image_path: ImagePath) -> InferenceResult:
        path = Path(image_path)
        with Image.open(path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
        return self.classify_pil(image, image_id=str(path))

    def classify_pil(self, image: Image.Image, *, image_id: str) -> InferenceResult:
        source = ImageOps.exif_transpose(image).convert("RGB")
        candidates = sorted(
            self._detector.detect(source, image_id=image_id),
            key=lambda candidate: candidate.confidence,
            reverse=True,
        )[: self._max_detections]

        counts: Counter[str] = Counter()
        detections: list[SpeciesDetection] = []
        for candidate in candidates:
            detector_confidence = float(candidate.confidence)
            if detector_confidence < self._detection_threshold:
                continue
            box = candidate.bbox.clamped()
            left = round(box.x * source.width)
            top = round(box.y * source.height)
            right = round((box.x + box.width) * source.width)
            bottom = round((box.y + box.height) * source.height)
            if right <= left or bottom <= top:
                continue
            crop = source.crop((left, top, right, bottom))
            prediction = self._classifier.classify(crop)
            classifier_confidence = float(prediction.confidence)
            if classifier_confidence < self._classification_threshold:
                continue
            label = self._labels.resolve(prediction.class_name)
            counts[label.canonical_tag] += 1
            detections.append(
                SpeciesDetection(
                    species=label.canonical_tag,
                    scientific_name=label.scientific_name,
                    detection_confidence=round(detector_confidence, 6),
                    classification_confidence=round(classifier_confidence, 6),
                    combined_confidence=round(
                        detector_confidence * classifier_confidence, 6
                    ),
                    bbox_pixels=(left, top, right, bottom),
                )
            )

        return InferenceResult(
            species_counts=dict(sorted(counts.items())),
            detections=tuple(detections),
            model_version=self._model_version,
        )

