# Architecture

Zerion is an agent-native, repository-first orchestration protocol.

## Entry path

A fresh AI session enters through `AGENTS.md`:

```text
User / scheduler / runtime
          |
          v
      AGENTS.md
          |
          v
coordination/zerion.yaml
          |
   +------+------+ 
   |      |      |
project  agent  state
   |      |      |
   +------+------+ 
          |
          v
      mailbox PR
          |
          v
 task PR / durable evidence
```

The CLI is optional setup/maintenance tooling, not the primary worker runtime.

## Durable layers

### Global registry

`coordination/zerion.yaml` identifies protocol version, canonical branch, orchestrator, worker pools, defaults, and projects.

### Project and agent registries

Project files define membership and canonical paths. Agent files define specialist identity and dispatcher-pool ownership.

### Current-state index

`coordination/state/<worker>.yaml` is a small machine-readable snapshot that lets a fresh agent cheaply discover the latest known task, claim, result, review, and mailbox.

It is deliberately treated as an index rather than final evidence.

### Control-plane event log

Long-lived mailbox PRs record assignments, ACKs, worker terminal reports, and orchestrator reviews.

### Work-plane evidence

Task PRs contain actual code, research, data, proofs, experiments, or writing. CI and artifacts verify or preserve results.

## Precedence

When data disagrees, use the newest relevant durable GitHub evidence. A stale state index should be repaired; it must not override a newer mailbox event or task PR.

Chat memory never outranks durable repository/GitHub state.

## Reconstruction property

A healthy Zerion project can be reconstructed without the original conversations. Current topology, task ownership, decisions, blockers, and evidence all have durable representations.

## Runtime adapters

ChatGPT conversations, scheduled tasks, API agents, coding agents, CI jobs, or other runtimes may act as dispatchers or workers as long as they follow `AGENTS.md` and the same task/ACK/result/review semantics.
