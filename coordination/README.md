# Coordination layer

Zerion stores durable orchestration state under this directory.

- `projects/` registers coordinated projects.
- `agents/` registers specialist workers and dispatcher pools.
- `mailboxes/` contains marker files used by long-lived mailbox branches/PRs.
- `templates/` defines project, agent, assignment, ACK, result, and review formats.
- `schema/` provides machine-readable configuration schemas.
- `OPERATING_MODEL.md` defines runtime-independent rules.

The repository is the source of truth. Chat history may help a worker reason, but it must not be required to reconstruct current project state.
