# Stage 3.3 Handoff — Tag Email Notifications

## What this stage owns

This stage owns watched-tag subscription state and the transition from a READY
or manually retagged media record to a filtered SNS email event. It deliberately
does not treat subscription creation as confirmation.

## Main files

- `application/notifications.py` — validation, status sync and event claims.
- `domain/notifications.py` — subscription entity and repository ports.
- `persistence/sns.py` — SNS protocol, filter, status and publish calls.
- `persistence/notifications.py` — in-memory/DynamoDB state.
- `tests/unit/test_notifications.py` — notification evidence.
- `application/processing.py` and `application/management.py` — trigger points.

## Verification

Run `uv run --project . --extra dev pytest -q` from `backend` and confirm all 75
tests pass. In the SNS adapter tests, verify that filter tags and published tags
use the same normalized values and `String.Array` message type.

## Demo questions

- Why is email read from Cognito claims instead of request JSON?
- What is the difference between SNS `PENDING` and `CONFIRMED`?
- How does one publish match users watching different tags?
- How are duplicate S3 events prevented from sending obvious duplicate email?
- Why does notification failure not turn valid processed media into `FAILED`?
- What rare duplicate window remains with an external at-least-once service?

## Live verification still required

After SAM deployment, a student must use an email account they control, click
the actual SNS confirmation link, refresh status until `CONFIRMED`, upload a
matching test image, and retain non-sensitive evidence of one received alert.
Do not commit the email address, confirmation URL, tokens or message headers.
