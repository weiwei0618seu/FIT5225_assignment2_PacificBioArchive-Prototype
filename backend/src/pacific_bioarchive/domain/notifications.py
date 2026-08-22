"""Notification subscriptions and durable publish-deduplication contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Protocol

from pacific_bioarchive.domain.media import utc_now
from pacific_bioarchive.ml.labels import normalize_tag


class SubscriptionStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class NotificationSubscription:
    user_sub: str
    email: str
    tags: tuple[str, ...]
    sns_subscription_arn: str
    status: SubscriptionStatus
    updated_at: str = ""
    version: int = 1

    def __post_init__(self) -> None:
        if not self.user_sub.strip() or not self.email.strip():
            raise ValueError("user_sub and email are required")
        if not self.sns_subscription_arn.strip():
            raise ValueError("sns_subscription_arn is required")
        normalized = tuple(
            sorted({tag for raw in self.tags if (tag := normalize_tag(raw))})
        )
        if not normalized:
            raise ValueError("At least one notification tag is required")
        if self.version < 1:
            raise ValueError("version must be positive")
        object.__setattr__(self, "tags", normalized)
        if not self.updated_at:
            object.__setattr__(self, "updated_at", utc_now())

    def with_state(
        self,
        *,
        tags: tuple[str, ...] | None = None,
        status: SubscriptionStatus | None = None,
        now: str | None = None,
    ) -> NotificationSubscription:
        return replace(
            self,
            tags=tags if tags is not None else self.tags,
            status=status if status is not None else self.status,
            updated_at=now or utc_now(),
            version=self.version + 1,
        )


class SubscriptionRepository(Protocol):
    def get(self, user_sub: str) -> NotificationSubscription | None: ...

    def save(
        self,
        subscription: NotificationSubscription,
        *,
        expected_version: int | None,
    ) -> None: ...

    def delete(self, user_sub: str) -> NotificationSubscription | None: ...


class NotificationEventRepository(Protocol):
    def claim(self, event_id: str) -> bool: ...

    def release(self, event_id: str) -> None: ...
