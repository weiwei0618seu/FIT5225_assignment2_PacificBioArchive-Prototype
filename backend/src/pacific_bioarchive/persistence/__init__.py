"""In-memory and DynamoDB persistence adapters."""

from .dynamodb import DynamoDedupRepository, DynamoMediaRepository
from .memory import InMemoryDedupRepository, InMemoryMediaRepository
from .s3 import S3ObjectStorage

__all__ = [
    "DynamoDedupRepository",
    "DynamoMediaRepository",
    "InMemoryDedupRepository",
    "InMemoryMediaRepository",
    "S3ObjectStorage",
]
