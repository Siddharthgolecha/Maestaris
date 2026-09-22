# Zerion

**Agents reason. GitHub remembers.**

Zerion is a GitHub-backed orchestration framework for coordinating persistent specialist AI workers across long-running research, engineering, analysis, and writing projects.

The core idea is simple: conversations and runtimes may be ephemeral, but project state should not be. Zerion keeps coordination state, task ownership, evidence, reviews, and durable outputs in GitHub so a project can be reconstructed even when an individual worker disappears or loses context.

## Architecture

```text
                         GitHub
                  durable coordination state
                            |
               +------------+------------+
               |                         |
               v                         v
          Orchestrator                Worker Pools
               |                         |
               |               +---------+---------+
               |               v         v         v
               |             Worker    Worker    Worker
               |               |         |         |
               +---------------+---------+---------+
                               |
                               v
                     task branches + PRs + CI
```

Zerion separates two planes:

```text
Mailbox PR = control plane
Task PR    = work plane
```

A mailbox carries assignments, claims, terminal reports, and orchestrator reviews. Substantive work belongs on normal task branches and pull requests.

## Core invariant

> If every worker vanished, the project should still be reconstructible from the repository.

Repository state is authoritative. Chat history is useful context, not canonical project state.

## Why Zerion

Zerion is designed for workflows where one AI conversation is not enough: parallel research branches, formal proofs, experiments, software implementation, audits, publication work, migrations, benchmarking, or any project that benefits from specialist workers with durable hand-offs.

It does **not** require a particular AI runtime. The protocol can be used with ordinary ChatGPT conversations, scheduled polling, API agents, CI-driven workers, or another compatible runtime.

## Quick start

1. Use this repository as a template or copy the `coordination/` layer into your project.
2. Copy `coordination/templates/PROJECT_TEMPLATE.yaml` to `coordination/projects/<project>.yaml`.
3. Create one agent file per specialist from `coordination/templates/AGENT_TEMPLATE.yaml`.
4. Create one long-lived draft mailbox PR per active worker.
5. Put only coordination messages in mailbox PRs; put substantive work in task PRs.
6. Give the orchestrator and worker runtime the prompts in `prompts/`.
7. Validate configuration with:

```bash
python scripts/validate_config.py
```

For a guided local bootstrap:

```bash
python scripts/bootstrap_project.py demo-project theory implementation audit
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

Stable task IDs and ACK claims make repeated polling safe and reduce duplicate execution.

## Design principles

- **GitHub wins.** Repository state outranks remembered chat summaries.
- **Bounded work.** Workers execute assigned objectives; the orchestrator chooses the next objective.
- **Durable evidence.** Results should point to commits, PRs, CI, tests, proofs, artifacts, or explicit blockers.
- **Idempotency.** Polling the same mailbox repeatedly must be safe.
- **Dormancy is healthy.** Finished or blocked workers should not consume runtime merely to appear active.
- **Negative results stay negative.** Reviews may reinterpret evidence, but should not silently rewrite failed results into successes.
- **Runtime constraints are adapters, not protocol rules.** Product-specific scheduling limits belong under `docs/runtime/`.

## Status

Zerion is an early reference implementation of a repository-first orchestration pattern. The protocol is intentionally small enough to inspect, fork, and adapt.

## License

MIT. See [LICENSE](LICENSE).
