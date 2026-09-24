# Architecture

Maestaris connects ephemeral reasoning runtimes to durable GitHub coordination.

```text
ChatGPT orchestrator / worker chats
             |
             | manual or scheduled polling
             v
      GitHub task Issues
             |
       protocol comments
             |
             v
        linked task PRs
             |
             v
       checks + artifacts

GitHub events
     |
     +--> Actions validate/sync labels/run CI
     |
     +--> GitHub Projects dashboard
     |
     X--> do not directly wake an ordinary ChatGPT chat
```

## Static configuration

The repository stores only stable topology and instructions:

- `AGENTS.md`
- `coordination/maestaris.yaml`
- project YAML
- agent YAML
- prompts and schemas

## Live state

GitHub is the single live state machine.

The task Issue body defines READY work. It does not create worker ownership. Comments record ACK ownership, terminal worker results, and orchestrator reviews. Linked PRs/checks/artifacts are evidence.

Protocol v4 intentionally has no mutable worker-state YAML and makes the ACK event authoritative for worker ownership.

## Derived views

Actions derive status/priority labels from the Issue event log.

GitHub Projects may auto-add task Issues and expose dashboards. Labels and Project fields are derived and never override Issue history.

## Reconstruction property

If every ChatGPT conversation disappeared, a fresh chat should recover from static repo config plus GitHub Issues/PRs/checks.
