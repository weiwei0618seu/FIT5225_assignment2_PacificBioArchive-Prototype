from __future__ import annotations

import json
import unittest
from pathlib import Path

from pacific_bioarchive.auth.config import JwtAuthorizerConfig

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = REPOSITORY_ROOT / "infrastructure" / "auth-and-iam.json"


class JwtAuthorizerConfigTests(unittest.TestCase):
    def test_cognito_issuer_audience_and_identity_source(self) -> None:
        config = JwtAuthorizerConfig.for_cognito(
            region="ap-southeast-2",
            user_pool_id="ap-southeast-2_Example123",
            app_client_id="client123",
        )
        self.assertEqual(
            config.issuer,
            "https://cognito-idp.ap-southeast-2.amazonaws.com/"
            "ap-southeast-2_Example123",
        )
        self.assertEqual(config.audience, ("client123",))
        self.assertEqual(
            config.to_sam(),
            {
                "IdentitySource": "$request.header.Authorization",
                "JwtConfiguration": {
                    "Issuer": config.issuer,
                    "Audience": ["client123"],
                },
            },
        )

    def test_invalid_region_pool_and_client_are_rejected(self) -> None:
        invalid = [
            {"region": "invalid", "user_pool_id": "pool", "app_client_id": "client"},
            {
                "region": "ap-southeast-2",
                "user_pool_id": "pool/unsafe",
                "app_client_id": "client",
            },
            {
                "region": "ap-southeast-2",
                "user_pool_id": "pool",
                "app_client_id": "",
            },
        ]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                JwtAuthorizerConfig.for_cognito(**values)


class AuthIamTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        cls.resources = cls.template["Resources"]

    def test_google_credentials_are_noecho_parameters_not_literals(self) -> None:
        parameters = self.template["Parameters"]
        self.assertTrue(parameters["GoogleClientId"]["NoEcho"])
        self.assertTrue(parameters["GoogleClientSecret"]["NoEcho"])
        provider = self.resources["GoogleIdentityProvider"]["Properties"]
        self.assertEqual(provider["ProviderType"], "Google")
        self.assertEqual(provider["ProviderDetails"]["client_secret"], {"Ref": "GoogleClientSecret"})
        self.assertEqual(provider["ProviderDetails"]["authorize_scopes"], "openid email profile")

    def test_registration_verification_password_and_recovery_match_requirements(self) -> None:
        pool = self.resources["UserPool"]["Properties"]
        self.assertEqual(pool["UsernameAttributes"], ["email"])
        self.assertEqual(pool["AutoVerifiedAttributes"], ["email"])
        self.assertEqual(pool["MfaConfiguration"], "OFF")
        schema = {item["Name"]: item for item in pool["Schema"]}
        self.assertEqual(set(schema), {"email", "given_name", "family_name"})
        self.assertTrue(all(item["Required"] for item in schema.values()))
        password = pool["Policies"]["PasswordPolicy"]
        self.assertGreaterEqual(password["MinimumLength"], 12)
        self.assertTrue(all(password[key] for key in (
            "RequireLowercase", "RequireUppercase", "RequireNumbers", "RequireSymbols"
        )))
        self.assertEqual(
            pool["AccountRecoverySetting"]["RecoveryMechanisms"],
            [{"Name": "verified_email", "Priority": 1}],
        )

    def test_spa_uses_pkce_compatible_code_flow_without_client_secret(self) -> None:
        client = self.resources["UserPoolClient"]["Properties"]
        self.assertFalse(client["GenerateSecret"])
        self.assertEqual(client["AllowedOAuthFlows"], ["code"])
        self.assertTrue(client["AllowedOAuthFlowsUserPoolClient"])
        providers = client["SupportedIdentityProviders"]["Fn::If"]
        self.assertEqual(providers[0], "GoogleFederationEnabled")
        self.assertEqual(providers[1], ["COGNITO", {"Ref": "GoogleIdentityProvider"}])
        self.assertEqual(providers[2], ["COGNITO"])
        self.assertEqual(set(client["AllowedOAuthScopes"]), {"openid", "email", "profile"})
        self.assertEqual(client["PreventUserExistenceErrors"], "ENABLED")

    def test_native_bootstrap_is_allowed_but_hd_google_requires_credentials(self) -> None:
        parameters = self.template["Parameters"]
        self.assertEqual(parameters["EnableGoogleFederation"]["Default"], "false")
        self.assertEqual(parameters["GoogleClientId"]["Default"], "")
        self.assertEqual(parameters["GoogleClientSecret"]["Default"], "")
        provider = self.resources["GoogleIdentityProvider"]
        self.assertEqual(provider["Condition"], "GoogleFederationEnabled")
        assertions = self.template["Rules"]["GoogleCredentialsRequiredWhenEnabled"]
        self.assertIn("Assertions", assertions)

    def test_lambda_roles_trust_only_lambda_and_have_no_star_actions_or_resources(self) -> None:
        for logical_id in ("CoreApiRole", "MediaProcessorRole", "TemporaryQueryRole"):
            with self.subTest(role=logical_id):
                role = self.resources[logical_id]["Properties"]
                trust = role["AssumeRolePolicyDocument"]["Statement"]
                self.assertEqual(
                    trust,
                    [{
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }],
                )
                statements = role["Policies"][0]["PolicyDocument"]["Statement"]
                for statement in statements:
                    actions = statement["Action"]
                    actions = [actions] if isinstance(actions, str) else actions
                    self.assertNotIn("*", actions)
                    self.assertNotEqual(statement["Resource"], "*")

    def test_roles_separate_core_processing_and_ml_permissions(self) -> None:
        def actions(role_name: str) -> set[str]:
            statements = self.resources[role_name]["Properties"]["Policies"][0][
                "PolicyDocument"
            ]["Statement"]
            return {
                action
                for statement in statements
                for action in (
                    [statement["Action"]]
                    if isinstance(statement["Action"], str)
                    else statement["Action"]
                )
            }

        core = actions("CoreApiRole")
        processor = actions("MediaProcessorRole")
        temporary = actions("TemporaryQueryRole")
        self.assertIn("sns:Subscribe", core)
        core_statements = self.resources["CoreApiRole"]["Properties"]["Policies"][0][
            "PolicyDocument"
        ]["Statement"]
        subscription_access = next(
            statement
            for statement in core_statements
            if statement.get("Sid") == "OwnTopicSubscriptions"
        )
        self.assertEqual(subscription_access["Resource"], {"Ref": "NotificationTopicArn"})
        self.assertEqual(
            set(subscription_access["Action"]),
            {
                "sns:GetSubscriptionAttributes",
                "sns:SetSubscriptionAttributes",
                "sns:Unsubscribe",
            },
        )
        self.assertNotIn("sns:Subscribe", processor)
        self.assertIn("sns:Publish", processor)
        self.assertNotIn("sns:Publish", temporary)
        self.assertEqual(temporary.intersection({"dynamodb:PutItem", "dynamodb:DeleteItem"}), set())


if __name__ == "__main__":
    unittest.main()
