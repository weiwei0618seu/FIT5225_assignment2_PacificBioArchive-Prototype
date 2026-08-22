"""Use-case services shared by Lambda handlers and local tests."""

from .queries import (
    MediaQueryService,
    QueryResult,
    QueryValidationError,
    normalize_thumbnail_reference,
)
from .management import (
    AuthorizationError,
    BulkDeleteResult,
    MediaManagementService,
    ManagementValidationError,
    TagEditResult,
)

__all__ = [
    "MediaQueryService",
    "QueryResult",
    "QueryValidationError",
    "normalize_thumbnail_reference",
    "AuthorizationError",
    "BulkDeleteResult",
    "MediaManagementService",
    "ManagementValidationError",
    "TagEditResult",
]
