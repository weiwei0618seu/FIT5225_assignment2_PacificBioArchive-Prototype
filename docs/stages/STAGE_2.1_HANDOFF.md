# Stage 2.1 Handoff — Domain and Persistence

## Added behavior

Application services can now persist media without depending on boto3. The same
business behavior runs against deterministic in-memory repositories in tests
and conditional DynamoDB tables in AWS.

## Files to understand

- `domain/media.py` — aggregate invariants and state/version changes
- `domain/repositories.py` — persistence ports and conflicts
- `persistence/memory.py` — test/local adapter
- `persistence/dynamodb.py` — AWS conditional and serialization adapter

## Verification

Run all 31 tests. Pay particular attention to the concurrent duplicate and
optimistic version conflict cases.

## Demo questions

- How can two simultaneous uploads of the same bytes be prevented?
- Why does an abandoned reservation have TTL but a committed checksum not?
- How are lost updates to manual tags prevented?
- Why are floats converted to Decimal for DynamoDB?

