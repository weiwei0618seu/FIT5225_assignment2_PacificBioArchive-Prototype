"""Amazon SNS email subscription, filtering, status and publish adapter."""

from __future__ import annotations

import json
from typing import Any

from pacific_bioarchive.domain.notifications import SubscriptionStatus


class SnsNotificationTopic:
    def __init__(self, client: Any, *, topic_arn: str) -> None:
        if not topic_arn.strip():
            raise ValueError("topic_arn is required")
        self._client = client
        self.topic_arn = topic_arn

    def subscribe_email(self, email: str, *, tags: tuple[str, ...]) -> str:
        response = self._client.subscribe(
            TopicArn=self.topic_arn,
            Protocol="email",
            Endpoint=email,
            ReturnSubscriptionArn=True,
        )
        arn = str(response["SubscriptionArn"])
        try:
            self.set_filter(arn, tags=tags)
        except Exception:
            self.unsubscribe(arn)
            raise
        return arn

    def set_filter(self, subscription_arn: str, *, tags: tuple[str, ...]) -> None:
        self._client.set_subscription_attributes(
            SubscriptionArn=subscription_arn,
            AttributeName="FilterPolicy",
            AttributeValue=json.dumps({"tags": list(tags)}, separators=(",", ":")),
        )

    def get_status(self, subscription_arn: str) -> SubscriptionStatus:
        try:
            response = self._client.get_subscription_attributes(
                SubscriptionArn=subscription_arn
            )
        except Exception as exc:
            code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if code in {"NotFound", "NotFoundException"}:
                return SubscriptionStatus.PENDING
            raise
        pending = str(response.get("Attributes", {}).get("PendingConfirmation", "false"))
        return (
            SubscriptionStatus.PENDING
            if pending.lower() == "true"
            else SubscriptionStatus.CONFIRMED
        )

    def unsubscribe(self, subscription_arn: str) -> None:
        self._client.unsubscribe(SubscriptionArn=subscription_arn)

    def publish(
        self,
        *,
        event_id: str,
        file_id: str,
        filename: str,
        tags: tuple[str, ...],
    ) -> None:
        self._client.publish(
            TopicArn=self.topic_arn,
            Subject="Pacific BioArchive wildlife tag alert",
            Message=json.dumps(
                {
                    "event_id": event_id,
                    "file_id": file_id,
                    "filename": filename,
                    "tags": list(tags),
                },
                separators=(",", ":"),
            ),
            MessageAttributes={
                "tags": {
                    "DataType": "String.Array",
                    "StringValue": json.dumps(list(tags), separators=(",", ":")),
                },
                "event_id": {"DataType": "String", "StringValue": event_id},
            },
        )
