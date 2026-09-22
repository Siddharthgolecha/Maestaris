# Zerion operating model

## Canonical state

The default precedence is:

```text
repository state > chat memory > remembered summaries
```

Projects may name additional canonical files. A worker must read them before acting.

## Control plane and work plane

```text
Mailbox PR = control plane
Task PR    = work plane
```

Mailbox PRs are long-lived coordination channels. They carry assignments, ACK claims, terminal worker reports, and orchestrator reviews. They should not contain substantive project changes.

## Worker identity

Worker identity is configuration, not runtime identity. A generic dispatcher may execute work as a named specialist worker as long as it reads that worker's configuration and assignment first.

## Bounded assignments

Workers execute the assigned objective and completion conditions. They do not invent the next major project objective. The orchestrator owns critical-path selection.

## Idempotency

Every task has a stable `task_id`. A dispatcher skips work when the task already has a terminal result or another valid ACK lease.

## ACK leases

An ACK may contain:

```text
claimed_at: <timestamp>
lease_hours: 3
```

If the lease expires without a terminal result, the orchestrator may mark the task stalled and release or reassign it.

## Terminal states

Worker terminal states:

```text
DONE
BLOCKED
NEEDS_REVIEW
```

Orchestrator review states:

```text
ACCEPTED
REVISE
REJECTED
```

## Dormancy

Workers may be `dormant` when no useful work is unblocked. Zerion optimizes useful progress, not agent activity.
