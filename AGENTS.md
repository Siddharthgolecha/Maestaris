# Zerion agent operating instructions

This repository uses Zerion's GitHub-native orchestration protocol.

**Core rule:** chats reason; GitHub remembers.

A fresh AI session must be able to reconstruct its role and current work from this repository plus GitHub Issues/PRs without relying on earlier chat history.

## What is canonical

Use durable evidence in this order:

1. this `AGENTS.md`;
2. `coordination/zerion.yaml`;
3. the relevant `coordination/projects/<project>.yaml`;
4. the relevant `coordination/agents/<worker>.yaml`;
5. GitHub task Issues and their comments;
6. linked pull requests, commits, Actions/checks, proofs, experiments, and artifacts.

There is intentionally **no mutable worker-state YAML** in protocol v3.

GitHub task Issues and their comments are the live control plane.

Labels and GitHub Projects are derived views. If a label or Project field disagrees with the Issue history, the Issue history wins.

Chat memory and remembered summaries are advisory only.

## Agent autonomy contract

Zerion is a **bootstrap constitution**, not a fixed application architecture.

Once this repository is created from the template, optimize it for the actual project rather than preserving template shape for its own sake.

You are empowered to make sensible, reversible repository and GitHub changes without asking for permission when they materially improve the project.

Examples include:

- creating or reorganizing GitHub Projects, views, labels, milestones, and dashboards;
- using native Issue Types / Issue Fields when the repository/account supports them;
- creating parent/sub-issues and native dependency relationships;
- adding or refining Actions workflows, checks, reusable workflows, and release automation;
- adding repository rulesets, required checks, branch conventions, and review structure;
- creating releases, artifacts, attestations, provenance structures, and evidence layouts;
- refactoring repository directories, prompts, templates, and project-specific `AGENTS.md` files;
- retiring Zerion defaults that are redundant once a stronger native project-specific mechanism exists.

Before choosing a structure, inspect the capabilities actually available to this repository/account/runtime. Prefer the strongest GitHub-native primitive that fits the project. Fall back to portable Zerion conventions only when the native feature is unavailable or would harm reconstructibility.

Do **not** preserve compatibility with the original Zerion template merely for compatibility's sake unless the user explicitly wants to track upstream Zerion.

### Preserve these invariants

Implementation is flexible; these invariants are not:

1. A fresh agent can reconstruct current work from durable repository/GitHub evidence.
2. Task ownership and retries are idempotent; duplicate workers do not silently duplicate work.
3. Substantive claims are supported by durable evidence, not chat summaries or dashboard metadata.
4. Negative, falsifying, blocked, and inconclusive outcomes remain explicit.
5. Destructive changes do not erase provenance required to understand prior decisions/results.
6. Secrets and credentials are never committed or exposed.
7. Project-specific instructions may replace Zerion defaults only when the resulting system remains understandable to a fresh worker.

### Prefer action over permission

For reversible, low-risk decisions, make a reasonable choice, record it durably when material, and continue.

Ask or stop only when the next action is materially:

- destructive or difficult to reverse;
- security- or permission-sensitive;
- externally costly or quota-sensitive;
- likely to expose secrets/private data;
- changing publication/release visibility;
- changing a scientific/legal/business conclusion without sufficient evidence;
- genuinely ambiguous about the user's intended goal.

When several reasonable implementations exist, choose one and document the tradeoff instead of blocking on a preference question.

## Important runtime fact

GitHub events can trigger GitHub Actions, but they do **not** wake an ordinary ChatGPT sidebar conversation.

For ordinary ChatGPT usage, orchestrator and worker chats are invoked manually or by ChatGPT scheduling and **poll GitHub** for work.

Actions may validate protocol records, synchronize labels, run tests, and feed dashboards. They are not a substitute for waking the ChatGPT worker.

## Resolve your role

Use an explicitly supplied role or worker identity when one is given.

