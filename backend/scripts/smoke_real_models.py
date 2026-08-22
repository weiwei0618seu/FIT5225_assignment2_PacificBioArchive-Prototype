"""Run both supplied models on real fixtures and write auditable JSON evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

from pacific_bioarchive.ml.runtime import RuntimeConfig, build_inference_service


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def parse_fixture(value: str) -> tuple[Path, str]:
    try:
        raw_path, expected = value.rsplit("=", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("fixture must be PATH=EXPECTED_TAG") from exc
    path = Path(raw_path)
    if not path.is_file() or not expected.strip():
        raise argparse.ArgumentTypeError(f"invalid fixture expectation: {value}")
    return path, expected.strip().lower()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--detector", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--source-classifier", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--fixture", action="append", type=parse_fixture, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    started = time.perf_counter()
    service = build_inference_service(
        RuntimeConfig(
            detector_path=args.detector,
            classifier_path=args.classifier,
            labels_path=args.labels,
            force_cpu=True,
        )
    )
    results: list[dict[str, object]] = []
    for fixture, expected_tag in args.fixture:
        fixture_started = time.perf_counter()
        result = service.classify_image(fixture)
        payload = result.to_dict()
        expected_counts = {expected_tag: 1}
        if payload["species_counts"] != expected_counts:
            raise RuntimeError(
                f"{fixture.name} expected {expected_counts!r}, got {payload['species_counts']}"
            )
        results.append(
            {
                "fixture": fixture.as_posix(),
                "fixture_sha256": sha256_file(fixture),
                "expected_tag": expected_tag,
                "elapsed_seconds": round(time.perf_counter() - fixture_started, 3),
                **payload,
            }
        )

    evidence = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "force_cpu": True,
        "source_artifacts": {
            "detector": {"path": args.detector.as_posix(), "sha256": sha256_file(args.detector)},
            "source_classifier": {
                "path": args.source_classifier.as_posix(),
                "sha256": sha256_file(args.source_classifier),
            },
            "classifier_torchscript": {
                "path": args.classifier.as_posix(),
                "sha256": sha256_file(args.classifier),
            },
            "labels": {"path": args.labels.as_posix(), "sha256": sha256_file(args.labels)},
        },
        "total_elapsed_seconds": round(time.perf_counter() - started, 3),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
