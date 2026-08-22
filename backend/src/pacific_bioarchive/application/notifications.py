"""Verified-email subscriptions and deduplicated watched-tag publishing."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from hashlib import sha256

from pacific_bioarchive.domain.media import MediaRecord, ProcessingStatus
from pacific_bioarchive.domain.notification_topic import NotificationTopic
from pacific_bioarchive.domain.notifications import (
    NotificationEventRepository,
    NotificationSubscription,
    SubscriptionRepository,
)
from pacific_bioarchive.ml.labels import normalize_tag

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
LOGGER = logging.getLogger(__name__)


class NotificationValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class NotificationService:
    def __init__(
        self,
        *,
        subscription_repository: SubscriptionRepository,
        event_repository: NotificationEventRepository,
        topic: NotificationTopic,
        max_tags: int = 20,
        max_tag_length: int = 50,
    ) -> None:
        self._subscriptions = subscription_repository
        self._events = event_repository
        self._topic = topic
        self._max_tags = max_tags
        self._max_tag_length = max_tag_length

    def set_subscription(
        self,
        *,
        actor_sub: str,
        verified_email: str,
        email_verified: bool,
        tags: Iterable[str],
    ) -> NotificationSubscription:
        actor = actor_sub.strip()
        email = verified_email.strip().lower()
        if not actor:
            raise NotificationValidationError("UNAUTHENTICATED", "A Cognito subject is required")
        if email_verified is not True or not EMAIL_PATTERN.fullmatch(email):
            raise NotificationValidationError(
                "EMAIL_NOT_VERIFIED", "A verified Cognito email is required"
            )
        normalized = self._normalize_tags(tags)
        existing = self._subscriptions.get(actor)

        if existing is None:
            arn = self._topic.subscribe_email(email, tags=normalized)
            try:
                status = self._topic.get_status(arn)
                subscription = NotificationSubscription(
                    user_sub=actor,
                    email=email,
                    tags=normalized,
                    sns_subscription_arn=arn,
                    status=status,
                )
                self._subscriptions.save(subscription, expected_version=None)
            except Exception:
                self._cleanup_new_subscription(arn)
                raise
            return subscription

        if existing.email != email:
            arn = self._topic.subscribe_email(email, tags=normalized)
            try:
                status = self._topic.get_status(arn)
                replacement = NotificationSubscription(
                    user_sub=actor,
                    email=email,
                    tags=normalized,
                    sns_subscription_arn=arn,
                    status=status,
                    version=existing.version + 1,
                )
                self._subscriptions.save(replacement, expected_version=existing.version)
            except Exception:
                self._cleanup_new_subscription(arn)
                raise
            try:
                self._topic.unsubscribe(existing.sns_subscription_arn)
            except Exception:
                LOGGER.exception(
                    "Unable to remove replaced SNS subscription for %s", existing.user_sub
                )
            return replacement

        self._topic.set_filter(existing.sns_subscription_arn, tags=normalized)
        status = self._topic.get_status(existing.sns_subscription_arn)
        updated = existing.with_state(tags=normalized, status=status)
        self._subscriptions.save(updated, expected_version=existing.version)
        return updated

    def get_subscription(self, *, actor_sub: str) -> NotificationSubscription | None:
        subscription = self._subscriptions.get(actor_sub.strip())
        if subscription is None:
            return None
        status = self._topic.get_status(subscription.sns_subscription_arn)
        if status == subscription.status:
            return subscription
        updated = subscription.with_state(status=status)
        self._subscriptions.save(updated, expected_version=subscription.version)
        return updated

    def delete_subscription(self, *, actor_sub: str) -> bool:
        subscription = self._subscriptions.get(actor_sub.strip())
        if subscription is None:
            return False
        self._topic.unsubscribe(subscription.sns_subscription_arn)
        self._subscriptions.delete(subscription.user_sub)
        return True

    def _cleanup_new_subscription(self, subscription_arn: str) -> None:
        try:
            self._topic.unsubscribe(subscription_arn)
        except Exception:
            LOGGER.exception("Unable to roll back SNS subscription creation")

    def publish_for_record(
        self, record: MediaRecord, *, tags: Iterable[str] | None = None
    ) -> bool:
        if record.processing_status != ProcessingStatus.READY:
            return False
        requested = set(record.all_tags if tags is None else self._normalize_tags(tags))
        notify_tags = tuple(sorted(requested.intersection(record.all_tags)))
        if not notify_tags:
            return False
        tag_digest = sha256("\0".join(notify_tags).encode("utf-8")).hexdigest()[:16]
        event_id = f"{record.file_id}#{record.version}#{tag_digest}"
        if not self._events.claim(event_id):
            return False
        try:
            self._topic.publish(
                event_id=event_id,
                file_id=record.file_id,
                filename=record.filename,
                tags=notify_tags,
            )
        except Exception:
            self._events.release(event_id)
            raise
        return True

    def _normalize_tags(self, tags: Iterable[str]) -> tuple[str, ...]:
        raw_values = tuple(tags)
        if not raw_values or len(raw_values) > self._max_tags:
            raise NotificationValidationError(
                "INVALID_NOTIFICATION_TAGS",
                f"Provide between 1 and {self._max_tags} notification tags",
            )
        normalized: set[str] = set()
        for raw in raw_values:
            if not isinstance(raw, str):
                raise NotificationValidationError(
                    "INVALID_NOTIFICATION_TAG", "Every notification tag must be a string"
                )
            tag = normalize_tag(raw)
            if not tag or len(tag) > self._max_tag_length:
                raise NotificationValidationError(
                    "INVALID_NOTIFICATION_TAG",
                    f"Tags must contain 1–{self._max_tag_length} normalized characters",
                )
            normalized.add(tag)
        return tuple(sorted(normalized))
