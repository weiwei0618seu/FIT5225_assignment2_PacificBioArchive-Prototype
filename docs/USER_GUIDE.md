# User Guide

## Create and verify an account

1. Open the CloudFront application URL and select **Create an account**.
2. Enter first name, last name, email and a password of at least 12 characters
   containing upper/lowercase letters, a number and a symbol.
3. Enter the six-digit code sent by Amazon Cognito.
4. Sign in. Every Overview, Upload, Search and Manage route is protected.

Never share a password, verification code or token. Signing out clears the
browser session and returns to the login page.

## Upload wildlife media

Open **Upload**, choose JPG/PNG/WebP or MP4/MOV/AVI, then select **Upload and
analyse**. Images are limited to 10 MiB; demo videos are limited to 50 MiB and
30 seconds. The browser shows hashing, duplicate check, private upload and ML
processing states.

The browser calculates SHA-256 before upload. Uploading the exact same bytes
again is rejected even if the filename changes. A successful image shows its
thumbnail, detected species/counts and a link to the expiring original URL.
Videos are sampled at exactly one frame per second.

## Search

Open **Search** and choose one of four modes:

- **Counts** — add one or more species/tag rows and minimum counts. Every row is
  required (logical AND).
- **Species** — find ready files with at least one automatic or manual tag.
- **Thumbnail** — paste a returned thumbnail URL/key to recover the original.
- **Image** — temporarily upload JPG/PNG/WebP. The model detects its tags and
  finds existing matches; the query object is deleted on success or failure and
  is never added to the archive.

Search results use thumbnails to save bandwidth. Select **Open original** only
when the full-size file is needed. Empty results and invalid input are shown as
explicit messages.

## Bulk tags and deletion

Open **Manage**:

1. Search by species/tag and select one or more cards, or paste file IDs/URLs.
2. Enter comma-separated manual tags.
3. Choose **Add tags** or **Remove tags**, then apply. Removing a tag that is not
   present is safely ignored.
4. To delete, select **Delete media…**, read the confirmation and explicitly
   approve it. Deletion removes the original/video, thumbnail, metadata and
   duplicate reservation. The outcome list reports deleted/already-absent/error
   per item and a retry is safe.

Only the uploader may change or delete their media. Bulk requests accept at
most 25 items.

## Email notifications

In **Manage → Email watch**, enter watched tags and select **Start watching**.
AWS SNS sends a confirmation to the verified Cognito email. Open that message
and confirm before notifications become active. New or manually updated media
with a watched tag triggers the filtered email flow; replay protection avoids
obvious duplicate events.

Use **Remove email subscription…** only when notifications should stop for all
watched tags.

## Common messages

| Message/state | Meaning/action |
|---|---|
| Duplicate file | Exact bytes already exist; use the existing record or another file. |
| Processing | Wait; the upload page polls until READY/FAILED. Short demo files are recommended. |
| Unauthorized/session expired | Sign in again; no request is sent with an expired local session. |
| No ready media matched | Query is valid but no record meets every condition. |
| Subscription pending | Confirm the AWS SNS email, then reload Manage. |
| Deletion incomplete | Keep the outcome list/request ID and retry; check CloudWatch if it repeats. |

