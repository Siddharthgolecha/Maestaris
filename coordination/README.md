# Coordination layer

A fresh AI session starts at root `AGENTS.md`, then reads this directory.

- `zerion.yaml` — global Zerion protocol and GitHub-native defaults.
- `projects/` — project membership and canonical paths.
- `agents/` — specialist identity and dispatcher-pool ownership.
- `state/` — compact current-state indexes.
- GitHub task Issues — chronological control-plane objects.
- linked task PRs/checks/artifacts — substantive work and evidence.
- `templates/` — protocol templates.
- `schema/` — machine-readable configuration schemas.
- `OPERATING_MODEL.md` — runtime-independent rules.

## Preferred transport

Zerion v0.4 uses **GitHub Issues** as the preferred task/control-plane transport.

A task Issue carries:

- the orchestrator assignment in its body;
- worker ACKs and terminal reports in comments;
- orchestrator review events in comments;
- native open/closed state and close reason;
- links to task PRs and other evidence.

This replaces the need for fake long-lived PRs whose only purpose is to hold messages.

## State vs history vs evidence

`coordination/state/<worker>.yaml` is a fast index.

The task Issue is the event history.

Task PRs, commits, CI/checks, proofs, experiments, and artifacts are the evidence.

If the state index conflicts with newer Issue/PR evidence, use the newer evidence and repair the index.

Legacy PR-mailbox fields remain supported for migration but are deprecated.
