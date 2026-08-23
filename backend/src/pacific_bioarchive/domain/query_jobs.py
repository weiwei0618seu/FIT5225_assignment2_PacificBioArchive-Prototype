"""Short-lived state for asynchronous temporary image queries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum

from pacific_bioarchive.domain.media import utc_now
from pacific_bioarchive.ml.labels import normalize_tag


class TemporaryQueryStatus(StrEnum):
    AWAITING_UPLOAD = "AWAITING_UPLOAD"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class TemporaryQueryJob:
    query_id: str
    owner_sub: str
    temp_key: str
    status: TemporaryQueryStatus = TemporaryQueryStatus.AWAITING_UPLOAD
    species_counts: Mapping[str, int] | None = None
    model_version: str | None = None
    matched_file_ids: tuple[str, ...] = ()
    total: int = 0
    truncated: bool = False
    error_code: str | None = None
    created_at: str = ""
    updated_at: str = ""
    expires_at: int = 0
    version: int = 1

    def __post_init__(self) -> None:
        required = {
            "query_id": self.query_id,
            "owner_sub": self.owner_sub,
            "temp_key": self.temp_key,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise ValueError(f"Missing required temporary-query fields: {', '.join(missing)}")
        if "/" in self.query_id or "\\" in self.query_id or ".." in self.query_id:
            raise ValueError("query_id is unsafe")
        if not self.temp_key.startswith("query-temp/"):
            raise ValueError("temp_key must use the query-temp prefix")
        if self.expires_at < 1:
            raise ValueError("expires_at must be a positive epoch timestamp")
        if self.version < 1:
            raise ValueError("version must be positive")
        if self.total < 0:
            raise ValueError("total cannot be negative")

        normalized_counts: dict[str, int] = {}
        for raw_tag, raw_count in (self.species_counts or {}).items():
            tag = normalize_tag(str(raw_tag))
            count = int(raw_count)
            if not tag or count < 1:
                raise ValueError("species_counts require non-empty tags and positive counts")
            normalized_counts[tag] = count
        object.__setattr__(self, "species_counts", dict(sorted(normalized_counts.items())))

        file_ids = tuple(str(value).strip() for value in self.matched_file_ids)
        if any(not value or "/" in value or "\\" in value for value in file_ids):
            raise ValueError("matched_file_ids contain an unsafe identifier")
        if len(file_ids) != len(set(file_ids)):
            raise ValueError("matched_file_ids must be unique")
        if len(file_ids) > self.total:
            raise ValueError("matched_file_ids cannot exceed total")
        object.__setattr__(self, "matched_file_ids", file_ids)

        if not self.created_at:
            object.__setattr__(self, "created_at", utc_now())
        if not self.updated_at:
            object.__setattr__(self, "updated_at", self.created_at)

        if self.status == TemporaryQueryStatus.READY:
            if not self.model_version or not self.model_version.strip():
                raise ValueError("READY temporary queries require a model_version")
            if self.error_code is not None:
                raise ValueError("READY temporary queries cannot have an error_code")
            object.__setattr__(self, "model_version", self.model_version.strip())
        elif self.status == TemporaryQueryStatus.FAILED:
            if not self.error_code or not self.error_code.strip():
                raise ValueError("FAILED temporary queries require an error_code")
            object.__setattr__(self, "error_code", self.error_code.strip())
        elif self.error_code is not None:
            raise ValueError("Non-terminal temporary queries cannot have an error_code")

    def mark_processing(self, *, now: str | None = None) -> TemporaryQueryJob:
        if self.status in {TemporaryQueryStatus.READY, TemporaryQueryStatus.FAILED}:
            return self
        return replace(
            self,
            status=TemporaryQueryStatus.PROCESSING,
            error_code=None,
            updated_at=now or utc_now(),
            version=self.version + 1,
        )

    def mark_ready(
        self,
        *,
        species_counts: Mapping[str, int],
        model_version: str,
        matched_file_ids: tuple[str, ...],
        total: int,
        truncated: bool,
        now: str | None = None,
    ) -> TemporaryQueryJob:
        return replace(
            self,
            status=TemporaryQueryStatus.READY,
            species_counts=species_counts,
            model_version=model_version,
            matched_file_ids=matched_file_ids,
            total=total,
            truncated=truncated,
            error_code=None,
            updated_at=now or utc_now(),
            version=self.version + 1,
        )

    def mark_failed(
        self, error_code: str, *, now: str | None = None
    ) -> TemporaryQueryJob:
        return replace(
            self,
            status=TemporaryQueryStatus.FAILED,
            species_counts={},
            model_version=None,
            matched_file_ids=(),
            total=0,
            truncated=False,
            error_code=error_code,
            updated_at=now or utc_now(),
            version=self.version + 1,
        )
