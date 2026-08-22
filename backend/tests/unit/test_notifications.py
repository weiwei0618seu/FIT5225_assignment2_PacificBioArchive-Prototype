from __future__ import annotations

import json
import unittest
from typing import ClassVar

from pacific_bioarchive.application.notifications import (
    NotificationService,
    NotificationValidationError,
)
from pacific_bioarchive.domain.media import MediaRecord, ProcessingStatus
from pacific_bioarchive.domain.notifications import (
    NotificationSubscription,
    SubscriptionStatus,
)
from pacific_bioarchive.media.validation import MediaType
from pacific_bioarchive.persistence.notifications import (
    DynamoNotificationEventRepository,
    DynamoSubscriptionRepository,
    InMemoryNotificationEventRepository,
    InMemorySubscriptionRepository,
    subscription_from_item,
    subscription_to_item,
)
from pacific_bioarchive.persistence.sns import SnsNotificationTopic


def ready_record(*, version: int = 3) -> MediaRecord:
    return MediaRecord(
        file_id="file-1",
        owner_sub="owner-1",
        filename="camera.jpg",
        checksum="a" * 64,
        file_type=MediaType.IMAGE,
        content_type="image/jpeg",
        size_bytes=100,
        original_key="originals/file-1/camera.jpg",
        thumbnail_key="thumbnails/file-1.jpg",
        species_counts={"dingo": 2, "wombat": 1},
        manual_tags=("night",),
        processing_status=ProcessingStatus.READY,
        created_at="2026-08-23T00:00:00Z",
        updated_at="2026-08-23T00:02:00Z",
        version=version,
    )


class FakeTopic:
    def __init__(self) -> None:
        self.status = SubscriptionStatus.PENDING
        self.subscribed: list[tuple[str, tuple[str, ...]]] = []
        self.filters: list[tuple[str, tuple[str, ...]]] = []
        self.unsubscribed: list[str] = []
        self.published: list[dict[str, object]] = []
        self.fail_publish = False

    def subscribe_email(self, email: str, *, tags: tuple[str, ...]) -> str:
        self.subscribed.append((email, tags))
        return f"arn:aws:sns:ap-southeast-2:123:topic:subscription-{len(self.subscribed)}"

    def set_filter(self, subscription_arn: str, *, tags: tuple[str, ...]) -> None:
        self.filters.append((subscription_arn, tags))

    def get_status(self, subscription_arn: str) -> SubscriptionStatus:
        return self.status

    def unsubscribe(self, subscription_arn: str) -> None:
        self.unsubscribed.append(subscription_arn)

    def publish(self, **kwargs: object) -> None:
        if self.fail_publish:
            raise RuntimeError("SNS unavailable")
        self.published.append(kwargs)


class NotificationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.subscriptions = InMemorySubscriptionRepository()
        self.events = InMemoryNotificationEventRepository()
        self.topic = FakeTopic()
        self.service = NotificationService(
            subscription_repository=self.subscriptions,
            event_repository=self.events,
            topic=self.topic,
        )

    def test_verified_email_subscription_normalizes_tags_and_reports_pending(self) -> None:
        subscription = self.service.set_subscription(
            actor_sub="user-1",
            verified_email="Student@Example.edu",
            email_verified=True,
            tags=[" DINGO ", "wombat", "dingo"],
        )
        self.assertEqual(subscription.email, "student@example.edu")
        self.assertEqual(subscription.tags, ("dingo", "wombat"))
        self.assertEqual(subscription.status, SubscriptionStatus.PENDING)
        self.assertEqual(self.topic.subscribed[0], (subscription.email, subscription.tags))

    def test_unverified_or_invalid_identity_is_rejected_before_sns(self) -> None:
        for actor, email, verified in [
            ("user-1", "student@example.edu", False),
            ("user-1", "not-an-email", True),
            ("", "student@example.edu", True),
        ]:
            with self.subTest(actor=actor, email=email), self.assertRaises(
                NotificationValidationError
            ):
                self.service.set_subscription(
                    actor_sub=actor,
                    verified_email=email,
                    email_verified=verified,
                    tags=["dingo"],
                )
        self.assertEqual(self.topic.subscribed, [])

    def test_update_filter_sync_confirmation_and_delete(self) -> None:
        first = self.service.set_subscription(
            actor_sub="user-1",
            verified_email="student@example.edu",
            email_verified=True,
            tags=["dingo"],
        )
        self.topic.status = SubscriptionStatus.CONFIRMED
        updated = self.service.set_subscription(
            actor_sub="user-1",
            verified_email="student@example.edu",
            email_verified=True,
            tags=["wombat"],
        )
        self.assertEqual(updated.status, SubscriptionStatus.CONFIRMED)
        self.assertEqual(updated.tags, ("wombat",))
        self.assertEqual(updated.version, first.version + 1)
        self.assertEqual(self.topic.filters[-1][1], ("wombat",))
        self.assertTrue(self.service.delete_subscription(actor_sub="user-1"))
        self.assertFalse(self.service.delete_subscription(actor_sub="user-1"))
        self.assertEqual(self.topic.unsubscribed, [first.sns_subscription_arn])

    def test_verified_email_change_replaces_subscription_then_removes_old(self) -> None:
        first = self.service.set_subscription(
            actor_sub="user-1",
            verified_email="old@example.edu",
            email_verified=True,
            tags=["dingo"],
        )
        replacement = self.service.set_subscription(
            actor_sub="user-1",
            verified_email="new@example.edu",
            email_verified=True,
            tags=["wombat"],
        )
        self.assertEqual(replacement.email, "new@example.edu")
        self.assertNotEqual(replacement.sns_subscription_arn, first.sns_subscription_arn)
        self.assertEqual(replacement.version, first.version + 1)
        self.assertEqual(self.topic.unsubscribed, [first.sns_subscription_arn])

    def test_publish_uses_intersection_and_suppresses_same_record_replay(self) -> None:
        record = ready_record()
        self.assertTrue(self.service.publish_for_record(record, tags=["DINGO", "absent"]))
        self.assertFalse(self.service.publish_for_record(record, tags=["dingo", "absent"]))
        self.assertEqual(len(self.topic.published), 1)
        self.assertEqual(self.topic.published[0]["tags"], ("dingo",))
        self.assertIn("file-1#3#", self.topic.published[0]["event_id"])

    def test_publish_failure_releases_claim_for_retry(self) -> None:
        record = ready_record()
        self.topic.fail_publish = True
        with self.assertRaisesRegex(RuntimeError, "SNS unavailable"):
            self.service.publish_for_record(record)
        self.topic.fail_publish = False
        self.assertTrue(self.service.publish_for_record(record))
        self.assertEqual(len(self.topic.published), 1)

    def test_non_ready_or_no_matching_tags_do_not_publish(self) -> None:
        failed = ready_record().mark_failed("MODEL_ERROR")
        self.assertFalse(self.service.publish_for_record(failed))
        self.assertFalse(self.service.publish_for_record(ready_record(), tags=["koala"]))
        self.assertEqual(self.topic.published, [])


class FakeSnsClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.pending = True
        self.fail_filter = False

    def subscribe(self, **kwargs: object) -> dict[str, str]:
        self.calls.append(("subscribe", kwargs))
        return {"SubscriptionArn": "arn:subscription"}

    def set_subscription_attributes(self, **kwargs: object) -> None:
        self.calls.append(("set_subscription_attributes", kwargs))
        if self.fail_filter:
            raise RuntimeError("filter failed")

    def get_subscription_attributes(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("get_subscription_attributes", kwargs))
        return {"Attributes": {"PendingConfirmation": str(self.pending).lower()}}

    def unsubscribe(self, **kwargs: object) -> None:
        self.calls.append(("unsubscribe", kwargs))

    def publish(self, **kwargs: object) -> None:
        self.calls.append(("publish", kwargs))


