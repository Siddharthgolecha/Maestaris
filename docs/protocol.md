# Protocol

## 1. Publish READY work

A bounded task is a GitHub Issue with the configured title prefix and a body beginning:

```text
[ORCHESTRATOR:v1]
task_id: example-proof-0001
project: example-project
priority: P1
depends_on: []
```

An open task Issue is **READY by default**.

Do not write `worker: unassigned`. Omit `worker` for ordinary queue work.

Use an optional worker pin only when a task genuinely requires one specialist:

```text
worker: example-security-auditor
```

The Issue body may contain legacy `status: ASSIGNED` during migration, but new tasks should not encode live state in the body.

## 2. Claim

A worker pool selects an eligible READY task and posts:

```text
[WORKER:theory-worker:v1]
task_id: example-proof-0001
status: ACK
dispatcher: pool-A
claimed_at: 2026-01-01T00:00:00Z
lease_hours: 3
```

The ACK establishes the worker identity and lease. Before ACK, the task has no owner.

The first valid unexpired ACK owns the task.

## 3. Work

For repository changes, create a task branch and linked draft PR early.

A closing keyword such as `Resolves #123` may connect merge to Issue completion.

## 4. Worker terminal event

Post DONE, BLOCKED, or NEEDS_REVIEW on the Issue with exact durable evidence.

## 5. Orchestrator review

Post ACCEPTED, REVISE, or REJECTED after inspecting actual evidence.

Native PR reviews are optional UX. The Issue-side Zerion review event is the protocol record.

## Live-state reduction

Task status is reconstructed by replaying Issue comments in order:

```text
open task, no ACK       -> ready
ACK                     -> claimed
BLOCKED                 -> blocked
DONE / NEEDS_REVIEW     -> needs_review
ACCEPTED                -> accepted
REVISE                  -> revise
REJECTED                -> rejected
```

Worker ownership is reconstructed from the active ACK, not from task creation metadata.

## Derived labels

GitHub Actions reduce the same event history and synchronize one Zerion status label plus task/priority labels.

Labels aid search and Projects. They are not canonical state.

## Idempotency

Every worker reads the Issue history before acting. Stable task IDs, ACK leases, terminal events, and reviews make polling retry-safe.
