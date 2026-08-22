"""Validated Cognito JWT-authorizer values shared with infrastructure tests."""

from __future__ import annotations

import re
from dataclasses import dataclass

REGION_PATTERN = re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-\d$")
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class JwtAuthorizerConfig:
    issuer: str
    audience: tuple[str, ...]
    identity_source: str = "$request.header.Authorization"

    @classmethod
    def for_cognito(
        cls, *, region: str, user_pool_id: str, app_client_id: str
    ) -> JwtAuthorizerConfig:
        normalized_region = region.strip().lower()
        pool = user_pool_id.strip()
        client = app_client_id.strip()
        if not REGION_PATTERN.fullmatch(normalized_region):
            raise ValueError("AWS region is invalid")
        if not SAFE_ID_PATTERN.fullmatch(pool) or not SAFE_ID_PATTERN.fullmatch(client):
            raise ValueError("Cognito pool/client identifiers are invalid")
        return cls(
            issuer=f"https://cognito-idp.{normalized_region}.amazonaws.com/{pool}",
            audience=(client,),
        )

    def to_sam(self) -> dict[str, object]:
        if not self.issuer.startswith("https://") or not self.audience:
            raise ValueError("A HTTPS issuer and at least one audience are required")
        return {
            "IdentitySource": self.identity_source,
            "JwtConfiguration": {
                "Issuer": self.issuer,
                "Audience": list(self.audience),
            },
        }
