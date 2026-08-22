"""Shared API Gateway HTTP API v2 parsing, authentication and safe errors."""

from __future__ import annotations

import base64
import json
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from pacific_bioarchive.application.management import (
    AuthorizationError,
    ManagementValidationError,
)
from pacific_bioarchive.application.notifications import NotificationValidationError
from pacific_bioarchive.application.queries import QueryValidationError
from pacific_bioarchive.application.temp_queries import TemporaryQueryError
from pacific_bioarchive.domain.repositories import (
    ConflictError,
    DuplicateFileError,
    RecordNotFoundError,
)
from pacific_bioarchive.media.validation import MediaValidationError


class HttpApiError(ValueError):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


@dataclass(frozen=True, slots=True)
class AuthContext:
    subject: str
    email: str
    email_verified: bool


@dataclass(frozen=True, slots=True)
class HttpRequest:
    method: str
    path: str
    query: Mapping[str, str]
    body: dict[str, object]
    auth: AuthContext
    request_id: str


Action = Callable[[HttpRequest], tuple[int, object]]
LOGGER = logging.getLogger(__name__)


def dispatch_http(event: object, action: Action) -> dict[str, object]:
    request_id = _request_id(event)
    try:
        request = parse_http_request(event, request_id=request_id)
        status, payload = action(request)
        return json_response(status, payload)
    except Exception as exc:
        status, code, message = map_exception(exc)
        if status >= 500:
            LOGGER.exception("HTTP request %s failed with %s", request_id, code)
        return json_response(
            status,
            {
                "error": {
                    "code": code,
                    "message": message,
                    "request_id": request_id,
                    "details": {},
                }
            },
        )


def parse_http_request(event: object, *, request_id: str) -> HttpRequest:
    if not isinstance(event, dict):
        raise HttpApiError(400, "INVALID_HTTP_EVENT", "HTTP event must be an object")
    context = event.get("requestContext")
    if not isinstance(context, dict) or not isinstance(context.get("http"), dict):
        raise HttpApiError(400, "INVALID_HTTP_EVENT", "HTTP API v2 context is required")
    method = str(context["http"].get("method", "")).upper()
    path = str(event.get("rawPath") or context["http"].get("path") or "")
    if not method or not path.startswith("/"):
        raise HttpApiError(400, "INVALID_HTTP_EVENT", "HTTP method and path are required")

    authorizer = context.get("authorizer")
    jwt = authorizer.get("jwt") if isinstance(authorizer, dict) else None
    claims = jwt.get("claims") if isinstance(jwt, dict) else None
    subject = str(claims.get("sub", "")).strip() if isinstance(claims, dict) else ""
    if not subject:
        raise HttpApiError(401, "UNAUTHORIZED", "A valid Cognito JWT is required")
    email = str(claims.get("email", "")).strip() if isinstance(claims, dict) else ""
    verified_raw = claims.get("email_verified", False) if isinstance(claims, dict) else False
    email_verified = verified_raw is True or str(verified_raw).lower() == "true"

    raw_query = event.get("queryStringParameters") or {}
    if not isinstance(raw_query, dict):
        raise HttpApiError(400, "INVALID_QUERY_STRING", "Query parameters must be an object")
    query = {str(key): str(value) for key, value in raw_query.items()}
    body = _parse_body(event)
    return HttpRequest(
        method=method,
        path=path.rstrip("/") or "/",
        query=query,
        body=body,
        auth=AuthContext(subject, email, email_verified),
        request_id=request_id,
    )


def json_response(status_code: int, payload: object) -> dict[str, object]:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json; charset=utf-8",
            "cache-control": "no-store",
        },
        "body": json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
        "isBase64Encoded": False,
    }


def map_exception(exc: Exception) -> tuple[int, str, str]:
    if isinstance(exc, HttpApiError):
        return exc.status_code, exc.code, str(exc)
    if isinstance(exc, DuplicateFileError):
        return 409, "DUPLICATE_FILE", "This file has already been uploaded"
    if isinstance(exc, RecordNotFoundError):
        return 404, "MEDIA_NOT_FOUND", "The requested media was not found"
    if isinstance(exc, AuthorizationError):
        return 403, "FORBIDDEN", "You cannot modify this media"
    if isinstance(exc, ConflictError):
        return 409, "CONFLICT", "The resource changed; retry the request"
    if isinstance(
        exc,
        (
            MediaValidationError,
            ManagementValidationError,
            QueryValidationError,
            NotificationValidationError,
            TemporaryQueryError,
        ),
    ):
        code = getattr(exc, "code", "INVALID_REQUEST")
        status = 401 if code == "UNAUTHENTICATED" else 400
        return status, code, str(exc)
    if isinstance(exc, (KeyError, TypeError, ValueError, json.JSONDecodeError)):
        return 400, "INVALID_REQUEST", "The request body or parameters are invalid"
    return 500, "INTERNAL_ERROR", "The service could not complete the request"


def require_list(body: Mapping[str, object], name: str) -> list[object]:
    value = body.get(name, [])
    if not isinstance(value, list):
        raise HttpApiError(400, "INVALID_REQUEST", f"{name} must be an array")
    return value


def require_object(body: Mapping[str, object], name: str) -> dict[str, object]:
    value = body.get(name)
    if not isinstance(value, dict):
        raise HttpApiError(400, "INVALID_REQUEST", f"{name} must be an object")
    return value


def _parse_body(event: dict[str, object]) -> dict[str, object]:
    raw = event.get("body")
    if raw in (None, ""):
        return {}
    if not isinstance(raw, str):
        raise HttpApiError(400, "INVALID_JSON", "Request body must be JSON text")
    if event.get("isBase64Encoded") is True:
        try:
            raw = base64.b64decode(raw, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise HttpApiError(400, "INVALID_JSON", "Request body encoding is invalid") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HttpApiError(400, "INVALID_JSON", "Request body is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise HttpApiError(400, "INVALID_JSON", "Request JSON must be an object")
    return parsed


def _request_id(event: object) -> str:
    if isinstance(event, dict) and isinstance(event.get("requestContext"), dict):
        return str(event["requestContext"].get("requestId", "unknown"))
    return "unknown"
