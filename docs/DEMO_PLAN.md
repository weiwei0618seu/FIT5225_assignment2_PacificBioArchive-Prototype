# Demo Plan

## Before the session

- all four members join Zoom and can explain their assigned code;
- verify AWS Free Plan/billing, stack `CREATE_COMPLETE` or `UPDATE_COMPLETE`, CloudFront HTTPS, ECR
  digest and CloudWatch alarms/log retention;
- prepare one verified Cognito demo account and one confirmed SNS subscription;
- keep a second unregistered email only if live registration will be shown;
- pre-open the architecture slide, application login and CloudWatch logs;
- use fixture copies, not the only source files, and avoid long videos;
- record sanitized screenshots and a short backup screen capture.

Recommended real fixtures and expected model results:

| Fixture | Expected result |
|---|---|
| `Alectura_lathami_1.JPG` | `australian brushturkey ×1` |
| `Casuarius_casuarius_1.JPG` | `southern cassowary ×1` |
| `Felis_catus_3.JPG` | `domestic cat ×1` |

## Architecture presentation (maximum 3 minutes)

1. **30 s — purpose/security:** authenticated wildlife archive; Cognito JWT;
   private S3; separate least-privilege Lambda roles.
2. **60 s — ingest:** browser SHA-256 → presigned S3 upload → EventBridge → ML
   container → thumbnail/one-frame-per-second video → DynamoDB → filtered SNS.
3. **45 s — query/manage:** HTTP API; four queries; stable IDs plus expiring
   URLs; bulk tag/delete; temporary query cleanup.
4. **30 s — delivery/cost:** CloudFront private origin, SAM/CloudFormation,
   immutable ECR digest, on-demand/expiry/throttling controls, AWS-only written
   teaching-team clarification.
5. **15 s — evidence:** real supplied-model Linux/AWS proof, automated tests and
   measured coverage.

The Team Report diagram must use official AWS architecture icons. Do not call a
Mermaid engineering sketch the final report diagram.

## Application demonstration (target 12–14 minutes)

1. Show protected-route redirect while signed out.
2. Register, receive Cognito code, verify, sign in; or show this quickly with a
   prepared verified account if email latency threatens the demo.
3. Start/confirm a watched tag subscription.
4. Upload `Alectura_lathami_1.JPG`; narrate hashing, duplicate check, private S3,
   automatic processing, thumbnail and expected real tag.
5. Rename a copy without changing bytes and show checksum duplicate rejection.
6. Show a short prepared video and the recorded one-frame-per-second evidence.
7. Run species search and click the thumbnail to the original.
8. Add manual tag `demo-reviewed`; query strict AND with
   `australian brushturkey >=1` and `demo-reviewed >=1`.
9. Paste the thumbnail URL and recover the original.
10. Use `Alectura_lathami_2.JPG` as a temporary image query; show detected tags,
    matches and the absence of a persistent query/media record.
11. Bulk-add then bulk-remove a tag; remove it again to demonstrate safe ignore.
12. Show confirmed SNS watched-tag delivery (use the prepared confirmation if
    live mail is delayed).
13. Permanently delete the demo record; show all outcomes and an idempotent retry.
14. Sign out and show protected access is blocked again.

## Member speaking ownership

- Member 1: supplied ML, thumbnail/video processing and real-model proof.
- Member 2: data model, four query paths, bulk tag/delete and API contracts.
- Member 3: S3/DynamoDB/SNS/EventBridge/IAM, CloudFormation and cost controls.
- Member 4: Cognito security, React UI, deployment UX and final integration.

## Backup plan

- Email delayed: use already verified/confirmed accounts, then show Cognito/SNS
  status and sanitized evidence.
- Cold ML start: begin one warm-up upload before the marked flow and disclose it.
- CloudFront cache: hard refresh after the recorded invalidation.
- AWS transient error: show the last successful screen capture plus live stack,
  logs and immutable commit/digest; never claim a currently failing action works.
- Model surprise: use the three hash-bound fixtures above and keep their local,
  Linux container and live-AWS evidence clearly separated.

## Q&A prompts

- Why is checksum calculated both in the browser and processor?
- Why do multi-tag queries use AND, and how is a manual tag counted?
- How is temporary-query cleanup guaranteed on exceptions?
- Why are URLs signed rather than durable public links?
- How are duplicate S3 events/notifications suppressed?
- How can the model be updated without changing business code?
- Which IAM role can access each bucket/table/topic?
- Why is reserved concurrency omitted in this Academy account?
- Which statements are proven locally, in Linux CI, and live in AWS?
