# Zerion operating model

## Agent entry point

The root `AGENTS.md` is the normative bootstrap for AI agents.

A fresh session reads:

```text
AGENTS.md
   |
   v
coordination/zerion.yaml
   |
   +--> projects/<project>.yaml
   +--> agents/<worker>.yaml
   +--> state/<worker>.yaml
                         |
                         v
                     mailbox PR
                         |
                         v
                  task PR / evidence
```

## Layers of durable truth

Zerion separates durable information by purpose.

### 1. Configuration

`coordination/zerion.yaml`, project files, and agent files define topology, identity, ownership, defaults, and canonical paths.

### 2. Current-state index

`coordination/state/<worker>.yaml` gives an agent a cheap machine-readable snapshot of the latest known worker/task state.

It is an index, not an immutable event log.

### 3. Control-plane event log

The long-lived mailbox PR records assignments, ACK claims, terminal worker reports, and orchestrator reviews in chronological order.

### 4. Substantive evidence

Task branches and PRs, commits, CI, formal verification, experimental outputs, and other artifacts establish what actually happened.

If a state index conflicts with newer durable mailbox or task evidence, use the newer evidence and repair the index. Chat memory never overrides durable GitHub evidence.

## Control plane and work plane

```text
Mailbox PR = control plane
Task PR    = work plane
```

Mailbox PRs should not contain substantive project changes.

## Worker identity

Worker identity is configuration, not runtime identity. A generic dispatcher may execute work as a named specialist worker only after reading the worker's agent file, state index, and mailbox.

## Bounded assignments

Workers execute the assigned objective and completion conditions. They do not invent the next major project objective. The orchestrator owns critical-path selection.

## Idempotency

Every task has a stable `task_id`. A dispatcher skips work when the task already has a terminal result or another valid ACK lease.

## ACK leases

An ACK contains a claim timestamp and lease duration. The default comes from `coordination/zerion.yaml`.

If a lease expires without a terminal result, the orchestrator may mark the claim stale and release or reassign it.

## State transitions

The normal current-state lifecycle is:

```text
idle
  -> assigned
  -> claimed
  -> done | blocked | needs_review
  -> idle | assigned | dormant
```

Mailbox events remain the audit history for those transitions.

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
