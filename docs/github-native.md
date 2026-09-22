# GitHub-native integration

Zerion v0.4 uses GitHub itself as the orchestration substrate.

## Required core primitives

### Issues

A Zerion task is a GitHub Issue.

The Issue body carries the orchestrator assignment. Comments carry ACKs, terminal worker reports, and orchestrator review events.

The Issue number is a native stable reference and is indexed in `coordination/state/<worker>.yaml`.

### Pull requests

Repository-changing work belongs in a task PR. Open it as a draft early so work in progress is visible.

Link the PR to the task Issue. Prefer a closing keyword such as `Resolves #123` when merge should complete the task.

### Actions and checks

CI/checks are first-class durable evidence. Workers should reference exact checks, workflow runs, proof logs, or artifacts in terminal reports.

### Issue close reasons

- ACCEPTED -> close as completed after finalization.
- REVISE -> leave open.
- REJECTED -> close as not planned.

## Native PR reviews

When a task has a PR, an orchestrator can use GitHub's review interface:

- APPROVE can mirror Zerion ACCEPTED.
- REQUEST_CHANGES can mirror Zerion REVISE.

The task Issue still receives the Zerion review event so every task has one consistent control-plane history.

## Optional GitHub features

### Labels

Labels are useful for search and dashboards. Suggested conventions:

- `zerion`
- `zerion:task`
- `zerion:blocked`
- `priority:P0`
- `priority:P1`

Labels are optional because not every connected runtime exposes label administration.

### Milestones

Milestones can map to releases, research phases, or launch gates.

### GitHub Projects

Projects can provide board/table/roadmap views across Issues and PRs. Treat Projects as a view, not the only copy of protocol state.

### Assignees

Use assignees for humans or GitHub identities when meaningful. Zerion worker identity remains in repository configuration because AI workers may not own GitHub accounts.

### Reactions

Reactions may be used as lightweight UX signals but must not replace structured ACK/review records.

### Rulesets and branch protection

Repositories can require CI, reviews, signed commits, or protected branches. Zerion should consume those checks as evidence rather than duplicating governance logic.

## Connected AI runtimes

A key v0.4 dogfood result is that an AI runtime may have a connected GitHub interface while shell-level `git clone` or `gh` access is unavailable.

Therefore:

- the core protocol must be operable through GitHub APIs/connectors;
- shell GitHub CLI is optional;
- default Issue-native operation does not depend on `gh`;
- legacy PR-mailbox bootstrap is the only CLI path that currently requires `gh`.

## Legacy PR mailboxes

v0.3 and earlier may contain permanent draft PR mailboxes. They remain readable and valid under `legacy_pull_request_mailbox` transport.

New projects should use task Issues instead.
