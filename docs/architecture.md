# Architecture

Zerion is built around a durable coordination layer in GitHub.

```text
User
 |
 v
Orchestrator
 |
 v
GitHub coordination state
 |
 +--> Worker Pool A --> specialist worker
 |
 +--> Worker Pool B --> specialist worker
 |
 v
task branches / PRs / CI / artifacts
```

The key separation is:

```text
control plane = mailbox PRs
work plane    = task branches + task PRs
```

A mailbox is long-lived and lightweight. A task PR contains the actual code, research, data, proofs, experiments, or writing.

## Reconstruction property

A healthy Zerion project can be reconstructed from repository state without requiring the original conversations. That means current objectives, worker identity, evidence, decisions, blockers, and accepted results all have durable representations.

## Runtime adapters

The protocol is runtime-independent. ChatGPT scheduled tasks, manual conversations, API agents, CI jobs, or other runtimes may act as dispatchers as long as they respect the same task/ACK/result/review semantics.
