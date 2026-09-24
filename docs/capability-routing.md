# Capability-aware routing

Maestaris tasks may optionally declare hard capabilities and soft preferences without tying work to a model provider.

```yaml
requires:
  - lean
  - github-write
prefers:
  - long-reasoning
```

`requires` is an eligibility constraint. A dispatcher must not ACK a task unless its current runtime can provide every required capability. If the runtime cannot determine its capabilities, a task with non-empty `requires` is not eligible for that dispatcher. Legacy tasks that omit `requires` remain eligible.

`prefers` is advisory. It may break ties among otherwise eligible work, but a preference miss never makes a dispatcher incompatible and never overrides priority, dependencies, an active ACK lease, or review backpressure.

Capabilities describe observable runtime/tooling facts, not model-quality rankings. Useful names include `python`, `web`, `github-read`, `github-write`, `schedule-management`, `lean`, and `qiskit`. Projects may define additional names such as a pinned compiler/toolchain or access to a domain-specific verifier.

A dispatcher should determine capabilities from the runtime it is actually executing in. Provider identity alone is not proof of a capability: for example, two sessions from the same provider may expose different connectors or local tools. Capability observations are routing metadata, not canonical task state and not evidence that a task result is correct.

Selection order remains:

1. reconstruct canonical Issue state and dependencies;
2. enforce worker pinning, ACK leases, and review backpressure;
3. reject tasks whose hard capabilities are not satisfied;
4. preserve explicit priority ordering;
5. use soft preferences only among otherwise eligible choices.

Examples:

```yaml
# Formal proof
requires: [lean, github-write]
prefers: [long-reasoning]

# Qiskit experiment
requires: [python, qiskit]
prefers: [github-write]

# Web-only research
requires: [web]

# Runtime topology maintenance
requires: [schedule-management, github-write]
```

The reference helper in `maestaris_orchestration.capabilities` implements the portable matching rule. It intentionally parses only the bounded string-list fields required by this contract rather than treating arbitrary Issue Markdown as trusted YAML.
