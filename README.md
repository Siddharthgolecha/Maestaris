# Zerion

**Agents reason. GitHub remembers.**

Zerion is a GitHub-backed orchestration protocol for coordinating persistent specialist AI workers across long-running research, engineering, analysis, and writing projects.

The primary interface is **agent-native**: a fresh AI session starts from the repository's `AGENTS.md`, reconstructs current operating state from GitHub, and continues without depending on prior chat history.

## Core invariant

> If every worker vanished, the project should still be reconstructible from the repository.

Chat memory is useful context, not canonical project state.

## Agent-native architecture

```text
                         AGENTS.md
                             |
                             v
                 coordination/zerion.yaml
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
         projects/        agents/         state/
              |              |              |
              +--------------+--------------+
                             |
                             v
                        mailbox PR
                    control-plane log
                             |
                             v
                     task PR / commits
                     CI / proofs / data
                     substantive evidence
```

Zerion separates two planes:

```text
Mailbox PR = control plane
Task PR    = work plane
```

The worker state file is a fast machine-readable index. The mailbox is the chronological control-plane history. Task PRs and artifacts are the substantive evidence.

## Why Zerion

Zerion is designed for workflows where one AI conversation is not enough: parallel research branches, formal proofs, experiments, software implementation, audits, publication work, migrations, benchmarking, or any project that benefits from specialist workers with durable hand-offs.

It does **not** require a particular AI runtime. Ordinary ChatGPT conversations, scheduled tasks, API agents, coding agents, CI-driven workers, or other runtimes can follow the same repository protocol.

## For AI agents

Read `AGENTS.md` first.

It defines a deterministic bootstrap:

1. read the global Zerion registry;
2. resolve the project and role;
3. read project, agent, and current-state files;
4. inspect the mailbox PR;
5. check task idempotency and ACK ownership;
6. read canonical project state;
7. inspect actual task evidence;
8. only then act.

This is the primary Zerion interface.

## Optional CLI

The CLI exists for human setup, validation, and maintenance; it is not required for an AI worker to operate Zerion.

Install locally:

```bash
python -m pip install -e .
```

Initialize a project:

```bash
zerion init demo-project \
  --workers theory implementation audit \
  --repository owner/repository
```

This automatically creates:

- a project registry entry;
- namespaced agent entries;
- one machine-readable state file per worker;
- registration in `coordination/zerion.yaml`.

With authenticated GitHub CLI, Zerion can also create long-lived draft mailbox PRs and record their PR numbers:

```bash
zerion init demo-project \
  --workers theory implementation audit \
  --repository owner/repository \
  --mailboxes \
  --commit
```

Inspect or validate:

```bash
zerion status
zerion validate
```

## Message lifecycle

```text
ORCHESTRATOR ASSIGNED
        |
        v
WORKER ACK
        |
        v
worker executes bounded task
        |
        v
DONE / BLOCKED / NEEDS_REVIEW
        |
        v
ORCHESTRATOR REVIEW
        |
        +--> ACCEPTED
        +--> REVISE
        +--> REJECTED
```

The mailbox records this history; `coordination/state/<worker>.yaml` summarizes the latest known state for efficient agent startup.

## Design principles

- **AGENTS.md is the bootstrap.** A fresh AI session should know how to enter the system.
- **GitHub wins.** Durable repository and GitHub evidence outrank remembered chat summaries.
- **State is indexed, evidence is inspected.** Fast state files never replace mailbox/task verification.
- **Bounded work.** Workers execute assigned objectives; the orchestrator chooses the next objective.
- **Durable evidence.** Results point to commits, PRs, CI, tests, proofs, artifacts, or explicit blockers.
- **Idempotency.** Repeated polling or invocation must be safe.
- **Dormancy is healthy.** Finished or blocked workers should not consume runtime merely to appear active.
- **Negative results stay negative.** Reviews may contextualize evidence but must not silently rewrite failures into successes.
- **Runtime constraints are adapters, not protocol rules.**

## Documentation

- [Architecture](docs/architecture.md)
- [Protocol](docs/protocol.md)
- [Quick start](docs/quickstart.md)
- [CLI](docs/cli.md)
- [Failure recovery](docs/failure-recovery.md)
- [Scaling](docs/scaling.md)

## Status

Zerion is an early reference implementation of a repository-first, agent-native orchestration pattern.

## License

MIT. See [LICENSE](LICENSE).
