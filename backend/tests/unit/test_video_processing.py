from __future__ import annotations

from collections import deque
from pathlib import Path
import unittest

from PIL import Image

from pacific_bioarchive.media.video_processing import (
    VideoFrame,
    VideoInferenceService,
    VideoProcessingError,
    whole_second_timestamps,
)
from pacific_bioarchive.ml.types import InferenceResult, SpeciesDetection


def detection(species: str) -> SpeciesDetection:
    return SpeciesDetection(
        species=species,
        scientific_name=species.title().replace(" ", "_"),
        detection_confidence=0.9,
        classification_confidence=0.8,
        combined_confidence=0.72,
        bbox_pixels=(0, 0, 10, 10),
    )


class FakeSampler:
    def __init__(self, timestamps: list[int]) -> None:
        self.frames = tuple(
            VideoFrame(timestamp, Image.new("RGB", (20, 10), "white"))
            for timestamp in timestamps
        )

    def sample(self, video_path: str | Path) -> tuple[VideoFrame, ...]:
        return self.frames


class FakeInference:
    def __init__(self, results: list[InferenceResult]) -> None:
        self.results = deque(results)
        self.image_ids: list[str] = []

    def classify_pil(self, image: Image.Image, *, image_id: str) -> InferenceResult:
        self.image_ids.append(image_id)
        return self.results.popleft()


class VideoTimestampTests(unittest.TestCase):
    def test_exact_one_frame_per_whole_second(self) -> None:
        self.assertEqual(whole_second_timestamps(0.01), (0,))
        self.assertEqual(whole_second_timestamps(1.0), (0,))
        self.assertEqual(whole_second_timestamps(3.0), (0, 1, 2))
        self.assertEqual(whole_second_timestamps(3.01), (0, 1, 2, 3))

    def test_invalid_and_overlong_durations_are_rejected(self) -> None:
        for invalid in (0, -1, float("inf"), float("nan")):
            with self.subTest(invalid=invalid), self.assertRaises(VideoProcessingError):
                whole_second_timestamps(invalid)
        with self.assertRaises(VideoProcessingError) as too_long:
            whole_second_timestamps(30.01, max_samples=30)
        self.assertEqual(too_long.exception.code, "VIDEO_TOO_LONG")


class VideoInferenceTests(unittest.TestCase):
    def test_uses_maximum_simultaneous_count_not_cross_frame_sum(self) -> None:
        results = [
            InferenceResult({"dingo": 1}, (detection("dingo"),), "test-v1"),
            InferenceResult(
                {"dingo": 2, "australian magpie": 1},
                (detection("dingo"), detection("dingo"), detection("australian magpie")),
                "test-v1",
            ),
            InferenceResult({"dingo": 1}, (detection("dingo"),), "test-v1"),
        ]
        inference = FakeInference(results)
        service = VideoInferenceService(
            sampler=FakeSampler([0, 1, 2]), image_inference=inference
        )

        result = service.classify_video("clip.mp4")

        self.assertEqual(result.species_counts, {"australian magpie": 1, "dingo": 2})
        self.assertEqual(result.sampled_timestamps, (0, 1, 2))
        self.assertEqual(len(result.detections), 5)
        self.assertEqual(result.to_dict()["video_samples"], 3)
        self.assertEqual(
            inference.image_ids,
            ["clip.mp4#t=0", "clip.mp4#t=1", "clip.mp4#t=2"],
        )

    def test_empty_or_disordered_samples_are_rejected(self) -> None:
        with self.assertRaises(VideoProcessingError) as empty:
            VideoInferenceService(
                sampler=FakeSampler([]), image_inference=FakeInference([])
            ).classify_video("empty.mp4")
        self.assertEqual(empty.exception.code, "NO_VIDEO_FRAMES")

        results = [InferenceResult({}, (), "v1"), InferenceResult({}, (), "v1")]
        with self.assertRaises(VideoProcessingError) as order:
            VideoInferenceService(
                sampler=FakeSampler([1, 1]), image_inference=FakeInference(results)
            ).classify_video("bad.mp4")
        self.assertEqual(order.exception.code, "INVALID_SAMPLE_ORDER")

    def test_model_version_cannot_change_mid_video(self) -> None:
        results = [InferenceResult({}, (), "v1"), InferenceResult({}, (), "v2")]
        with self.assertRaisesRegex(RuntimeError, "Model version changed"):
            VideoInferenceService(
                sampler=FakeSampler([0, 1]), image_inference=FakeInference(results)
            ).classify_video("version.mp4")


if __name__ == "__main__":
    unittest.main()

