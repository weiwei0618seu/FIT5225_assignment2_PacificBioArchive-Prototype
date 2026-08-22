# Stage 3.3 Report — Tag Email Notifications

## Goal and boundary

Add verified-user email subscriptions and filtered, replay-safe SNS publishing
for automatic and newly added manual wildlife tags. REST route serialization,
Cognito infrastructure and live email confirmation remain later stages.

## Completed behavior

- Accepts subscription email only from a verified Cognito identity input;
  unverified/invalid email and missing subject fail before SNS is called.
- Normalizes and bounds watched tags, creates an SNS email subscription, and
  stores the real `PENDING`, `CONFIRMED` or `ERROR` state.
- Updates SNS `FilterPolicy` when watched tags change and synchronizes status
  through `GetSubscriptionAttributes` rather than assuming confirmation.
- Supports idempotent local deletion plus SNS unsubscribe; the future UI must
  display a user confirmation before calling the destructive route.
- Publishes one message with a `String.Array` tag attribute so any matching
  watched tag can select the email subscription without duplicate per-tag mail.
- Uses deterministic `file_id#version#tag-digest` event claims. Replays are
  suppressed; a failed SNS publish releases the claim for retry.
- Hooks automatic READY processing and manual tag additions into the same
  notification service.
- A post-READY SNS failure leaves the media and checksum committed and uses the
  S3 replay path to retry notification without rerunning ML or thumbnails.
- Added in-memory and conditional DynamoDB subscription/event repositories plus
  an injected boto3 SNS adapter.

## Created files

- `backend/src/pacific_bioarchive/domain/notifications.py`
- `backend/src/pacific_bioarchive/domain/notification_topic.py`
- `backend/src/pacific_bioarchive/application/notifications.py`
- `backend/src/pacific_bioarchive/persistence/notifications.py`
- `backend/src/pacific_bioarchive/persistence/sns.py`
- `backend/tests/unit/test_notifications.py`
- `docs/stages/STAGE_3.3_REPORT.md`
- `docs/stages/STAGE_3.3_HANDOFF.md`

## Modified files

- `backend/src/pacific_bioarchive/application/management.py`
- `backend/src/pacific_bioarchive/application/processing.py`
- `backend/src/pacific_bioarchive/handlers/media_processor.py`
- `backend/tests/unit/test_async_processing.py`
- `backend/tests/unit/test_management.py`
- `docs/ARCHITECTURE.md`
- `docs/DATA_MODEL.md`
- `docs/GENAI_USAGE.md`

## Verification

Command from `backend`:

```powershell
uv run --project . --extra dev pytest -q
```

Observed result: `75 passed` (62 prior tests plus 13 notification and integration
tests). Focused Ruff checks pass for all new Stage 3.3 files and the Stage 3.2
files modified by this stage.

Coverage includes verified/unverified identity, normalization, pending status,
confirmation synchronization, filter update, verified-email replacement,
failed-filter rollback, deletion, watched-tag
intersection, replay suppression, publish failure/retry, non-READY suppression,
SNS request shapes, DynamoDB conditions, manual-tag triggering, and post-READY
notification retry without repeated ML.

## Run/configuration notes

The processor now additionally requires `PBA_SUBSCRIPTIONS_TABLE`,
`PBA_NOTIFICATION_EVENTS_TABLE`, and `PBA_NOTIFICATION_TOPIC_ARN`. The REST API
stage will compose the same service for subscription endpoints.

## AWS operations

None. Tests use injected fake SNS/DynamoDB clients. No subscription email has
been claimed sent or confirmed. Live confirmation requires a real recipient to
click the SNS link after deployment.

## Known risks

- SNS is at-least-once; the durable event claim removes ordinary Lambda replay
  duplicates, while a crash after SNS accepts publish but before the client
  returns can still produce a rare duplicate on retry.
- A pending email subscription must be confirmed by the recipient before SNS
  sends tag alerts.
- The deployment role still needs least-privilege topic/subscription/table
  actions, added in Stage 4.2/6.1.
