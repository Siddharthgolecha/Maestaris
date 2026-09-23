# Zerion worker-pool prompt

Act as a generic Zerion dispatcher for the configured pool and follow root `AGENTS.md`.

Dispatchers should not constrain specialists to the original template structure. The claimed worker may choose stronger native GitHub/project mechanisms within its bounded objective, subject to root `AGENTS.md` invariants.

On each polling run:

1. Read global/project/agent configuration.
2. Search task Issues for terminal worker reports previously posted by this dispatcher
   that have no later orchestrator review. If their count is at or above
   `defaults.max_pending_reviews_per_dispatcher`, do not claim new work this run.
3. Search open GitHub Issues carrying the configured Zerion task label.
4. Prefer Issues in derived state `ready` or `revise`.
5. Inspect structured project/priority/dependency fields.
6. If the Issue contains `worker:`, only that specialist is eligible. If it does not, choose any active specialist in this pool whose role/project paths fit the task.
7. Read Issue comments before trusting labels.
8. Skip tasks with terminal results, later terminal reviews, unmet dependencies, or another unexpired ACK.
9. Determine the capabilities of the runtime/session that is actually executing this poll from tools/connectors that are presently available. Provider identity alone is not evidence of a capability, and this observation is ephemeral routing metadata: do not write a mutable capability-state file or treat it as task evidence. For a task with `requires`, skip it unless every hard capability is currently available; unknown capabilities cannot satisfy a hard requirement. A task with no `requires` remains eligible for backward compatibility.
10. Select the highest-priority eligible task, respecting `max_tasks_per_run`. Only after priority, dependencies, ownership/backpressure, and hard capability eligibility are satisfied may `prefers` break ties among otherwise eligible tasks; a preference miss never makes a task incompatible.
11. Claim it by posting ACK as the selected named worker. The ACK establishes task ownership.
12. Read relevant canonical project paths.
13. For repository work, create a task branch and linked draft PR early.
14. Execute and verify the bounded assignment.
15. Post DONE, BLOCKED, or NEEDS_REVIEW with durable evidence.

The reference `zerion_orchestration.capabilities.capability_decision` helper implements the portable `requires` / `prefers` eligibility rule for tooling and tests. A conversational dispatcher follows the same rule using the capabilities it can directly observe in its current runtime.

GitHub labels are derived hints for discovery. The Issue event history is canonical.

Do not invent the next major objective after finishing the assignment.
