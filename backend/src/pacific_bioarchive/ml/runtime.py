"""Lazy adapters for the supplied MegaDetector and onnx2torch classifier."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

import numpy as np
from PIL import Image

from .inference import WildlifeInferenceService
from .labels import SpeciesLabelMap
from .types import BoundingBox, ClassifierPrediction, DetectionCandidate


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    detector_path: Path
    classifier_path: Path
    labels_path: Path
    model_version: str = "supplied-v1"
    detection_threshold: float = 0.05
    classification_threshold: float = 0.0
    force_cpu: bool = True

    @classmethod
    def from_environment(cls) -> RuntimeConfig:
        return cls(
            detector_path=Path(os.environ["PBA_DETECTOR_MODEL_PATH"]),
            classifier_path=Path(os.environ["PBA_CLASSIFIER_MODEL_PATH"]),
            labels_path=Path(os.environ["PBA_LABELS_PATH"]),
            model_version=os.getenv("PBA_MODEL_VERSION", "supplied-v1"),
            detection_threshold=float(os.getenv("PBA_DETECTION_THRESHOLD", "0.05")),
            classification_threshold=float(
                os.getenv("PBA_CLASSIFICATION_THRESHOLD", "0.0")
            ),
            force_cpu=os.getenv("PBA_FORCE_CPU", "true").lower() not in {"0", "false", "no"},
        )


class MegaDetectorRuntime:
    def __init__(self, model_path: Path, *, force_cpu: bool = True) -> None:
        self._model_path = model_path
        self._force_cpu = force_cpu
        self._detector: Any | None = None
        self._lock = Lock()

    def _load(self) -> Any:
        if self._detector is None:
            with self._lock:
                if self._detector is None:
                    from megadetector.detection.run_detector import load_detector

                    self._detector = load_detector(
                        str(self._model_path), force_cpu=self._force_cpu
                    )
        return self._detector

    def detect(self, image: Image.Image, *, image_id: str) -> list[DetectionCandidate]:
        result = self._load().generate_detections_one_image(
            image,
            image_id=image_id,
            detection_threshold=0.00001,
        )
        if result.get("failure"):
            raise RuntimeError(f"MegaDetector failed: {result['failure']}")
        candidates: list[DetectionCandidate] = []
        for detection in result.get("detections", []):
            if str(detection.get("category")) != "1":
                continue
            bbox = detection.get("bbox", [])
            if len(bbox) != 4:
                continue
            candidates.append(
                DetectionCandidate(
                    bbox=BoundingBox(*(float(value) for value in bbox)),
                    confidence=float(detection["conf"]),
                )
            )
        return candidates


class TorchSpeciesClassifierRuntime:
    def __init__(self, model_path: Path, labels: SpeciesLabelMap, *, force_cpu: bool) -> None:
        self._model_path = model_path
        self._labels = labels
        self._force_cpu = force_cpu
        self._torch: Any | None = None
        self._model: Any | None = None
        self._device = "cpu"
        self._lock = Lock()

    def _load(self) -> tuple[Any, Any]:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    import torch

                    if not self._force_cpu and torch.cuda.is_available():
                        self._device = "cuda"
                    self._model = torch.jit.load(str(self._model_path), map_location=self._device)
                    self._model.eval()
                    self._model.to(self._device)
                    self._torch = torch
        return self._torch, self._model

    def classify(self, image: Image.Image) -> ClassifierPrediction:
        torch, model = self._load()
        resized = image.convert("RGB").resize((480, 480), Image.Resampling.BILINEAR)
        pixels = np.asarray(resized, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(pixels).unsqueeze(0).to(self._device)
        with torch.no_grad():
            logits = model(tensor)
            probabilities = torch.softmax(logits, dim=1)[0]
            confidence, index = torch.max(probabilities, dim=0)
        label = self._labels.by_index(int(index.item()))
        return ClassifierPrediction(
            class_name=label.scientific_name,
            confidence=float(confidence.item()),
        )


def build_inference_service(config: RuntimeConfig) -> WildlifeInferenceService:
    for path in (config.detector_path, config.classifier_path, config.labels_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required ML artifact not found: {path}")
    labels = SpeciesLabelMap.from_file(config.labels_path)
    return WildlifeInferenceService(
        detector=MegaDetectorRuntime(config.detector_path, force_cpu=config.force_cpu),
        classifier=TorchSpeciesClassifierRuntime(
            config.classifier_path, labels, force_cpu=config.force_cpu
        ),
        labels=labels,
        model_version=config.model_version,
        detection_threshold=config.detection_threshold,
        classification_threshold=config.classification_threshold,
    )
