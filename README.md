# Zerion

**Agents reason. GitHub remembers.**

Zerion is a lightweight orchestration protocol for running **long-lived projects with ordinary ChatGPT conversations**.

It came from a practical problem: one ChatGPT chat can do serious work, but long research and engineering projects quickly outgrow one conversation. You want an orchestrator, specialist workers, parallel branches, reproducible evidence, hand-offs, and the ability to close a chat and come back later without losing the project.

Zerion makes GitHub the durable coordination layer.

```text
ordinary ChatGPT chats / scheduled chats
                 |
                 | poll
                 v
          GitHub task Issues
                 |
       +---------+---------+
       |                   |
       v                   v
   worker chat         worker chat
       |                   |
       +---------+---------+
                 |
                 v
        task PRs / commits
        checks / artifacts
                 |
                 v
          orchestrator chat
```

The invariant is simple:

> **Any chat may disappear. The project must still be reconstructible from GitHub.**

## What Zerion is meant for

Zerion is useful when you want to treat multiple normal ChatGPT conversations as persistent specialist workers:

- one chat coordinates the project;
- other chats specialize in theory, implementation, experiments, review, writing, or anything else;
- scheduled ChatGPT tasks can periodically poll GitHub when you are away;
- GitHub holds assignments, ACKs, results, evidence, reviews, branches, PRs, and provenance;
- GitHub Projects gives you a human dashboard over the same work.

The chats do the reasoning. GitHub carries the durable state.

## Zerion is a seed, not the final repository architecture

A repository created from Zerion is expected to **evolve away from the template** when the project benefits from it.

The agent should inspect what GitHub capabilities are available and shape the repository accordingly.

For example, it may decide to:

- create a Project and custom views;
- use native Issue Types or Issue Fields in an organization;
- replace free-text dependencies with native sub-issues/dependencies;
- introduce milestones for phases/releases;
- add rulesets and required checks;
- create domain-specific Actions workflows;
- use Releases, artifacts, or attestations for provenance;
- restructure directories and add nested `AGENTS.md` files;
- add an evidence ledger for research, or skip it for a simple software project;
- remove template mechanisms that have become redundant.

The goal is **not** to keep every Zerion repository looking identical.

The goal is to preserve a few invariants:

```text
fresh agent can recover the project
        +
tasks are safely owned/idempotent
        +
evidence is durable and inspectable
        +
negative/blocking results are not erased
        +
provenance survives agent/chat turnover
```

For reversible low-risk choices, the agent should make a reasonable decision and continue rather than repeatedly asking the user for implementation preferences.

Human confirmation is primarily for destructive, irreversible, permission/security-sensitive, externally costly, publication/visibility-changing, or genuinely goal-ambiguous decisions.

## What Zerion is not

Zerion is **not** primarily an API-agent framework.

It does not require:

- spinning up disposable API agents;
- a separate vector database;
- a message broker;
- ChatGPT Work;
- a daemon running on your computer;
- a CLI in order for the AI workers to operate.

There is a small CLI for static setup and validation, but the protocol is designed so an AI agent can operate directly through GitHub.

## The important constraint: GitHub cannot wake an ordinary chat

GitHub Issues, comments, PRs, and other events can trigger **GitHub Actions**.

They cannot directly invoke an ordinary ChatGPT sidebar conversation.

So Zerion deliberately separates two kinds of automation:

```text
GitHub event
    |
    +--> Actions: validate records, sync labels, run tests, update dashboard
    |
    X--> does not wake a normal ChatGPT chat

ChatGPT schedule / user invocation
    |
    +--> worker polls GitHub
         finds eligible task
         ACKs it
         works
         reports result
```

That is why Zerion is built around **safe polling and idempotency**, not fake webhook-driven chat execution.

## The current model

Zerion stores stable configuration in the repository and live orchestration state in GitHub itself.

### Stable configuration

```text
AGENTS.md
coordination/
  zerion.yaml
  projects/
  agents/
prompts/
```

### Live state

```text
GitHub task Issue
  ├── assignment in Issue body
  ├── ACK in comments
  ├── DONE / BLOCKED / NEEDS_REVIEW in comments
  └── ACCEPTED / REVISE / REJECTED in comments

linked task PR
  ├── code / research / writing changes
  ├── commits
  ├── Actions / checks
  └── artifacts
```

There is intentionally **no mutable `coordination/state/` directory**.

Keeping a second state machine in YAML created drift and required commits for every coordination transition. GitHub already has durable Issues, comments, PRs, timestamps, close state, and history, so v0.5 uses them directly.

## A task from start to finish

The orchestrator opens:

```text
[Zerion task] Prove bounded convergence result
```

with a structured body:

```text
[ORCHESTRATOR:v1]
task_id: convergence-theory-0042
project: convergence
priority: P0
depends_on: []
...
```

That Issue is **READY**. No worker owns it yet.

If the work truly requires one specialist, the orchestrator may add `worker: convergence-theory`; otherwise worker pools are free to select an eligible specialist.

A worker pool later polls GitHub, sees the task, verifies there is no valid competing ACK, selects a suitable worker, and comments:

```text
[WORKER:convergence-theory:v1]
task_id: convergence-theory-0042
status: ACK
dispatcher: pool-A
claimed_at: ...
lease_hours: 3
```

That ACK creates the lease and establishes the worker as the current owner.

For repository work it opens a linked draft PR early.

When finished it posts a terminal result to the Issue with exact evidence. The orchestrator later polls, inspects the actual PR/checks/artifacts, and records ACCEPTED, REVISE, or REJECTED.

