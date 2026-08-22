"""Private object-storage port."""

from __future__ import annotations

from typing import Protocol


class ObjectStorage(Protocol):
    def delete(self, key: str) -> None:
        """Delete an object; missing keys must be treated as success."""

