# Zerion

**Agents reason. GitHub remembers.**

Zerion is an agent-native orchestration protocol for coordinating persistent AI workers through ordinary GitHub primitives.

A fresh AI session starts at `AGENTS.md`, reconstructs its role and current work from GitHub, and continues without depending on prior chat history.

## GitHub-native model

```text
AGENTS.md
    |
    v
coordination/zerion.yaml
    |
    +--> project / agent / state indexes
    |
    v
GitHub task Issue
    |
    +--> ACK / worker result / orchestrator review comments
    |
    v
linked draft task PR
    |
    v
commits + Actions/checks + artifacts
```

The preferred mapping is:

| Zerion | GitHub |
| --- | --- |
| bounded task | Issue |
| control-plane history | Issue comments |
| work in progress | draft PR |
| substantive result | PR / commit |
| verification | Actions / checks / artifacts |
| review UX | native PR review |
| accepted task | Issue closed as completed |
| rejected task | Issue closed as not planned |

The current-state YAML is only a fast index. The Issue/PR/check history is the durable evidence.

## Core invariant

> If every worker disappeared, the project should still be reconstructible from GitHub.

## For AI agents

Read `AGENTS.md` first.

The default lifecycle is:

1. discover or create a structured `[Zerion task]` Issue;
2. ACK in an Issue comment;
3. open a linked draft PR early for repository work;
4. execute and verify the bounded objective;
5. report DONE / BLOCKED / NEEDS_REVIEW in the Issue;
6. inspect durable evidence;
7. record the Zerion review event;
8. close the Issue with GitHub's appropriate close reason when terminal.

No CLI is required for agent operation.

## Optional CLI

The CLI is for setup, local validation, and maintenance:

```bash
python -m pip install -e .

# If build isolation cannot reach package indexes:
# python -m pip install --no-build-isolation -e .

zerion init demo-project \
  --workers theory implementation audit \
  --repository owner/repository

zerion validate
zerion status
```

New projects use GitHub Issues by default. `--mailboxes` remains only for deprecated PR-mailbox compatibility and requires shell-level GitHub CLI access.

## GitHub-native extras

Labels, milestones, assignees, GitHub Projects, reactions, and branch rules can improve navigation and governance, but Zerion does not require them for correctness. This keeps the protocol usable from connected AI runtimes even when some GitHub surfaces are unavailable.

See [GitHub-native integration](docs/github-native.md).

## Design principles

- **AGENTS.md is the bootstrap.**
- **GitHub is durable state.**
- **Issues are task/control-plane objects.**
- **Draft PRs expose work in progress.**
- **Checks and artifacts are evidence.**
- **State YAML is an index, not truth by itself.**
- **Retries must be idempotent.**
- **Negative and inconclusive results remain preserved.**
- **Dormancy is healthy.**
- **Runtime-specific limits stay outside the core protocol.**

## Documentation

- [Architecture](docs/architecture.md)
- [Protocol](docs/protocol.md)
- [GitHub-native integration](docs/github-native.md)
- [Quick start](docs/quickstart.md)
- [CLI](docs/cli.md)
- [Failure recovery](docs/failure-recovery.md)
- [Scaling](docs/scaling.md)

## License

MIT. See [LICENSE](LICENSE).
