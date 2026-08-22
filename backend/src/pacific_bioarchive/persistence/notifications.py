"""In-memory and DynamoDB notification state adapters."""

from __future__ import annotations

from threading import RLock
from typing import Any

from pacific_bioarchive.domain.notifications import (
    NotificationSubscription,
    SubscriptionStatus,
)
from pacific_bioarchive.domain.repositories import ConflictError
from pacific_bioarchive.persistence.dynamodb import _is_conditional_failure


def subscription_to_item(subscription: NotificationSubscription) -> dict[str, object]:
    return {
        "user_sub": subscription.user_sub,
        "email": subscription.email,
        "tags": list(subscription.tags),
        "sns_subscription_arn": subscription.sns_subscription_arn,
        "status": subscription.status.value,
        "updated_at": subscription.updated_at,
        "version": subscription.version,
    }


def subscription_from_item(item: dict[str, Any]) -> NotificationSubscription:
    return NotificationSubscription(
        user_sub=item["user_sub"],
        email=item["email"],
        tags=tuple(item["tags"]),
        sns_subscription_arn=item["sns_subscription_arn"],
        status=SubscriptionStatus(item["status"]),
        updated_at=item["updated_at"],
        version=int(item["version"]),
    )


class InMemorySubscriptionRepository:
    def __init__(self) -> None:
        self._items: dict[str, NotificationSubscription] = {}
        self._lock = RLock()

    def get(self, user_sub: str) -> NotificationSubscription | None:
        with self._lock:
            return self._items.get(user_sub)

    def save(
        self,
        subscription: NotificationSubscription,
        *,
        expected_version: int | None,
    ) -> None:
        with self._lock:
            current = self._items.get(subscription.user_sub)
            if expected_version is None:
                if current is not None:
                    raise ConflictError("Notification subscription already exists")
            elif current is None or current.version != expected_version:
                raise ConflictError("Notification subscription version conflict")
            self._items[subscription.user_sub] = subscription

    def delete(self, user_sub: str) -> NotificationSubscription | None:
        with self._lock:
            return self._items.pop(user_sub, None)


class InMemoryNotificationEventRepository:
    def __init__(self) -> None:
        self._events: set[str] = set()
        self._lock = RLock()

    def claim(self, event_id: str) -> bool:
        with self._lock:
            if event_id in self._events:
                return False
            self._events.add(event_id)
            return True

    def release(self, event_id: str) -> None:
        with self._lock:
            self._events.discard(event_id)


class DynamoSubscriptionRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def get(self, user_sub: str) -> NotificationSubscription | None:
        response = self._table.get_item(Key={"user_sub": user_sub}, ConsistentRead=True)
        item = response.get("Item")
        return subscription_from_item(item) if item else None

    def save(
        self,
        subscription: NotificationSubscription,
        *,
        expected_version: int | None,
    ) -> None:
        if expected_version is None:
            expression = "attribute_not_exists(user_sub)"
            values = None
        else:
            expression = "#version = :expected"
            values = {":expected": expected_version}
        kwargs: dict[str, object] = {
            "Item": subscription_to_item(subscription),
            "ConditionExpression": expression,
        }
        if values is not None:
            kwargs["ExpressionAttributeNames"] = {"#version": "version"}
            kwargs["ExpressionAttributeValues"] = values
        try:
            self._table.put_item(**kwargs)
        except Exception as exc:
            if _is_conditional_failure(exc):
                raise ConflictError("Notification subscription conflict") from exc
            raise

    def delete(self, user_sub: str) -> NotificationSubscription | None:
        response = self._table.delete_item(
            Key={"user_sub": user_sub}, ReturnValues="ALL_OLD"
        )
        item = response.get("Attributes")
        return subscription_from_item(item) if item else None


class DynamoNotificationEventRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def claim(self, event_id: str) -> bool:
        try:
            self._table.put_item(
                Item={"event_id": event_id},
                ConditionExpression="attribute_not_exists(event_id)",
            )
        except Exception as exc:
            if _is_conditional_failure(exc):
                return False
            raise
        return True

    def release(self, event_id: str) -> None:
        self._table.delete_item(Key={"event_id": event_id})
