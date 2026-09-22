# Protocol

## Assignment

A bounded task is a GitHub Issue with the configured title prefix and a body beginning:

```text
[ORCHESTRATOR:v1]
task_id: example-theory-0001
project: example-project
worker: theory-worker
status: ASSIGNED
priority: P1
depends_on: []
```

## Claim

Before substantive work, a worker posts:

```text
[WORKER:theory-worker:v1]
task_id: example-theory-0001
status: ACK
dispatcher: pool-A
claimed_at: 2026-01-01T00:00:00Z
lease_hours: 3
```

The first valid unexpired ACK owns the task.

## Work

For repository changes, create a task branch and linked draft PR early.

A closing keyword such as `Resolves #123` may connect merge to Issue completion.

## Worker terminal event

Post DONE, BLOCKED, or NEEDS_REVIEW on the Issue with exact durable evidence.

## Orchestrator review

Post ACCEPTED, REVISE, or REJECTED after inspecting actual evidence.

Native PR reviews are optional UX. The Issue-side Zerion review event is the protocol record.

## Live-state reduction

Task status is reconstructed by replaying Issue comments in order:

```text
Issue assignment       -> assigned
ACK                    -> claimed
BLOCKED                -> blocked
DONE / NEEDS_REVIEW    -> needs_review
ACCEPTED               -> accepted
REVISE                 -> revise
REJECTED               -> rejected
```

No YAML state cache is required.

## Derived labels

GitHub Actions reduce the same event history and synchronize one Zerion status label plus the configured task/priority labels.

Labels aid search and Projects. They are not canonical state.

## Idempotency

Every worker must read the Issue history before acting. Stable task IDs, ACK leases, terminal events, and reviews make polling retry-safe.
