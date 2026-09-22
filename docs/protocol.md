# Protocol

## Assignment

```text
[ORCHESTRATOR:v1]
task_id: example-theory-0001
project: example-project
worker: theory-worker
status: ASSIGNED
base: main
objective: ...
constraints:
  - ...
completion:
  - ...
```

## ACK

Before substantive work, the dispatcher claims the task.

```text
[WORKER:theory-worker:v1]
task_id: example-theory-0001
status: ACK
dispatcher: pool-A
claimed_at: 2026-01-01T00:00:00Z
lease_hours: 3
```

## Terminal worker report

```text
[WORKER:theory-worker:v1]
task_id: example-theory-0001
status: DONE
commit: <sha>
pr: <number-or-url>
summary: ...
claim_changes: none
next_blocker: none
```

Allowed terminal states are `DONE`, `BLOCKED`, and `NEEDS_REVIEW`.

## Orchestrator review

```text
[ORCHESTRATOR-REVIEW:v1]
task_id: example-theory-0001
status: ACCEPTED
summary: ...
next_task: example-theory-0002
```

Review states are `ACCEPTED`, `REVISE`, and `REJECTED`.

## Idempotency

A worker skips an assignment when a terminal result already exists or another valid ACK lease owns it. An orchestrator skips a terminal result when a later review for the same task already exists.
