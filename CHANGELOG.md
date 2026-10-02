# Changelog

## 0.7.0 — 2026-10-02

Maestaris returns to its original purpose: using ordinary AI chat conversations to produce real GitHub commits and pull requests.

- Make the default architecture explicitly chat-first: Worker A, Worker B, one orchestrator chat, and GitHub as durable shared memory.
- Use bounded GitHub Issues, lightweight claim comments, normal task branches, commits, pull requests, CI, and normal GitHub review as the complete core workflow.
- Make scheduled/background execution optional convenience rather than part of the correctness model.
- Remove admission/fair-share scheduling, dispatcher backpressure, review leases, protocol relay, capability/execution routing, runtime conformance and simulation, checkpoints, provenance/telemetry machinery, scheduler bootstrap logic, and the Python orchestration package/test matrix.
- Replace the larger protocol with concise `AGENTS.md`, configuration, quick-start, protocol, and architecture guidance.
- Keep the safety boundary simple: avoid duplicate worker effort, preserve tests/review, and never commit secrets.

### Migration from 0.6.x

v0.7.0 is intentionally a simplification release. Consumers should stop depending on the removed `maestaris_orchestration` Python package, CLI, protocol-relay workflows, runtime executors, scheduler bootstrap, leases, or duplicate Maestaris state machines. The supported path is:

`Issue -> worker chat -> branch/commit/PR -> orchestrator review -> merge`

Earlier implementation history remains available through Git history.
