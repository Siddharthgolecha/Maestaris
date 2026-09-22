# Architecture

Zerion connects ephemeral reasoning runtimes to durable GitHub coordination.

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
- `coordination/zerion.yaml`
- project YAML
- agent YAML
- prompts and schemas

## Live state

GitHub is the single live state machine.

The task Issue body is the assignment. Comments record claims, terminal worker results, and orchestrator reviews. Linked PRs/checks/artifacts are evidence.

Protocol v3 intentionally has no mutable worker-state YAML.

## Derived views

Actions derive status/priority labels from the Issue event log.

GitHub Projects may auto-add task Issues and expose dashboards. Labels and Project fields are derived and never override Issue history.

## Reconstruction property

If every ChatGPT conversation disappeared, a fresh chat should recover from static repo config plus GitHub Issues/PRs/checks.
