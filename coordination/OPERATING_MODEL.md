# Zerion operating model

## The two worlds

Zerion deliberately separates **reasoning runtime** from **durable coordination**.

```text
ChatGPT
  reasons, plans, writes, reviews
        |
        | polls / writes
        v
GitHub
  Issues, comments, PRs, checks, artifacts
  durable project state
```

An ordinary ChatGPT conversation is not a GitHub webhook target.

GitHub can immediately trigger Actions when an Issue or comment changes, but a normal ChatGPT worker runs only when the user invokes it or its ChatGPT schedule fires.

## Invariants vs implementation freedom

Zerion standardizes **invariants and hand-off semantics**, not the final shape of every repository.

The template is a starting point. An agent operating a derived repository may replace Zerion defaults with stronger project-specific or GitHub-native structures when useful.

For example, a personal repository might use labels plus a Project view, while an organization repository might use native Issue Types and Issue Fields. A research repository may add an evidence ledger and immutable release provenance; a software repository may rely mostly on Issues, PRs, checks, releases, and rulesets.

The agent should discover capabilities, choose the simplest strong native design, and evolve the repository accordingly.

The durable requirements are reconstructibility, idempotency, evidence integrity, provenance, explicit blockers/negative results, and safe handling of secrets/permissions.

## Static repository configuration

`AGENTS.md`, `coordination/zerion.yaml`, project YAML, and agent YAML describe how the system is organized.

They change when the architecture of the project changes, not every time a task changes state.

## Live state

Live state is reconstructed from the GitHub task Issue.

```text
open task Issue = ready
comment ACK = claimed + worker ownership
comment BLOCKED = blocked
comment DONE / NEEDS_REVIEW = needs review
comment ACCEPTED = accepted
comment REVISE = revise
comment REJECTED = rejected
```

There is no second mutable YAML state machine.

## Work plane

Substantive repository work goes into a normal task branch and linked PR.

Open a draft PR early when useful for visibility.

A draft PR is **not** a mailbox and does not wake ChatGPT.

## Mechanical automation

GitHub Actions may:

- validate structured protocol records;
- derive status/priority labels;
- run tests and formal verification;
- produce artifacts;
- support Projects dashboards.

Actions should not make scientific or project-management judgments that belong to an orchestrator unless explicitly designed to do so.

## Projects

GitHub Projects is a derived mission board.

The recommended auto-add filter is:

```text
is:issue label:"zerion:task"
```

Built-in Project automation can mark added items Todo and closed Issues Done.

Zerion status labels provide richer views such as claimed, blocked, and needs review.

## Polling and idempotency

Because worker chats poll, duplicate invocation is normal. Publishing work does not assign it; ownership exists only while a valid ACK lease exists.

Safe polling requires:

- stable task IDs;
- ACK leases;
- checking comments before claiming work;
- checking terminal reports and reviews before acting;
- dependency checks.

## Dormancy

A worker with no useful unblocked task should remain idle/dormant.

Zerion optimizes useful progress, not activity.
