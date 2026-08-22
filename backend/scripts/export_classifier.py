"""Convert the supplied onnx2torch pickle into runtime-only TorchScript."""

from __future__ import annotations

import argparse
from pathlib import Path


def export_classifier(source: Path, destination: Path) -> tuple[int, ...]:
    import onnx2torch  # noqa: F401 - required while unpickling converter classes
    import torch

    model = torch.load(source, map_location="cpu", weights_only=False)
    model.eval()
    sample = torch.zeros((1, 480, 480, 3), dtype=torch.float32)
    with torch.inference_mode():
        expected = model(sample)
        traced = torch.jit.trace(model, sample, strict=False)
        traced = torch.jit.freeze(traced.eval())
        actual = traced(sample)
    if tuple(expected.shape) != (1, 46) or tuple(actual.shape) != (1, 46):
        raise RuntimeError(
            f"Classifier output must be [1, 46], got {tuple(expected.shape)} and {tuple(actual.shape)}"
        )
    if not torch.allclose(expected, actual, rtol=1e-4, atol=1e-5):
        raise RuntimeError("TorchScript output changed during conversion")
    destination.parent.mkdir(parents=True, exist_ok=True)
    torch.jit.save(traced, destination)
    return tuple(actual.shape)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    shape = export_classifier(args.source, args.destination)
    print(f"exported classifier {args.destination} with output shape {shape}")


if __name__ == "__main__":
    main()
