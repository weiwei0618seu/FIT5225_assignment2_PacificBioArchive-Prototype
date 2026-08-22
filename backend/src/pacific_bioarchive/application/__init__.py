"""Use-case services shared by Lambda handlers and local tests."""

from .management import (
    AuthorizationError,
    BulkDeleteResult,
    ManagementValidationError,
    MediaManagementService,
    TagEditResult,
)
from .queries import (
    MediaQueryService,
    QueryResult,
    QueryValidationError,
    normalize_thumbnail_reference,
)
from .uploads import UploadService, UploadTicket

__all__ = [
    "AuthorizationError",
    "BulkDeleteResult",
    "ManagementValidationError",
    "MediaManagementService",
    "MediaQueryService",
    "QueryResult",
    "QueryValidationError",
    "TagEditResult",
    "UploadService",
    "UploadTicket",
    "normalize_thumbnail_reference",
]
