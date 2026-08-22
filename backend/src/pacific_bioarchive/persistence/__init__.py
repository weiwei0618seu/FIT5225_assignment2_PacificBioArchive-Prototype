"""In-memory and DynamoDB persistence adapters."""

from .dynamodb import DynamoDedupRepository, DynamoMediaRepository
from .memory import InMemoryDedupRepository, InMemoryMediaRepository

__all__ = [
    "DynamoDedupRepository",
    "DynamoMediaRepository",
    "InMemoryDedupRepository",
    "InMemoryMediaRepository",
]