If the PR contains `Resolves #42`, GitHub can close the task Issue automatically when the PR merges.

## GitHub Actions do the mechanical work

Zerion ships an Issue/comment workflow that:

1. validates structured Zerion task records;
2. reconstructs the task's current protocol state from Issue comments;
3. derives GitHub labels such as `zerion:ready`, `zerion:claimed`, `zerion:blocked`, or `zerion:needs-review`;
4. preserves unrelated user labels.

Those labels are derived metadata. The Issue history remains authoritative.

## GitHub Projects becomes the mission board

GitHub Projects fits Zerion well because it can remain a **view over Issues**, rather than another required database.

Recommended setup:

1. Create a GitHub Project for your Zerion work.
2. Enable its **Auto-add to project** workflow.
3. Point it at your repository with:

```text
is:issue label:"zerion:task"
```

4. Enable the built-in workflow that sets newly added items to **Todo**.
5. Keep the built-in closed-item -> **Done** workflow enabled.
6. Add useful views such as:
   - Blocked: `label:zerion:blocked`
   - Needs review: `label:zerion:needs-review`
   - Ready: `label:zerion:ready`
   - Claimed: `label:zerion:claimed`
   - P0: `label:priority:P0`

The Project is for visibility. A fresh worker must be able to reconstruct work without reading Project-specific fields.

See [GitHub Projects](docs/github-projects.md).

## How ChatGPT workers use Zerion

Every Zerion repository has a root [AGENTS.md](AGENTS.md).

A fresh worker starts there and learns how to:

- resolve its project and role;
- search for open Zerion task Issues;
- derive task state from comments;
- respect ACK leases;
- read canonical project documents;
- inspect PR/check evidence;
- claim work safely;
- report durable results.

This lets you start a completely fresh conversation and say something as small as:

> Use Zerion on this repository. Act as worker pool A.

or:

> Use Zerion and continue orchestration for this project.

The repository should contain enough durable information for the new chat to recover.

## Suggested ChatGPT topology

For a serious project:

```text
Orchestrator chat
    |
    +-- Worker Pool A scheduled chat
    |      +-- theory worker identities
    |      +-- audit worker identities
    |
    +-- Worker Pool B scheduled chat
           +-- implementation identities
           +-- experiment identities
```

A worker identity is not the same thing as a scheduled ChatGPT task.

A small number of generic scheduled worker pools can service many specialist identities defined in GitHub.

When you are actively using ChatGPT, you can run a worker immediately. When you are away, scheduled polling provides eventual progress.

## Repository layout

```text
AGENTS.md
coordination/
  zerion.yaml
  projects/
    example-project.yaml
  agents/
    orchestrator.yaml
    theory-worker.yaml
    implementation-worker.yaml
    audit-worker.yaml
  templates/
  schema/
prompts/
  orchestrator.md
  worker-pool.md
  worker.md
  auditor.md
docs/
.github/
  ISSUE_TEMPLATE/
  workflows/
```

## Quick start

Use the repository as a template or copy Zerion's coordination layer into an existing repository.

Optional local helper:

```bash
python -m pip install -e .

# In a network-restricted environment with dependencies already installed:
# python -m pip install --no-build-isolation -e .

zerion init my-project \
  --workers theory implementation audit \
  --repository owner/repository

zerion validate
```

The CLI writes only stable configuration. It does not maintain live worker state.

Then create your ChatGPT orchestrator / worker chats and point them at the repository.

## Why not store live task state in YAML?

Earlier Zerion versions maintained a state index in the repository.

Dogfooding showed that this created the wrong abstraction:

- ACKing a task should not require a code commit;
- Issue comments already have durable ordering and timestamps;
- a YAML cache could disagree with GitHub;
- parallel workers could contend on state files;
- AI runtimes with GitHub connector access may not have shell GitHub access.

Zerion therefore makes GitHub the single live state machine. Protocol v4 additionally separates **work availability** from **worker ownership**: an open task is READY; an ACK creates the active owner lease.

## Design principles

- **Chats are workers. GitHub is memory.**
- **AGENTS.md is the bootstrap.**
- **Issues are tasks and control-plane histories.**
- **PRs are work, not mailboxes.**
- **Actions react to GitHub; ChatGPT workers poll GitHub.**
- **Projects is a dashboard, not canonical state.**
- **READY work is unowned until an ACK claims it.**
- **Stable task IDs make retries safe.**
- **Evidence beats summaries.**
- **Negative results stay negative.**
- **Dormancy is healthy.**
- **No worker is required for project reconstruction.**
- **The template may evolve. Preserve invariants, not template shape.**
- **Prefer sensible reversible action over unnecessary permission checks.**

## Documentation

- [Architecture](docs/architecture.md)
- [Protocol](docs/protocol.md)
- [GitHub-native integration](docs/github-native.md)
- [GitHub Projects](docs/github-projects.md)
- [Multi-model GitHub runtimes](docs/runtime/multi-model-github.md)
- [ChatGPT scheduled runtime](docs/runtime/chatgpt-scheduled.md)
- [Manual chat runtime](docs/runtime/manual-chat.md)
- [Quick start](docs/quickstart.md)
- [Failure recovery](docs/failure-recovery.md)
- [Scaling](docs/scaling.md)
- [Migrating to v0.5](docs/migration-v0.5.md)
- [Migrating to v0.6 / protocol v4](docs/migration-v0.6.md)

## License

MIT. See [LICENSE](LICENSE).