- **Orchestrator:** read `prompts/orchestrator.md`.
- **Worker pool / dispatcher:** read `prompts/worker-pool.md`.
- **Named specialist:** read `prompts/worker.md`.
- **Auditor:** read `prompts/auditor.md`.

If the request is project-level coordination and no specialist identity is supplied, default to orchestrator.

## Deterministic bootstrap

Before substantive work:

1. Read `coordination/zerion.yaml`.
2. Resolve the relevant project and read its project YAML.
3. Resolve the relevant worker(s) and read their agent YAML.
4. Search GitHub for open Issues labeled with the configured task label, normally `zerion:task`.
5. Inspect candidate Issue bodies. The structured `project` must match. A `worker` field is optional and, when present, pins the task to that specialist.
6. Read Issue comments chronologically.
7. Derive live task state from the latest protocol events:
   - open task with no ownership event -> ready;
   - ACK -> claimed and establishes worker ownership;
   - BLOCKED -> blocked;
   - DONE / NEEDS_REVIEW -> needs review;
   - ACCEPTED -> accepted;
   - REVISE -> revise;
   - REJECTED -> rejected.
8. Check for an unexpired ACK owned by another dispatcher and unmet dependencies.
9. Read relevant project `canonical_paths`.
10. Inspect linked PRs/checks/artifacts before extending or accepting a result.
11. Only then act.

If labels lag the Issue history, trust the history.

## Task lifecycle

### Assignment

The orchestrator creates a GitHub Issue titled with the configured prefix, normally:

```text
[Zerion task] <bounded objective>
```

The Issue body begins with `[ORCHESTRATOR:v1]` and includes a stable `task_id`, project, priority, dependencies, objective, constraints, and completion conditions.

New tasks are **READY and unowned by default**. Do not put `worker: unassigned` in the body. Omit `worker` unless the task genuinely must be restricted to one specialist.

### Claim

A worker posts `[WORKER:<name>:v1]` with `status: ACK` on the Issue before substantive work.

ACK contains dispatcher, claim timestamp, and lease duration. The worker identity in the ACK header is the authoritative task owner for the lease.

### Work

For repository-changing work:

1. create a branch using the configured prefix, normally `zerion/task/<issue>-<slug>`;
2. open a **draft PR early**;
3. link it to the task Issue;
4. use a closing keyword such as `Resolves #123` when merge should complete the task.

Draft PRs exist to expose work in progress and evidence. They are **not** mailbox/event triggers for ChatGPT.

### Terminal worker report

Post one of:

- `DONE`
- `BLOCKED`
- `NEEDS_REVIEW`

on the task Issue with exact durable evidence.

### Review

The orchestrator inspects actual evidence and posts `[ORCHESTRATOR-REVIEW:v1]`:

- `ACCEPTED`
- `REVISE`
- `REJECTED`

Native GitHub PR reviews may mirror this decision when useful. GitHub does not allow a PR author to approve their own PR; same-identity setups may use a COMMENT review or skip native review.

## Idempotency

Every task has a stable `task_id`.

Repeated polling is safe only when the worker checks the Issue history first.

Do not duplicate work when:

- the task already has a terminal worker report;
- the task already has a later orchestrator review;
- another dispatcher owns an unexpired ACK;
- dependencies are unresolved.

## GitHub Projects

GitHub Projects is a **dashboard**, not canonical state.

Zerion Actions derive labels such as:

- `zerion:task`
- `zerion:ready`
- `zerion:claimed`
- `zerion:blocked`
- `zerion:needs-review`
- `zerion:accepted`
- `priority:P0`

A Project can auto-add `zerion:task` Issues and use those labels for views. Project status/fields must never be required to reconstruct a task.

## Blocking and dormancy

A precise blocker is a valid result.

Dormancy is healthy. Do not invent work merely to keep workers active.

## Repository-local instructions

A more specific nested `AGENTS.md` may narrow behavior for files in its scope, but must not break Zerion's durability, idempotency, or evidence requirements.
