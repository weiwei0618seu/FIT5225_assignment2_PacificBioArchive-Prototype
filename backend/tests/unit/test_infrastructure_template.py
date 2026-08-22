from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Any

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = REPOSITORY_ROOT / "infrastructure" / "template.yaml"
BOOTSTRAP_PATH = REPOSITORY_ROOT / "infrastructure" / "github-oidc-bootstrap.yaml"


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

    def test_core_api_sam_context_contains_importable_handler_and_dependencies(self) -> None:
        function = self.resources["CoreApiFunction"]["Properties"]
        self.assertEqual(function["CodeUri"], "../backend/src/")
        self.assertEqual(
            function["Handler"], "pacific_bioarchive.handlers.api.lambda_handler"
        )
        code_root = (TEMPLATE_PATH.parent / function["CodeUri"]).resolve()
        self.assertTrue(code_root.joinpath("pacific_bioarchive/handlers/api.py").is_file())
        requirements = code_root.joinpath("requirements.txt").read_text(encoding="utf-8")
        self.assertEqual(
            requirements.splitlines(), ["Pillow==12.0.0", "boto3==1.40.0"]
        )

    def test_ml_functions_require_one_immutable_sydney_ecr_digest(self) -> None:
        pattern = self.template["Parameters"]["MlImageUri"]["AllowedPattern"]
        valid = (
            "123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/"
            f"pacific-bioarchive-prototype-ml@sha256:{'a' * 64}"
        )
        self.assertIsNotNone(re.fullmatch(pattern, valid))
        self.assertIsNone(re.fullmatch(pattern, valid.replace("ap-southeast-2", "us-east-1")))
        self.assertIsNone(re.fullmatch(pattern, valid.replace("@sha256:", ":latest")))
        for name in ("MediaProcessorFunction", "TemporaryQueryFunction"):
            with self.subTest(function=name):
                resource = self.resources[name]
                self.assertEqual(resource["Properties"]["ImageUri"], {"Ref": "MlImageUri"})
                self.assertNotIn("Metadata", resource)

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
        self.assertIn("pip uninstall --yes opencv-python", dockerfile)
        self.assertIn("--force-reinstall --no-deps opencv-python-headless", dockerfile)
        self.assertNotIn("curl ", dockerfile)
        self.assertNotIn("wget ", dockerfile)


class GitHubOidcBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = yaml.load(
            BOOTSTRAP_PATH.read_text(encoding="utf-8"), Loader=CloudFormationLoader
        )
        cls.resources = cls.template["Resources"]

    def test_trust_is_exactly_one_repository_branch_and_audience(self) -> None:
        statement = self.resources["GitHubEcrPushRole"]["Properties"][
            "AssumeRolePolicyDocument"
        ]["Statement"][0]
        self.assertEqual(statement["Action"], "sts:AssumeRoleWithWebIdentity")
        conditions = statement["Condition"]["StringEquals"]
        self.assertEqual(
            conditions["token.actions.githubusercontent.com:aud"], "sts.amazonaws.com"
        )
        self.assertEqual(
            conditions["token.actions.githubusercontent.com:sub"],
            {
                "Sub": "repo:${GitHubOrganization}@${GitHubOrganizationId}/"
                "${GitHubRepository}@${GitHubRepositoryId}:"
                "ref:refs/heads/${DeploymentBranch}"
            },
        )
        parameters = self.template["Parameters"]
        self.assertEqual(parameters["GitHubOrganizationId"]["Default"], "265754710")
        self.assertEqual(parameters["GitHubRepositoryId"]["Default"], "1339555089")

    def test_oidc_provider_is_retained_across_repeat_bootstrap_updates(self) -> None:
        provider = self.resources["GitHubOidcProvider"]
        self.assertEqual(provider["DeletionPolicy"], "Retain")
        self.assertEqual(provider["UpdateReplacePolicy"], "Retain")
        self.assertEqual(provider["Properties"]["ClientIdList"], ["sts.amazonaws.com"])

    def test_role_can_push_only_one_ecr_repository(self) -> None:
        statements = self.resources["GitHubEcrPushRole"]["Properties"]["Policies"][0][
            "PolicyDocument"
        ]["Statement"]
        login, repository = statements
        self.assertEqual(login["Action"], "ecr:GetAuthorizationToken")
        self.assertEqual(login["Resource"], "*")
        self.assertEqual(repository["Resource"], {"GetAtt": "MlImageRepository.Arn"})
        self.assertTrue(all(action.startswith("ecr:") for action in repository["Action"]))
        self.assertNotIn("ecr:DeleteRepository", repository["Action"])

    def test_repository_is_immutable_scanned_retained_and_lifecycle_bounded(self) -> None:
        repository = self.resources["MlImageRepository"]
        self.assertEqual(repository["DeletionPolicy"], "Retain")
        properties = repository["Properties"]
        self.assertEqual(properties["ImageTagMutability"], "IMMUTABLE")
        self.assertTrue(properties["ImageScanningConfiguration"]["ScanOnPush"])
        lifecycle = properties["LifecyclePolicy"]["LifecyclePolicyText"]
        self.assertIn('"imageCountMoreThan"', lifecycle)
        self.assertIn('"countNumber":1', lifecycle)


if __name__ == "__main__":
    unittest.main()
