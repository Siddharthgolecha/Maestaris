# Coordination layer

Zerion stores durable orchestration state under this directory.

A fresh AI session should begin at the repository root `AGENTS.md`, then read this coordination layer in a deterministic order.

- `zerion.yaml` is the global registry: protocol version, canonical branch, orchestrator, dispatcher pools, defaults, and registered projects.
- `projects/` registers coordinated projects and their canonical paths.
- `agents/` registers specialist workers, roles, and dispatcher-pool ownership.
- `state/` is the machine-readable **current-state index** for each worker.
- mailbox PRs are the chronological **control-plane event log**.
- task PRs, commits, CI, proofs, experiments, and artifacts are the **substantive evidence**.
- `templates/` defines project, agent, state, assignment, ACK, result, and review formats.
- `schema/` provides machine-readable configuration schemas.
- `OPERATING_MODEL.md` defines runtime-independent rules.

The state index is intentionally redundant with some mailbox metadata. This redundancy is checked by `zerion validate` so drift becomes visible rather than silently changing project truth.

Repository and GitHub evidence are authoritative. Chat history may help an agent reason, but it must not be required to reconstruct current project state.
