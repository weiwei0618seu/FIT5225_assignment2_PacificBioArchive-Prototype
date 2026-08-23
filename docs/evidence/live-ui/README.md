# Live browser evidence

Observed on 2026-08-23 against the Sydney CloudFront deployment.

- `00-registration.png` shows the required Cognito registration fields before
  any user data was entered.
- `01-login-protected.png` shows the native sign-in page after disabled Google
  federation was hidden.
- `02-upload-ml-thumbnail.png` shows the supplied-model `READY` result for the
  real fixture, including the generated thumbnail, species count and model
  version. The signed URL itself is not displayed.
- `03-strict-and-manual-tag.png` shows the live two-row minimum-count query for
  the supplied-model species plus the manually added `reviewed` tag. Both the
  image and the three-frame video satisfy the strict AND query.
- `04-temporary-query-async.png` shows the deployed asynchronous temporary
  image query after `PROCESSING` reached `READY`: the supplied model detected
  one Australian brushturkey and matched the existing image and video.
- `05-duplicate-checksum-rejected.png` shows the deployed upload UI rejecting
  the exact bytes of the existing fixture before a second object is stored.
  This uses checksum identity rather than the filename.
- `06-thumbnail-to-original.png` shows the live reverse lookup accepting an
  existing thumbnail reference and returning an **Open original** action. The
  signed input and private file identifier are visibly marked as redacted.
- `07-temporary-query-failure-cleanup.png` shows a deliberately undecodable
  temporary image reaching the honest failure state. A separate sanitized,
  read-only AWS check observed zero `query-temp/` objects and the latest job in
  `FAILED` with a one-hour TTL.
- `08-manage-cleanup-and-sns.png` shows the owner-management cleanup controls,
  the watched `australian brushturkey` tag and the live SNS subscription in
  `CONFIRMED`. Separate sanitized observations recorded the two-record
  remove/delete idempotency checks, zero related S3/media/dedup residue, one
  confirmed email subscriber and the notification-event claim for the new
  watched-tag test upload. The recipient separately observed the delivered
  watched-tag message.
- `09-logout-protected.png` shows the blank native sign-in screen reached after
  logout and a direct protected Manage-route revisit. The remembered email and
  password fields are covered with opaque labelled redactions.

The screenshots contain no credentials, email addresses, tokens, codes,
pre-signed URLs or private media identifiers. Authenticated screenshots are
cropped to the application main region so the Cognito subject is not visible;
where a successful reverse lookup inherently displayed a signed URL/private
identifier, both fields were covered and explicitly labelled as redacted.
