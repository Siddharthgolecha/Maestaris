# Zerion coordination configuration

This directory contains **stable configuration only**.

Live task state belongs in GitHub Issues, comments, PRs, checks, and artifacts.

## Files

- `zerion.yaml` — global protocol, GitHub label policy, pools, and registered projects.
- `projects/` — project membership, canonical paths, and worker lists.
- `agents/` — worker identities, roles, pool ownership, and relevant paths.
- `templates/` — reusable Issue/comment/project/agent templates.
- `schema/` — machine-readable static config schemas.
- `OPERATING_MODEL.md` — the runtime-independent model.

## What is intentionally absent

Protocol v3 has no:

- `coordination/state/`
- permanent mailbox PR registry
- mutable current-task fields in agent YAML

Those concepts duplicated GitHub's own state.

## Live control plane

A Zerion task is a GitHub Issue.

Its body is the assignment. Comments record ACK, worker terminal results, and orchestrator reviews.

GitHub Actions derive labels for search and Projects dashboards, but Issue/comment history remains authoritative.
