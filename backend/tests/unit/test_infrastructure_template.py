from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Any

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = REPOSITORY_ROOT / "infrastructure" / "template.yaml"


class CloudFormationLoader(yaml.SafeLoader):
    pass


def construct_intrinsic(loader: CloudFormationLoader, suffix: str, node: yaml.Node) -> Any:
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node)
    else:
        value = loader.construct_mapping(node)
    return {suffix: value}


CloudFormationLoader.add_multi_constructor("!", construct_intrinsic)


class RootInfrastructureTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = yaml.load(
            TEMPLATE_PATH.read_text(encoding="utf-8"), Loader=CloudFormationLoader
        )
        cls.resources = cls.template["Resources"]

    def test_region_rule_and_free_plan_cost_guardrails_exist(self) -> None:
        self.assertIn("DeployOnlyInSydney", self.template["Rules"])
        self.assertIn("CostBudget", self.resources)
        self.assertEqual(self.resources["CostBudget"]["Condition"], "CostBudgetEnabled")
        forbidden = {
            "AWS::EC2::Instance",
            "AWS::EC2::NatGateway",
            "AWS::RDS::DBInstance",
            "AWS::OpenSearchService::Domain",
            "AWS::SageMaker::NotebookInstance",
            "AWS::EFS::FileSystem",
            "AWS::WAFv2::WebACL",
        }
        self.assertFalse(
            forbidden.intersection(resource["Type"] for resource in self.resources.values())
        )

    def test_private_buckets_encryption_and_temp_lifecycle(self) -> None:
        for name in ("MediaBucket", "ModelBucket", "FrontendBucket"):
            with self.subTest(bucket=name):
                properties = self.resources[name]["Properties"]
                public = properties["PublicAccessBlockConfiguration"]
                self.assertTrue(all(public.values()))
                self.assertIn("BucketEncryption", properties)
                ownership = properties["OwnershipControls"]["Rules"][0]
                self.assertEqual(ownership["ObjectOwnership"], "BucketOwnerEnforced")
        rules = self.resources["MediaBucket"]["Properties"]["LifecycleConfiguration"][
            "Rules"
        ]
        query_rule = next(rule for rule in rules if rule["Id"] == "ExpireTemporaryQueries")
        self.assertEqual(query_rule["Prefix"], "query-temp/")
        self.assertEqual(query_rule["ExpirationInDays"], 1)

    def test_on_demand_encrypted_tables_and_dedup_ttl(self) -> None:
        for name in ("MediaTable", "DedupTable", "SubscriptionsTable", "NotificationEventsTable"):
            with self.subTest(table=name):
                properties = self.resources[name]["Properties"]
                self.assertEqual(properties["BillingMode"], "PAY_PER_REQUEST")
                self.assertTrue(properties["SSESpecification"]["SSEEnabled"])
        ttl = self.resources["DedupTable"]["Properties"]["TimeToLiveSpecification"]
        self.assertEqual(ttl, {"AttributeName": "expires_at", "Enabled": True})

    def test_all_business_routes_use_one_jwt_authorized_http_api(self) -> None:
        api = self.resources["HttpApi"]["Properties"]
        self.assertEqual(api["Auth"]["DefaultAuthorizer"], "CognitoJwtAuthorizer")
        self.assertEqual(api["DefaultRouteSettings"]["ThrottlingRateLimit"], 5)
        routes: set[tuple[str, str]] = set()
        for function_name in ("CoreApiFunction", "TemporaryQueryFunction"):
            events = self.resources[function_name]["Properties"].get("Events", {})
            for event in events.values():
                if event["Type"] == "HttpApi":
                    properties = event["Properties"]
                    routes.add((properties["Method"], properties["Path"]))
        expected = {
            ("GET", "/health"),
            ("POST", "/uploads/init"),
            ("GET", "/media/{file_id}"),
            ("POST", "/queries/tags"),
            ("GET", "/queries/species"),
            ("POST", "/queries/thumbnail"),
            ("POST", "/queries/file/init"),
            ("POST", "/queries/file/{query_id}"),
            ("POST", "/media/tags"),
            ("POST", "/media/delete"),
            ("POST", "/notifications/subscription"),
            ("GET", "/notifications/subscription"),
            ("DELETE", "/notifications/subscription"),
        }
        self.assertEqual(routes, expected)

    def test_ml_compute_and_logs_are_bounded(self) -> None:
        for name in ("MediaProcessorFunction", "TemporaryQueryFunction"):
            properties = self.resources[name]["Properties"]
            self.assertEqual(properties["PackageType"], "Image")
            self.assertEqual(properties["ReservedConcurrentExecutions"], 1)
            self.assertLessEqual(properties["MemorySize"], 4096)
            self.assertLessEqual(properties["Timeout"], 900)
        self.assertEqual(
            self.resources["CoreApiFunction"]["Properties"]["ReservedConcurrentExecutions"],
            2,
        )
        for name in ("CoreApiLogGroup", "MediaProcessorLogGroup", "TemporaryQueryLogGroup"):
            self.assertEqual(self.resources[name]["Properties"]["RetentionInDays"], 7)

    def test_model_runtime_is_frozen_and_models_are_not_downloaded_at_runtime(self) -> None:
        for name in ("requirements-ml.txt", "requirements-convert.txt"):
            requirements = (REPOSITORY_ROOT / "backend" / name).read_text(encoding="utf-8")
            pins = [line for line in requirements.splitlines() if line and not line.startswith("#")]
            self.assertTrue(pins)
            for pin in pins:
                exact_version = "==" in pin and " @ " not in pin
                hash_pinned_pytorch_wheel = re.fullmatch(
                    r"[A-Za-z0-9_.-]+ @ https://download-r2\.pytorch\.org/"
                    r"[^#\s]+#sha256=[0-9a-f]{64}",
                    pin,
                )
                self.assertTrue(
                    exact_version or hash_pinned_pytorch_wheel,
                    f"Dependency is not immutably pinned: {pin}",
                )
        dockerfile = (REPOSITORY_ROOT / "backend" / "Dockerfile.ml").read_text(
            encoding="utf-8"
        )
        self.assertIn("COPY legacy/PacificBioArchive/mdv5a.pt /opt/models/mdv5a.pt", dockerfile)
        self.assertIn("COPY legacy/PacificBioArchive/model.pt /tmp/model.pt", dockerfile)
        self.assertIn("/opt/models/model.torchscript", dockerfile)
        self.assertIn("rglob('__pycache__')", dockerfile)
        self.assertNotIn("find ${LAMBDA_TASK_ROOT}", dockerfile)
        self.assertNotIn("curl ", dockerfile)
        self.assertNotIn("wget ", dockerfile)


if __name__ == "__main__":
    unittest.main()
