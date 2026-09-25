# Scheduled-runtime conformance

Maestaris trusts durable behavior, not a provider's self-description. The conformance
suite in `maestaris_orchestration.conformance` evaluates recorded or simulated
observations for worker, orchestrator, and runtime-recovery invariants.

A complete result covers ACK arbitration, dependencies, hard capability gating,
admission/fair-share decisions, review backpressure, REVISE resumption, lease expiry,
duplicate prevention, review-claim arbitration/recovery, evidence inspection, the
acceptance-before-merge rule, and recovery from provider refusal, tool authorization
failure, outage, and malformed responses.

Results are deliberately **advisory**. They cannot establish ownership, acceptance,
review state, or any other canonical task state; GitHub Issue history remains
authoritative. Missing required observations fail closed.

## Applying it

Adapters for ChatGPT, Gemini Spark, Claude/Actions, or future runtimes should convert
durable transcript facts into `Observation` records and call `evaluate`. This path
requires no provider API key and is suitable for saved/simulated histories. Keep raw
transcript references in the observation evidence rather than trusting a runtime's
claim that it is compliant.

`compliant_recorded_scenario()` is a deterministic baseline that simulation #41 can
reuse. `gemini_backpressure_violation_scenario()` preserves the live regression where
a worker claimed new work after exhausting pending-review capacity; it must fail the
`review-backpressure` invariant. Runtime-failure fixtures verify recovery through a
separately compatible runtime without changing the underlying task conclusion.
