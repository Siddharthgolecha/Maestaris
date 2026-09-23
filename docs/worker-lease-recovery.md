# Worker lease renewal and recovery

Worker ownership remains reconstructible from GitHub Issue history. An ACK starts a bounded lease. If a worker crashes after ACK and posts no terminal report, the lease eventually expires and the task becomes eligible for another compatible dispatcher; a crash before ACK consumes no retry.

A continuing owner may post a renewal using the same worker/dispatcher identity and a fresh `claimed_at`/`lease_hours`. Renewals extend ownership only when they move the authoritative interval forward; stale, future-dated, malformed, or shorter renewals do not rewind or steal a lease. A competing ACK that begins before the current lease expires cannot steal it.

Retry accounting counts distinct valid ACK attempts, not renewal records or duplicate polling. `defaults.worker_retry_budget` controls the default budget. Once the budget is exhausted with no active lease, the derived recovery state is `quarantine`: a holding state requiring orchestrator inspection. Quarantine never deletes or rewrites prior ACKs, failures, BLOCKED reports, or negative evidence.

The pure projection lives in `zerion_orchestration.worker_leases`. `active_worker_lease()` returns the current valid owner, `retry_count()` reconstructs attempts, and `recovery_state()` yields `claimed`, `ready`, or `quarantine`. Audit/orchestrator integrations should use these projections rather than mutating historical comments.

Example renewal record:

```text
[WORKER:implementation-worker:v1]
task_id: example
status: RENEW
dispatcher: chatgpt-pool-b
runtime: chatgpt
instance: Zerion Worker Pool B
claimed_at: 2026-09-23T15:00:00Z
lease_hours: 3
attempt: 1
```

`RENEW` is lease metadata, not a new execution attempt and not a terminal result. Implementations that have not yet wired renewal validation into their protocol-comment validator should continue to use a fresh ACK from the same logical owner for compatibility; the lease projection treats same-owner ACKs monotonically and retry accounting deduplicates identical ACK delivery. Full protocol-validator integration is required before `RENEW` should be emitted by generic workers.
