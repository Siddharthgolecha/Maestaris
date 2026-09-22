# Protocol

## Bootstrap

Every AI agent starts with root `AGENTS.md`, then reads the global registry, relevant project/agent/state files, mailbox PR, and task evidence.

## Assignment

```text
[ORCHESTRATOR:v1]
task_id: example-theory-0001
project: example-project
worker: theory-worker
status: ASSIGNED
base: main
priority: P1
objective: ...
constraints:
  - ...
completion:
  - ...
```

The orchestrator also updates the worker's state index to `assigned`.

## ACK

Before substantive work, the dispatcher checks the mailbox for idempotency/conflicting claims, then claims the task.

```text
[WORKER:theory-worker:v1]
task_id: example-theory-0001
status: ACK
dispatcher: pool-A
claimed_at: 2026-01-01T00:00:00Z
lease_hours: 3
```

The worker state index moves to `claimed`.

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

The state index mirrors the latest terminal state and references the task evidence.

## Orchestrator review

```text
[ORCHESTRATOR-REVIEW:v1]
task_id: example-theory-0001
status: ACCEPTED
summary: ...
next_task: example-theory-0002
```

Review states are `ACCEPTED`, `REVISE`, and `REJECTED`.

A review is valid only after inspecting durable evidence, not merely the worker's summary.

## State index

The current-state file is optimized for discovery, not historical audit. It records:

- worker and project identity;
- lifecycle;
- mailbox PR;
- current task;
- ACK claim;
- latest result;
- latest orchestrator review;
- update timestamp.

The mailbox PR remains the chronological control-plane history.

## Idempotency

A worker skips an assignment when a terminal result already exists or another valid ACK lease owns it. An orchestrator skips a terminal result when a later review for the same task already exists.

If the state index disagrees with newer mailbox/task evidence, repair the index and continue from the newer evidence.
