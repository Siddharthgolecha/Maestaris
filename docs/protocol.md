# Protocol

## 1. Task Issue

Create an Issue with title prefix `[Zerion task]` and a body beginning with:

```text
[ORCHESTRATOR:v1]
task_id: example-theory-0001
project: example-project
worker: theory-worker
status: ASSIGNED
priority: P1
```

Record the Issue number in the worker state index.

## 2. ACK

Before substantive work, the worker posts:

```text
[WORKER:theory-worker:v1]
task_id: example-theory-0001
status: ACK
dispatcher: pool-A
claimed_at: 2026-01-01T00:00:00Z
lease_hours: 3
```

Then state moves to `claimed`.

## 3. Work PR

For repository changes, use a branch such as:

```text
zerion/task/123-short-slug
```

Open a draft PR early and link it to the task Issue. A closing keyword such as `Resolves #123` is preferred when merge should finish the task.

## 4. Terminal worker result

Post DONE, BLOCKED, or NEEDS_REVIEW on the Issue with exact evidence.

## 5. Orchestrator review

Inspect actual evidence. Native PR reviews may mirror the decision, but always record:

```text
[ORCHESTRATOR-REVIEW:v1]
task_id: example-theory-0001
status: ACCEPTED
```

Then synchronize state.

- ACCEPTED: finalize/integrate work and close Issue as completed.
- REVISE: leave Issue open.
- REJECTED: close Issue as not planned.

## Idempotency

Stable task IDs plus ACK leases prevent repeated polling from duplicating work. The Issue comment history is checked before any claim or terminal action.

## State index

The YAML state file is optimized for discovery and recovery. It must never override newer GitHub Issue/PR evidence.