class SnsAdapterTests(unittest.TestCase):
    def test_subscribe_sets_filter_and_exposes_real_pending_status(self) -> None:
        client = FakeSnsClient()
        topic = SnsNotificationTopic(client, topic_arn="arn:topic")
        arn = topic.subscribe_email("student@example.edu", tags=("dingo", "wombat"))
        self.assertEqual(arn, "arn:subscription")
        subscribe = client.calls[0][1]
        self.assertEqual(subscribe["Protocol"], "email")
        self.assertTrue(subscribe["ReturnSubscriptionArn"])
        filter_call = client.calls[1][1]
        self.assertEqual(
            json.loads(filter_call["AttributeValue"]), {"tags": ["dingo", "wombat"]}
        )
        self.assertEqual(topic.get_status(arn), SubscriptionStatus.PENDING)
        client.pending = False
        self.assertEqual(topic.get_status(arn), SubscriptionStatus.CONFIRMED)

    def test_publish_uses_string_array_for_filter_matching(self) -> None:
        client = FakeSnsClient()
        topic = SnsNotificationTopic(client, topic_arn="arn:topic")
        topic.publish(
            event_id="file-1#3#digest",
            file_id="file-1",
            filename="camera.jpg",
            tags=("dingo", "wombat"),
        )
        call = client.calls[-1][1]
        self.assertEqual(call["TopicArn"], "arn:topic")
        self.assertEqual(call["MessageAttributes"]["tags"]["DataType"], "String.Array")
        self.assertEqual(
            json.loads(call["MessageAttributes"]["tags"]["StringValue"]),
            ["dingo", "wombat"],
        )

    def test_filter_failure_rolls_back_new_sns_subscription(self) -> None:
        client = FakeSnsClient()
        client.fail_filter = True
        topic = SnsNotificationTopic(client, topic_arn="arn:topic")
        with self.assertRaisesRegex(RuntimeError, "filter failed"):
            topic.subscribe_email("student@example.edu", tags=("dingo",))
        self.assertEqual(client.calls[-1][0], "unsubscribe")


class ConditionalFailure(Exception):
    response: ClassVar[dict[str, object]] = {
        "Error": {"Code": "ConditionalCheckFailedException"}
    }


class FakeDynamoTable:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, object]] = {}
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.fail_condition = False

    def put_item(self, **kwargs: object) -> None:
        self.calls.append(("put_item", kwargs))
        if self.fail_condition:
            raise ConditionalFailure()
        item = dict(kwargs["Item"])
        key_name = "user_sub" if "user_sub" in item else "event_id"
        self.items[str(item[key_name])] = item

    def get_item(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("get_item", kwargs))
        key = str(next(iter(kwargs["Key"].values())))
        return {"Item": self.items[key]} if key in self.items else {}

    def delete_item(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("delete_item", kwargs))
        key = str(next(iter(kwargs["Key"].values())))
        old = self.items.pop(key, None)
        return {"Attributes": old} if old else {}


class NotificationDynamoTests(unittest.TestCase):
    def test_subscription_round_trip_and_conditional_versions(self) -> None:
        table = FakeDynamoTable()
        repository = DynamoSubscriptionRepository(table)
        created = self._subscription()
        repository.save(created, expected_version=None)
        self.assertIn("attribute_not_exists", table.calls[-1][1]["ConditionExpression"])
        self.assertEqual(repository.get(created.user_sub), created)
        updated = created.with_state(
            tags=("wombat",), status=SubscriptionStatus.CONFIRMED, now="later"
        )
        repository.save(updated, expected_version=created.version)
        self.assertEqual(table.calls[-1][1]["ExpressionAttributeValues"], {":expected": 1})
        self.assertEqual(subscription_from_item(subscription_to_item(updated)), updated)
        self.assertEqual(repository.delete(created.user_sub), updated)

    def test_event_claim_returns_false_on_conditional_duplicate_and_releases(self) -> None:
        table = FakeDynamoTable()
        repository = DynamoNotificationEventRepository(table)
        self.assertTrue(repository.claim("event-1"))
        table.fail_condition = True
        self.assertFalse(repository.claim("event-1"))
        table.fail_condition = False
        repository.release("event-1")
        self.assertNotIn("event-1", table.items)

    @staticmethod
    def _subscription() -> NotificationSubscription:
        return NotificationSubscription(
            user_sub="user-1",
            email="student@example.edu",
            tags=("dingo",),
            sns_subscription_arn="arn:subscription",
            status=SubscriptionStatus.PENDING,
            updated_at="now",
        )


if __name__ == "__main__":
    unittest.main()
