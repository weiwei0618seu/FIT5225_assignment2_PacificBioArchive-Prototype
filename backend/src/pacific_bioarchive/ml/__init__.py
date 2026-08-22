"""Reusable wildlife detection and species-classification services."""

from .inference import WildlifeInferenceService
from .labels import SpeciesLabel, SpeciesLabelMap, normalize_tag
from .types import (
    BoundingBox,
    ClassifierPrediction,
    DetectionCandidate,
    InferenceResult,
    SpeciesDetection,
)

__all__ = [
    "BoundingBox",
    "ClassifierPrediction",
    "DetectionCandidate",
    "InferenceResult",
    "SpeciesDetection",
    "SpeciesLabel",
    "SpeciesLabelMap",
    "WildlifeInferenceService",
    "normalize_tag",
]

