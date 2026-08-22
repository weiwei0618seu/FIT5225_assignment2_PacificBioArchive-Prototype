"""Parse and normalize the supplied classifier label map."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_WHITESPACE = re.compile(r"\s+")
_TAG_PUNCTUATION = re.compile(r"[^a-z0-9]+")


def normalize_tag(value: str) -> str:
    """Return a stable lowercase tag while preserving readable word spacing."""

    normalized = _TAG_PUNCTUATION.sub(" ", value.strip().lower())
    return _WHITESPACE.sub(" ", normalized).strip()


@dataclass(frozen=True, slots=True)
class SpeciesLabel:
    identifier: str
    scientific_name: str
    common_name: str
    canonical_tag: str


class SpeciesLabelMap:
    """Ordered mapping matching the 46 outputs of the supplied classifier."""

    def __init__(self, labels: list[SpeciesLabel]) -> None:
        if not labels:
            raise ValueError("At least one species label is required")
        scientific_keys = [label.scientific_name.lower() for label in labels]
        if len(scientific_keys) != len(set(scientific_keys)):
            raise ValueError("Scientific class names must be unique")
        self._labels = tuple(labels)
        self._by_scientific = {
            label.scientific_name.lower(): label for label in self._labels
        }

    @classmethod
    def from_file(cls, path: str | Path) -> SpeciesLabelMap:
        rows: list[SpeciesLabel] = []
        for line_number, raw_line in enumerate(
            Path(path).read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw_line.strip():
                continue
            fields = [field.strip() for field in raw_line.split(";")]
            if len(fields) != 7:
                raise ValueError(
                    f"Invalid label row {line_number}: expected 7 fields, got {len(fields)}"
                )
            identifier, _class, _order, _family, genus, species, common = fields
            scientific = f"{genus}_{species}".rstrip("_")
            canonical = normalize_tag(common or scientific.replace("_", " "))
            if not identifier or not scientific or not canonical:
                raise ValueError(f"Invalid label row {line_number}: missing identity")
            rows.append(
                SpeciesLabel(
                    identifier=identifier,
                    scientific_name=scientific,
                    common_name=common,
                    canonical_tag=canonical,
                )
            )
        return cls(rows)

    @property
    def class_names(self) -> tuple[str, ...]:
        return tuple(label.scientific_name for label in self._labels)

    def by_index(self, index: int) -> SpeciesLabel:
        try:
            return self._labels[index]
        except IndexError as exc:
            raise ValueError(f"Unknown classifier output index: {index}") from exc

    def resolve(self, scientific_name: str) -> SpeciesLabel:
        key = scientific_name.strip().lower()
        try:
            return self._by_scientific[key]
        except KeyError as exc:
            raise ValueError(f"Unsupported classifier class: {scientific_name}") from exc

    def __len__(self) -> int:
        return len(self._labels)

