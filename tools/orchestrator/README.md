# Maestaris execution router

This directory adapts the Jev/Laya/Needle3 plan into Maestaris without making any model
canonical.

The architecture is:

```text
GitHub canonical task state
        |
        v
deterministic feature extraction + capability floors
        |
        +--> zero-model baseline route
        |
        +--> optional Laya (local) / Jev (hosted) typed System-1 signal
                    |
                    v
             confidence gate
                    |
                    v
bounded Needle3 tool selection (optional)
                    |
                    v
write-capable external executor
        |
        v
System-2 generator only when the selected tier requires it
        |
        v
tests / CI / Lean / domain verifier
        |
        +--> pass: report durable evidence
        +--> fail: deterministic escalation
```

## Why this exists

Scheduled ChatGPT can remain a read-only planner when its connected-app writes are
unavailable.  The external executor is the component that owns write capability.
Jev/Laya decide *which lane* is appropriate; Needle3 decides *which allowlisted tools*
fit a bounded step; neither model is allowed to establish Maestaris ownership, task
state, review state, or scientific truth.

## System-1 contract

Laya is preferred when a local/self-hosted Jev-compatible endpoint is available.
Jev is the hosted fallback.  Both are treated as optional typed-decision providers with
the same three useful primitives:

- `choice`: execution tier
- `noul`: probability that deep reasoning is required
- `score`: overall complexity

The deterministic route always exists.  System-1 may not cross a hard capability floor,
and uncertain downgrades are rejected.

## Needle3 contract

Needle3 receives a bounded tool catalogue.  Its `function_calls` are accepted only when
all selected names are in the deterministic allowlist and confidence clears policy.
The host executes validated calls; Needle3 never receives ambient authority.

## Shadow first

`scripts/route_task_shadow.py` runs with no API keys and performs no GitHub mutations.
It is intended for collecting route telemetry before any real generator is connected.
