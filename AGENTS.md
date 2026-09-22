# Zerion agent operating instructions

This repository uses Zerion's repository-first orchestration protocol.

**Start here.** A fresh AI session should be able to reconstruct its operating state from GitHub without relying on prior chat history.

## Source-of-truth order

Use durable repository and GitHub evidence in this order:

1. this `AGENTS.md` for operating instructions;
2. `coordination/zerion.yaml` for global Zerion topology, pools, defaults, and registered projects;
3. `coordination/projects/<project>.yaml` for project membership and canonical paths;
4. `coordination/agents/<worker>.yaml` for worker identity and dispatcher-pool ownership;
5. `coordination/state/<worker>.yaml` as the fast current-state index;
6. the worker's mailbox PR as the chronological control-plane event log;
7. task PRs, commits, CI, proofs, experiments, and artifacts as the evidence for substantive work.

The state file is an index, not an excuse to ignore newer GitHub evidence. If a mailbox event or task PR is newer than the index, use the newer durable evidence, report the index as stale, and repair it as part of the next coordination update.

Chat memory and remembered summaries are advisory only.

## Resolve your role

Use an explicitly supplied role or worker identity when one is given.

- **Orchestrator:** read `prompts/orchestrator.md`.
- **Worker pool / dispatcher:** read `prompts/worker-pool.md`, then consider only workers assigned to that pool.
- **Named specialist worker:** read `prompts/worker.md` and that worker's agent/state files.
- **Auditor:** read `prompts/auditor.md`.

If no worker identity is supplied and the request is project-level coordination, default to the orchestrator role. Do not invent a specialist identity from memory.

## Deterministic bootstrap

Before substantive work:

1. Read `coordination/zerion.yaml`.
2. Resolve the relevant project or projects from the user's request and the registry.
3. Read each relevant `coordination/projects/<project>.yaml`.
4. Resolve the worker identity, if any, and read:
   - `coordination/agents/<worker>.yaml`;
   - `coordination/state/<worker>.yaml`.
5. Inspect the configured mailbox PR before trusting the indexed task state.
6. Check the task ID for:
   - a later terminal worker result;
   - a later orchestrator review;
   - a valid ACK lease owned by another dispatcher.
7. Read every path listed in the project's `canonical_paths` that is relevant to the assignment.
8. Inspect the actual task PR/commit/CI/artifact before accepting or extending a substantive result.
9. Only then perform work.

## Control plane vs work plane

```text
Mailbox PR = control plane
Task PR    = work plane
```

Mailbox PRs carry assignments, ACKs, terminal reports, and orchestrator reviews. Do not put substantive project changes on mailbox branches.

Substantive code, research, proofs, experiments, data, or writing belongs on a task branch and task PR.

## State transitions

The machine-readable state index uses these normal transitions:

```text
idle
  -> assigned
  -> claimed
  -> done | blocked | needs_review
  -> idle | assigned | dormant
```

When changing control-plane state, keep the mailbox event log and `coordination/state/<worker>.yaml` synchronized. The mailbox event should remain the auditable history; the state file should summarize the latest known state.

## Idempotency

Every task must have a stable `task_id`.

Before execution, skip or stop when:

- the same task already has a terminal result;
- the same terminal result already has an orchestrator review;
- another dispatcher owns an unexpired ACK lease;
- the task's dependencies are not satisfied.

Retries must be safe. Never create duplicate substantive work merely because a scheduler or user invoked the same worker twice.

## Evidence and review

A `DONE` message is not proof by itself. Orchestrators must inspect referenced commits, PRs, CI, formal verification, experimental output, or other durable evidence before `ACCEPTED`.

Preserve negative and inconclusive results. Do not silently upgrade them to success.

## Blocking and dormancy

A precise blocker is a valid result. Record the first exact missing dependency, failed assumption, permission problem, unavailable artifact, or failed verification.

Dormancy is healthy. Do not invent tasks just to keep workers active.

## Repository-local instructions

If a project adds a more specific nested `AGENTS.md`, apply it to files in its scope in addition to these root Zerion rules. More specific repository instructions may narrow behavior but should not break Zerion's durability, idempotency, or evidence requirements.
