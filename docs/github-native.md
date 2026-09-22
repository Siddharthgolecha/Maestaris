# GitHub-native integration

Zerion uses GitHub as the live coordination substrate. The design rule is **native first, portable fallback second**: use a first-class GitHub primitive when it is available to every relevant runtime, but keep enough portable Issue protocol data to reconstruct work when a connector does not expose that primitive.

## Core vs optional primitives

| Concern | Preferred GitHub primitive | Zerion requirement |
| --- | --- | --- |
| bounded work | Issue | core |
| queue/ownership state | Issue history + ACK lease | core |
| implementation/evidence | linked PR, commits, checks, artifacts | core for repository-changing work |
| discovery | derived labels and GitHub search | core |
| decomposition | native sub-issues | optional; structured task IDs remain portable |
| ordering/blocking | native issue dependencies | optional; `depends_on` remains the portable fallback |
| release/phase grouping | milestones | optional and recommended |
| human dashboard | Projects | optional derived view |
| structured dashboard metadata | Issue Fields where supported, otherwise Project fields | optional; never required for reconstruction |
| verification | Actions/check runs | optional mechanism, preferred when local verification is unavailable |
| governance | repository rulesets / required checks | optional policy layer |
| publication/provenance | Releases, release assets, artifact attestations | optional, preferred over duplicating GitHub metadata in Markdown |

## Issues

Each bounded task is an Issue.

The body defines the bounded task. A newly opened task is READY and unowned by default. Comments form the event log; the first valid ACK establishes the active worker lease. A `worker:` field is therefore a constraint/pin, not the ownership record.

Do not duplicate information GitHub already records reliably. In particular, linked PRs, review decisions, checks, commit SHAs, close state, and timestamps should normally be read from GitHub rather than copied into a mutable status ledger.

## Native hierarchy and dependencies

When the connected runtime exposes them reliably, prefer native sub-issues for task decomposition and native blocked-by/blocking relationships for scheduling. They give humans and GitHub tooling a navigable graph without inventing another graph store.

Zerion must still tolerate runtimes that cannot read or mutate these APIs. Stable `task_id` values and `depends_on` metadata are the portable fallback. Native relationships mirror that portable intent; they do not replace it as the reconstructible protocol.

### Mapping

| Zerion intent | Portable representation | Native mirror when available |
| --- | --- | --- |
| stable identity | `task_id: child-001` | Issue number/URL is navigation only |
| decomposition | child task has its own `task_id`; parent identity remains durable in task text when needed | parent/sub-issue relationship |
| prerequisite | `depends_on: [parent-001]` | child is blocked by the prerequisite Issue; prerequisite blocks child |
| no prerequisite | `depends_on: []` | no blocked-by edge |

A dependency edge is directional: if task B lists task A in `depends_on`, B is **blocked by A**, and A is **blocking B**. The dependency is satisfied only when the prerequisite has a terminal accepted outcome according to the Zerion Issue history; merely closing the GitHub Issue is not enough if the protocol history says REJECTED, REVISE, or otherwise unresolved.

Sub-issues express decomposition, not automatically execution ordering. A child being a sub-issue of a parent does not imply that either blocks the other. Add a dependency only when there is a real prerequisite.

### Capability detection

Treat hierarchy and dependency support as separate capabilities. A runtime may be able to read native relationships without being able to create or remove them.

Before relying on a native relationship, verify that the current connector/API can read the relevant endpoint. Before mutating one, verify that the runtime exposes a supported write operation. Do not infer write support from successful reads.

The GitHub connector used by Zerion's ordinary chat runtime can currently read repository issue `sub_issues` and `dependencies/blocked_by` endpoints. Its exposed mutation surface does not provide corresponding relationship writes. In that environment workers therefore **read native relationships as validation/navigation evidence but keep `depends_on` as the scheduling source available to all workers**. A different runtime with reliable relationship-write support may mirror the portable metadata natively.

### Reconciliation and fallback

For every candidate task:

