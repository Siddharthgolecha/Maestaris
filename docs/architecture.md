# Architecture

Zerion is a repository-first protocol with GitHub-native control and work planes.

```text
User / scheduler / AI runtime
            |
            v
        AGENTS.md
            |
            v
 coordination/zerion.yaml
            |
    +-------+-------+
    |       |       |
 project  agent   state index
            |
            v
      GitHub task Issue
            |
     control-plane events
            |
            v
       linked draft PR
            |
            v
     checks / artifacts
```

## Durable layers

### Configuration

The global registry plus project and agent files define identity, pools, policy, and canonical paths.

### Current-state index

`coordination/state/<worker>.yaml` points to the latest known task Issue and task PR. It exists for efficient agent startup.

### Control-plane history

The task Issue body/comments hold assignment, claim, terminal worker result, and orchestrator review.

### Work plane

Task branches and PRs contain substantive changes. Draft PRs make in-progress work visible.

### Evidence

Commits, Actions/checks, proof output, experimental artifacts, and other durable outputs establish what happened.

## Legacy transport

Older Zerion repositories may use long-lived draft PR mailboxes. v0.4 validates them as a compatibility transport but does not recommend them for new projects.
