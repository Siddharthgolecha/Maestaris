# Changelog

## 0.3.0

- Make root `AGENTS.md` the normative Zerion entry point for AI agents.
- Add `coordination/zerion.yaml` as the global protocol, pool, defaults, and project registry.
- Add one machine-readable `coordination/state/<worker>.yaml` current-state index per worker.
- Distinguish configuration, current-state index, mailbox event log, and substantive task evidence.
- Extend validation to detect missing state, unregistered projects, invalid pool ownership, and mailbox-reference drift.
- Make `zerion init` register projects globally and create worker state files.
- Make `zerion init` create `AGENTS.md` only when absent and never overwrite existing agent instructions.
- Synchronize mailbox PR numbers across project, agent, and worker-state registries.
- Update orchestrator, worker-pool, specialist, and auditor prompts to use the deterministic `AGENTS.md` bootstrap.

## 0.2.0

- Add installable zerion command-line interface.
- Add zerion init for project and worker registration.
- Add automatic draft mailbox-PR bootstrap through GitHub CLI.
- Add zerion status dashboard with JSON output.
- Add zerion validate as the canonical configuration validator.
- Namespace generated worker IDs by project.
- Make mailbox bootstrap recoverable when a mailbox PR already exists.
- Add CLI tests and CI coverage.
- Preserve the original bootstrap and validation scripts as compatibility wrappers.

## 0.1.0

- Initial repository-first orchestration protocol and public templates.
