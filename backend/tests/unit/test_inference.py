from __future__ import annotations

import unittest
from collections import deque
from pathlib import Path

from pacific_bioarchive.ml.inference import WildlifeInferenceService
from pacific_bioarchive.ml.labels import SpeciesLabelMap
from pacific_bioarchive.ml.types import (
    BoundingBox,
    ClassifierPrediction,
    DetectionCandidate,
)
from PIL import Image

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
LABELS_PATH = REPOSITORY_ROOT / "legacy" / "PacificBioArchive" / "labels.txt"


class FakeDetector:
    def __init__(self, candidates: list[DetectionCandidate]) -> None:
        self.candidates = candidates
        self.image_ids: list[str] = []

    def detect(self, image: Image.Image, *, image_id: str) -> list[DetectionCandidate]:
        self.image_ids.append(image_id)
        return self.candidates


class FakeClassifier:
    def __init__(self, predictions: list[ClassifierPrediction]) -> None:
        self.predictions = deque(predictions)
        self.crop_sizes: list[tuple[int, int]] = []

    def classify(self, image: Image.Image) -> ClassifierPrediction:
        self.crop_sizes.append(image.size)
        return self.predictions.popleft()


class WildlifeInferenceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.labels = SpeciesLabelMap.from_file(LABELS_PATH)
        self.image = Image.new("RGB", (1000, 500), "white")

    def build_service(
        self,
        candidates: list[DetectionCandidate],
        predictions: list[ClassifierPrediction],
        **kwargs: object,
    ) -> tuple[WildlifeInferenceService, FakeDetector, FakeClassifier]:
        detector = FakeDetector(candidates)
        classifier = FakeClassifier(predictions)
        service = WildlifeInferenceService(
            detector=detector,
            classifier=classifier,
            labels=self.labels,
            model_version="test-v1",
            **kwargs,
        )
        return service, detector, classifier

    def test_counts_multiple_animals_and_returns_structured_evidence(self) -> None:
        candidates = [
            DetectionCandidate(BoundingBox(0.1, 0.2, 0.2, 0.4), 0.9),
            DetectionCandidate(BoundingBox(0.5, 0.1, 0.3, 0.5), 0.8),
            DetectionCandidate(BoundingBox(0.0, 0.0, 0.1, 0.2), 0.7),
        ]
        predictions = [
            ClassifierPrediction("Canis_dingo", 0.95),
            ClassifierPrediction("Canis_familiaris", 0.75),
            ClassifierPrediction("Gymnorhina_tibicen", 0.85),
        ]
        service, detector, classifier = self.build_service(candidates, predictions)

        result = service.classify_pil(self.image, image_id="camera-1")

        self.assertEqual(result.species_counts, {"australian magpie": 1, "dingo": 2})
        self.assertEqual(len(result.detections), 3)
        self.assertEqual(result.model_version, "test-v1")
        self.assertEqual(detector.image_ids, ["camera-1"])
        self.assertEqual(classifier.crop_sizes[0], (200, 200))
        self.assertEqual(result.detections[0].bbox_pixels, (100, 100, 300, 300))
        self.assertEqual(result.detections[0].combined_confidence, 0.855)
        self.assertEqual(result.to_dict()["species_counts"], result.species_counts)

    def test_thresholds_skip_low_confidence_without_consuming_prediction(self) -> None:
        candidates = [
            DetectionCandidate(BoundingBox(0, 0, 0.5, 0.5), 0.01),
            DetectionCandidate(BoundingBox(0.5, 0.5, 0.5, 0.5), 0.9),
        ]
        predictions = [ClassifierPrediction("Bos_taurus", 0.4)]
        service, _, classifier = self.build_service(
            candidates,
            predictions,
            detection_threshold=0.05,
            classification_threshold=0.5,
        )

        result = service.classify_pil(self.image, image_id="threshold")

        self.assertEqual(result.species_counts, {})
        self.assertEqual(classifier.crop_sizes, [(500, 250)])

    def test_invalid_and_out_of_bounds_boxes_are_safe(self) -> None:
        candidates = [
            DetectionCandidate(BoundingBox(1.5, -1, 0.5, 2), 0.9),
            DetectionCandidate(BoundingBox(0.8, 0.8, -0.2, 0.1), 0.8),
            DetectionCandidate(BoundingBox(-0.1, 0.1, 0.5, 0.5), 0.7),
        ]
        predictions = [ClassifierPrediction("Felis_catus", 0.9)]
        service, _, _ = self.build_service(candidates, predictions)

        result = service.classify_pil(self.image, image_id="bounds")

        self.assertEqual(result.species_counts, {"domestic cat": 1})
        self.assertEqual(result.detections[0].bbox_pixels, (0, 50, 400, 300))

    def test_max_detections_is_deterministic_by_detector_confidence(self) -> None:
        candidates = [
            DetectionCandidate(BoundingBox(0, 0, 0.2, 0.2), 0.6),
            DetectionCandidate(BoundingBox(0.2, 0.2, 0.2, 0.2), 0.9),
        ]
        service, _, _ = self.build_service(
            candidates,
            [ClassifierPrediction("Sus_scrofa", 0.8)],
            max_detections=1,
        )

        result = service.classify_pil(self.image, image_id="bounded")

        self.assertEqual(result.species_counts, {"wild boar": 1})
        self.assertEqual(result.detections[0].detection_confidence, 0.9)

    def test_invalid_configuration_is_rejected(self) -> None:
        detector = FakeDetector([])
        classifier = FakeClassifier([])
        with self.assertRaises(ValueError):
            WildlifeInferenceService(
                detector=detector,
                classifier=classifier,
                labels=self.labels,
                model_version="",
            )


if __name__ == "__main__":
    unittest.main()

