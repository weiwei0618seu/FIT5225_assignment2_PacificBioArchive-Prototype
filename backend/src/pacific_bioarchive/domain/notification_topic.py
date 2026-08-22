"""SNS-facing notification topic port."""

from __future__ import annotations

from typing import Protocol

from pacific_bioarchive.domain.notifications import SubscriptionStatus


class NotificationTopic(Protocol):
    def subscribe_email(self, email: str, *, tags: tuple[str, ...]) -> str: ...

    def set_filter(self, subscription_arn: str, *, tags: tuple[str, ...]) -> None: ...

    def get_status(self, subscription_arn: str) -> SubscriptionStatus: ...

    def unsubscribe(self, subscription_arn: str) -> None: ...

    def publish(
        self,
        *,
        event_id: str,
        file_id: str,
        filename: str,
        tags: tuple[str, ...],
    ) -> None: ...
