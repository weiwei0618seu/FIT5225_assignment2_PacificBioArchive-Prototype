# Stage 2.2 Handoff — Query Engine

## Added behavior

The complete query semantics now live in one service, so HTTP routes and the UI
cannot accidentally implement different OR/count behavior.

## Files to understand

- `application/queries.py`
- `tests/unit/test_queries.py`
- query semantics in `docs/DATA_MODEL.md`

## Verification

Run all 41 tests. The key Rubric proof is that a record satisfying only wombat
or only magpie is excluded from `{wombat:2, magpie:1}`.

## Demo questions

- Where is AND enforced?
- Does `>=3` include exactly three animals?
- How do manual tags affect minimum counts?
- How can an expiring thumbnail URL still identify a durable record?
- Why is the temporary query's detected count reduced to presence?