1. parse `task_id` and `depends_on` from the Issue assignment;
2. resolve each portable dependency to its Zerion task Issue;
3. if native dependency reads are available, inspect the native blocked-by edges;
4. if both representations agree, use the graph normally;
5. if portable metadata contains an unresolved prerequisite but the native edge is missing, **remain blocked according to portable metadata** and optionally repair the native mirror when write support exists;
6. if a native blocked-by edge exists that portable metadata does not declare, do not silently claim the task—report/reconcile the unexpected edge first;
7. if native APIs are unavailable, continue entirely from portable metadata.

This asymmetry is intentional: an optional native mirror must never make a portable dependency disappear. It also prevents a runtime with richer GitHub access from creating scheduling state that ordinary workers cannot reconstruct.

Migration is therefore additive. Existing `depends_on` arrays remain valid. A capable migration tool/runtime may create equivalent native edges and sub-issue links, but it must not delete the portable identifiers merely because the mirror was created.

## Milestones

Use milestones for releases, research phases, or other bounded collections of Issues. A milestone answers “what belongs to this phase/release?”; it should not be replaced by an epic Issue whose only purpose is grouping.

Sub-issues remain appropriate when the children are actual decomposition of one parent outcome.

## Pull requests

Repository-changing work belongs in a linked task PR. Opening it as a draft early exposes work in progress.

A PR is work-plane evidence, not a mailbox and not a mechanism for waking ChatGPT. Prefer native PR links, reviews, checks, commits, and merge state over copying those values into Issue metadata.

## Actions and checks

GitHub Actions react immediately to repository events and are ideal for mechanical work:

- protocol validation;
- label synchronization;
- tests/checks;
- artifact generation;
- reusable validation workflows for consumer repositories.

Actions do not directly invoke an ordinary ChatGPT sidebar conversation.

When a worker runtime cannot reproduce a required toolchain locally, a durable GitHub check or workflow run is preferable to claiming that verification was performed locally. The worker should report exactly which environment produced the evidence.

## Labels and search

Zerion derives managed labels from the Issue history. By default:

- `zerion:task`
- `zerion:ready`
- `zerion:claimed`
- `zerion:blocked`
- `zerion:needs-review`
- `zerion:accepted`
- `zerion:revise`
- `zerion:rejected`
- `priority:<value>`

Unmanaged user labels are preserved. Labels are discovery/indexing hints, not stronger evidence than the Issue event history. Worker pools should use GitHub search to find eligible READY work and then inspect the Issue before claiming it.

## Native PR reviews

APPROVE may mirror ACCEPTED and REQUEST_CHANGES may mirror REVISE.

GitHub prevents a PR author from approving their own PR. Same-identity setups should use COMMENT or skip native review; the Issue-side Zerion review remains canonical.

## Projects and structured fields

Projects is an optional derived dashboard. See `docs/github-projects.md`.

For organization-owned repositories where GitHub Issue Fields are available, fields can hold structured Priority, Project, Evidence Status, Review State, or dates. For personal repositories, Project fields can provide a similar dashboard. Neither is required for the core protocol because not every account or connector exposes them.

## Rulesets and repository policy

Rulesets and required checks are the native place for enforceable repository governance. Zerion should document or recommend them rather than emulate branch protection in protocol comments.

Rulesets are repository policy, not task state. Their availability and enforcement depend on repository/account capabilities, so the template must not assume that every derived repository can create the same ruleset.

## Releases and provenance

For frozen publication/release outputs, prefer GitHub-native provenance where practical:

- commit/tag SHA for source identity;
- GitHub Releases for the publication boundary;
- release assets or Actions artifacts for produced bundles;
- artifact attestations for build provenance;
- checks/workflow runs for validation evidence.

Repository manifests remain useful only for semantics GitHub cannot express well, such as domain assumptions, raw-vs-derived distinctions, blind-analysis constraints, recovery notes, or detailed limitations.

## Connected AI runtimes

An AI runtime may have GitHub connector/API access while its shell cannot reach github.com. Zerion therefore makes shell `git`/`gh` optional for agent operation and capability-detects native features rather than assuming one access path.
