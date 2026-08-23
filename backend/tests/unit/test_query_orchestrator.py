from __future__ import annotations

import json
import unittest
from io import BytesIO

from pacific_bioarchive.domain.query_jobs import TemporaryQueryJob, TemporaryQueryStatus
from pacific_bioarchive.handlers.query_orchestrator import (
    TemporaryQueryOrchestrationError,
    handle_s3_event,
)
from pacific_bioarchive.persistence.query_jobs import (
    InMemoryTemporaryQueryRepository,
    temporary_query_job_from_item,
    temporary_query_job_to_item,
)

BUCKET = "private-media"
QUERY_ID = "query-1"
KEY = f"query-temp/{'a' * 32}/{QUERY_ID}/query.jpg"


def s3_event(key: str = KEY) -> dict[str, object]:
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {"bucket": {"name": BUCKET}, "object": {"key": key}},
            }
        ]
    }


class FakeLambdaClient:
    def __init__(self, *, status: int = 200, body: dict[str, object] | None = None) -> None:
        self.status = status
        self.body = body or {
            "detected_species_counts": {"dingo": 1},
            "model_version": "supplied-v1",
            "media": [
                {
                    "file_id": "file-1",
                    "original_url": "https://signed.example/private",
                    "thumbnail_url": "https://signed.example/private-thumb",
                }
            ],
            "total": 1,
            "truncated": False,
        }
        self.calls: list[dict[str, object]] = []

    def invoke(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        request = json.loads(bytes(kwargs["Payload"]).decode("utf-8"))
        self.assert_private_event(request)
        response = {
            "statusCode": self.status,
            "body": json.dumps(self.body),
        }
        return {"Payload": BytesIO(json.dumps(response).encode("utf-8"))}

    @staticmethod
    def assert_private_event(request: dict[str, object]) -> None:
        claims = request["requestContext"]["authorizer"]["jwt"]["claims"]
        assert claims == {"sub": "user-1"}
        assert "email" not in json.dumps(request)


class TemporaryQueryOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jobs = InMemoryTemporaryQueryRepository()
        self.jobs.create(
            TemporaryQueryJob(
                query_id=QUERY_ID,
                owner_sub="user-1",
                temp_key=KEY,
                expires_at=200,
                created_at="now",
                updated_at="now",
            )
        )

    def test_success_persists_only_stable_result_fields(self) -> None:
        client = FakeLambdaClient()
        result = handle_s3_event(
            s3_event(),
            jobs=self.jobs,
            lambda_client=client,
            function_name="temporary-query-function",
            expected_bucket=BUCKET,
        )
        self.assertEqual(result["processed"], 1)
        job = self.jobs.get(QUERY_ID)
        assert job is not None
        self.assertEqual(job.status, TemporaryQueryStatus.READY)
        self.assertEqual(job.species_counts, {"dingo": 1})
        self.assertEqual(job.matched_file_ids, ("file-1",))
        stored = json.dumps(temporary_query_job_to_item(job))
        self.assertNotIn("signed.example", stored)
        self.assertNotIn("original_url", stored)

    def test_safe_ml_error_becomes_terminal_job_without_secret_body(self) -> None:
        client = FakeLambdaClient(
            status=400,
            body={
                "error": {
                    "code": "NO_SPECIES_DETECTED",
                    "message": "No species were detected",
                    "details": {"implementation": "must-not-persist"},
                }
            },
        )
        handle_s3_event(
            s3_event(),
            jobs=self.jobs,
            lambda_client=client,
            function_name="temporary-query-function",
            expected_bucket=BUCKET,
        )
        job = self.jobs.get(QUERY_ID)
        assert job is not None
        self.assertEqual(job.status, TemporaryQueryStatus.FAILED)
        self.assertEqual(job.error_code, "NO_SPECIES_DETECTED")
        self.assertNotIn("must-not-persist", json.dumps(temporary_query_job_to_item(job)))

    def test_replay_does_not_invoke_ml_again(self) -> None:
        client = FakeLambdaClient()
        handle_s3_event(
            s3_event(),
            jobs=self.jobs,
            lambda_client=client,
            function_name="temporary-query-function",
            expected_bucket=BUCKET,
        )
        handle_s3_event(
            s3_event(),
            jobs=self.jobs,
            lambda_client=client,
            function_name="temporary-query-function",
            expected_bucket=BUCKET,
        )
        self.assertEqual(len(client.calls), 1)

    def test_unbound_or_malformed_key_is_rejected_before_ml(self) -> None:
        client = FakeLambdaClient()
        with self.assertRaises(TemporaryQueryOrchestrationError):
            handle_s3_event(
                s3_event(f"query-temp/{'b' * 32}/{QUERY_ID}/query.jpg"),
                jobs=self.jobs,
                lambda_client=client,
                function_name="temporary-query-function",
                expected_bucket=BUCKET,
            )
        self.assertEqual(client.calls, [])

    def test_serialization_round_trip_preserves_ttl_and_status(self) -> None:
        job = self.jobs.get(QUERY_ID)
        assert job is not None
        self.assertEqual(temporary_query_job_from_item(temporary_query_job_to_item(job)), job)


if __name__ == "__main__":
    unittest.main()
