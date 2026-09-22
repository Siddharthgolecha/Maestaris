# Zerion agent operating instructions

This repository uses Zerion's repository-first, GitHub-native orchestration protocol.

**Start here.** A fresh AI session must be able to reconstruct its role and current work from GitHub without depending on prior chat history.

## Source-of-truth order

Use durable evidence in this order:

1. this `AGENTS.md` for operating rules;
2. `coordination/zerion.yaml` for global protocol, GitHub settings, pools, defaults, and registered projects;
3. `coordination/projects/<project>.yaml` for project membership and canonical paths;
4. `coordination/agents/<worker>.yaml` for worker identity and pool ownership;
5. `coordination/state/<worker>.yaml` as the fast current-state index;
6. the current Zerion **GitHub task Issue** as the chronological control-plane object;
7. linked task PRs, commits, checks, proofs, experiments, and artifacts as substantive evidence.

The state file is an index, not final evidence. If it disagrees with newer GitHub Issue/PR evidence, use the newer durable evidence and repair the index.

Chat memory and remembered summaries are advisory only.

## Resolve your role

Use an explicitly supplied role or worker identity when one is given.

- **Orchestrator:** read `prompts/orchestrator.md`.
- **Worker pool / dispatcher:** read `prompts/worker-pool.md`.
- **Named specialist:** read `prompts/worker.md`.
- **Auditor:** read `prompts/auditor.md`.

If no worker identity is supplied and the request is project-level coordination, default to the orchestrator role. Do not invent a specialist identity from memory.

## Native control plane

The preferred Zerion control-plane object is a GitHub Issue whose title begins with the configured prefix, normally:

```text
[Zerion task]
```

The Issue body contains the `[ORCHESTRATOR:v1]` assignment. Issue comments contain ACKs, terminal worker reports, and orchestrator review events.

Do not create permanent PRs merely to hold coordination comments.

## Deterministic bootstrap

Before substantive work:

1. Read `coordination/zerion.yaml`.
2. Resolve the relevant project.
3. Read the project registry and relevant worker agent/state files.
4. If `state.task.issue` is set, inspect that Issue directly.
5. Otherwise search open Zerion task Issues for the project/worker and inspect candidate bodies/comments before claiming one.
6. Check the stable `task_id` for:
   - an existing terminal worker result;
   - an existing later orchestrator review;
   - another dispatcher's unexpired ACK lease;
   - unmet dependencies.
7. Read relevant project `canonical_paths`.
8. Inspect linked task PRs, commits, checks, proofs, experiments, or artifacts.
9. Only then act.

## Task lifecycle

### Assignment

The orchestrator creates a task Issue with `[ORCHESTRATOR:v1]`, then updates the worker state index to `assigned` and records the Issue number in `task.issue`.

### Claim

The worker posts a `[WORKER:<name>:v1]` ACK comment on the Issue before substantive work and updates state to `claimed`.

### Work

For repository changes, create a task branch using the configured prefix, normally:

```text
zerion/task/<issue-number>-<short-slug>
```

Open a **draft pull request early** and link it to the Issue. Prefer a GitHub closing keyword such as `Resolves #123` when merge should complete the task.

Substantive work belongs on the task branch/PR, never in coordination-only branches.

### Terminal worker result

Post `DONE`, `BLOCKED`, or `NEEDS_REVIEW` on the task Issue with exact durable evidence. Synchronize the state index.

### Review

The orchestrator inspects actual evidence. When a task PR exists, native GitHub PR reviews are useful:

- `APPROVE` may mirror `ACCEPTED`;
- `REQUEST_CHANGES` may mirror `REVISE`.

The Zerion `[ORCHESTRATOR-REVIEW:v1]` event on the task Issue remains the protocol record so non-PR tasks and PR tasks have one consistent control-plane history.

- `ACCEPTED`: close the Issue as **completed** after accepted work is integrated or otherwise finalized.
- `REVISE`: leave the Issue open.
- `REJECTED`: close the Issue as **not planned** after recording why.

## Idempotency

Every task has a stable `task_id`. Repeated polling or repeated user invocation must be safe.

Never duplicate work when a terminal result or valid ACK already exists.

## GitHub-native features

Use GitHub features when they add durable meaning:

- Issues for task lifecycle and discussion;
- draft PRs for work in progress;
- PR reviews for human/agent review UX;
- Actions/checks for verification;
- closing keywords for Issue↔PR linkage;
- Issue close reasons for terminal lifecycle;
- milestones/Projects/labels as optional views, not required protocol state.

## Legacy PR mailboxes

Projects using `legacy_pull_request_mailbox` remain supported for migration. Follow their existing mailbox PR history and compatibility fields. Do not create new legacy mailboxes unless explicitly required.

## Blocking and dormancy

A precise blocker is a valid result. Dormancy is healthy. Do not invent tasks merely to keep workers active.

## Repository-local instructions

A more specific nested `AGENTS.md` may narrow behavior for files in its scope, but must not break Zerion's durability, idempotency, or evidence requirements.
