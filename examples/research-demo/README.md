# Research demo

This deliberately small example shows how three workers can collaborate on a bounded research-and-build question.

**Question:** Compare two implementation approaches for a toy key-value service and produce a recommendation supported by a prototype and audit.

Workers:

- `theory-worker`: defines criteria and researches trade-offs;
- `implementation-worker`: builds a minimal prototype and tests it;
- `audit-worker`: checks that the final synthesis is supported by durable evidence.

The example is domain-light on purpose. It demonstrates orchestration mechanics rather than a specific scientific claim.
