# Zerion operating model

## Agent entry point

Root `AGENTS.md` is the normative bootstrap.

```text
AGENTS.md
   |
   v
coordination/zerion.yaml
   |
   +--> projects/<project>.yaml
   +--> agents/<worker>.yaml
   +--> state/<worker>.yaml
                         |
                         v
                  GitHub task Issue
                         |
                         v
                  draft/task PR
                         |
                         v
               checks + durable evidence
```

## Native GitHub mapping

Zerion maps its protocol onto GitHub primitives rather than recreating them.

| Zerion concept | GitHub primitive |
| --- | --- |
| bounded task | Issue |
| task conversation / audit log | Issue comments |
| work in progress | Draft pull request |
| substantive repository result | Pull request / commit |
| verification | Actions / checks / artifacts |
| review UX | Pull request review |
| accepted terminal task | Issue closed as completed |
| rejected task | Issue closed as not planned |
| project/release grouping | optional milestone / GitHub Project |

Labels, milestones, Projects, assignees, and reactions may improve navigation but are not required for protocol correctness.

## Durable layers

### Configuration

`coordination/zerion.yaml`, project files, and agent files define topology and policy.

### Current-state index

`coordination/state/<worker>.yaml` summarizes the latest known task. For native transport, `task.issue` points to the control-plane Issue.

### Control-plane history

The GitHub task Issue body/comments record assignment, claim, terminal report, and orchestrator review.

### Substantive evidence

Linked task PRs, commits, CI/checks, formal verification, experiments, and artifacts establish what actually happened.

## Lifecycle

```text
Issue opened / ASSIGNED
        |
        v
ACK comment / claimed
        |
        v
draft task PR + work
        |
        v
DONE | BLOCKED | NEEDS_REVIEW
        |
        v
orchestrator evidence review
        |
        +--> ACCEPTED -> complete/merge -> close Issue completed
        +--> REVISE   -> keep Issue open
        +--> REJECTED -> close Issue not planned
```

## Native PR reviews

When a task PR exists, the orchestrator may also submit a native GitHub review. This improves GitHub UX but does not replace the Issue-side `[ORCHESTRATOR-REVIEW:v1]` protocol event.

## Idempotency and ACK leases

Every task has a stable `task_id`. ACK comments include a dispatcher, timestamp, and lease duration.

A worker skips a task when a terminal result already exists or another unexpired ACK owns it.

## Legacy transport

`legacy_pull_request_mailbox` remains valid for older repositories. It is a compatibility path, not the v0.4 default.

## Dormancy

Workers may be dormant when no useful work is unblocked. Zerion optimizes critical-path progress, not agent activity.
