# Multi-AI orchestration

Maestaris does not require every scheduled worker to run on the same model provider.

A ChatGPT schedule, Gemini Spark schedule, Claude/Actions worker, local CLI agent, or
future runtime can all compete safely for the same READY queue as long as they follow
the same ACK lease protocol.

## The shared-queue model

```text
GitHub READY queue
      |
      +--> ChatGPT scheduled dispatcher
      |
      +--> Gemini Spark scheduled dispatcher
      |
      +--> Claude / Actions dispatcher
      |
      +--> local/API dispatcher
               |
               v
        first valid ACK wins
```

Provider identity is not canonical task state. The Issue history is.

Each scheduler instance should use a unique `dispatcher:` value. It is also useful to
include optional runtime metadata:

```text
[WORKER:implementation-worker:v1]
task_id: example-0042
status: ACK
dispatcher: gemini-spark-pool-b
runtime: gemini-spark
instance: personal-spark-schedule-b
claimed_at: 2026-09-22T19:30:00Z
lease_hours: 3
```

Existing Maestaris workers that omit `runtime` or `instance` remain valid.

## Collision handling

Before ACKing, every dispatcher must reread the Issue comments.

If another dispatcher has an unexpired ACK, skip the task.

The runtime does not matter:

```text
ChatGPT ACK first  -> Gemini skips
Gemini ACK first   -> ChatGPT skips
Claude ACK first   -> both skip
```

Stable task IDs and leases make multi-provider polling safe.

## Scheduling strategy

Two useful strategies are:

### Shared pools

ChatGPT and Gemini both service Pool A/B. This maximizes throughput and failover.

Stagger schedule times to reduce wasted races, for example:

```text
ChatGPT Pool A   :22
Gemini Pool A    :37
ChatGPT Pool B   :52
Gemini Pool B    :07
```

### Capability-specialized dispatchers

Let different runtimes prefer different work:

- ChatGPT: research/orchestration/review;
- Gemini Spark: UI-connected scheduled tasks;
- Claude Code/Actions: repository-heavy event-driven work;
- local/API agents: toolchain-specific tasks.

The Issue may pin a worker only when required. Otherwise dispatcher selection remains
dynamic.

## One-orchestrator bootstrap

The preferred provider setup is **one orchestrator first**, not manual creation of
every worker schedule.

There is exactly one unavoidable provider-side bootstrap action: the user creates or
invokes that orchestrator in ChatGPT, Gemini Spark, Claude, or another runtime. GitHub
cannot create a provider-owned chat/task on its own. After that, the repository should
carry everything needed for the orchestrator to configure the rest.

When `scheduler_bootstrap.enabled` is true, an orchestrator should reconcile **three
layers**: one recurring orchestrator schedule, the configured worker-pool dispatcher
schedules, and one persistent review-drain schedule. A provider that supports schedule
management should create missing schedules, update drifted ones, and avoid duplicates
by using stable instance names. A one-shot bootstrap chat is not enough for unattended
operation because execution and review both need persistent loops.

For the default Maestaris topology:

```text
pools: A, B

Gemini Spark bootstrap session
  -> ensures maestaris-gemini-spark-orchestrator exists and recurs
  -> ensures maestaris-gemini-spark-pool-A exists
  -> ensures maestaris-gemini-spark-pool-B exists
  -> ensures maestaris-gemini-spark-review exists
  -> keeps all four hourly and staggered
```

This makes the user-facing bootstrap:

```text
connect GitHub to provider
      |
user creates ONE provider orchestrator
      |
prompt: "Use Maestaris on OWNER/REPO as orchestrator."
      |
      +--> orchestrator reads AGENTS.md + coordination/maestaris.yaml
      +--> discovers pools / cadence / identities / protocol
      +--> creates or reconciles a recurring orchestrator schedule
      +--> creates or reconciles provider-owned worker schedules
      +--> creates or reconciles a persistent review-drain schedule
      +--> workers service READY queue; reviewer drains terminal results
```

GitHub is the bootstrap memory and desired-state source; the provider remains the
owner of its actual scheduled tasks.

Live schedules are intentionally not copied into GitHub as canonical state. They are
provider runtime objects. GitHub records the desired topology and all durable work.

### Gemini Spark orchestrator bootstrap prompt

Start one Gemini Spark task with instructions like:

```text
Act as the Maestaris orchestrator for OWNER/REPO.

Read AGENTS.md and coordination/maestaris.yaml first. Treat GitHub as the durable system
of record.

On startup, inspect scheduler_bootstrap and the configured pools. Because Gemini Spark
supports conversational schedule management, ensure there is one recurring Spark
orchestrator schedule, one recurring worker-dispatcher schedule for every configured
Maestaris pool, and one recurring review-drain schedule. If this task is already the
recurring orchestrator schedule, do not create a duplicate.

Use stable schedule/instance names from the configured templates. For the default
configuration create/reconcile:
- maestaris-gemini-spark-orchestrator, hourly, using the configured orchestrator minute;
- maestaris-gemini-spark-pool-A, hourly, using the configured Pool A minute hint;
- maestaris-gemini-spark-pool-B, hourly, using the configured Pool B minute hint;
- maestaris-gemini-spark-review, hourly, using the configured review minute.

Do not create duplicates. If a matching schedule exists, inspect and update it instead.
Each generated worker schedule must read AGENTS.md on every run, poll the shared READY
queue, respect dependencies and unexpired ACK leases, claim no more than its configured
`max_tasks_per_run` productive allowance, and use its stable
dispatcher/runtime/instance identity in the ACK. The reviewer remains enabled and drains
independent terminal results rather than waiting for a per-review schedule pin.

After reconciling execution and review schedules, perform the normal Maestaris
orchestrator duties: maintain dependency/priority state, route around runtime capability
gaps, and create bounded READY work only when useful. The persistent reviewer inspects
actual PR/check/artifact evidence and posts ACCEPTED/REVISE/REJECTED or merges when
warranted.

Reconcile worker and review schedules again on future orchestrator runs so missing,
paused, or drifted recurring roles are repaired when safe.
```

Gemini Spark supports creating and editing schedules conversationally, so the
orchestrator can perform this bootstrap from the task thread. If provider capabilities
change, capability detection wins over these instructions.

## Gemini Spark scheduled worker prompt

Normally the Gemini orchestrator creates these schedules. The generated Pool A/B
schedule should use a prompt equivalent to:

```text
Act as Maestaris worker dispatcher Pool A for OWNER/REPO.

Read AGENTS.md and the current Maestaris configuration first. Search open maestaris:task
Issues and select the highest-priority eligible READY task for this pool. Read the
Issue history before claiming anything. If another dispatcher owns an unexpired ACK,
skip it.

When claiming a task, post a normal Maestaris ACK and identify this scheduler as:

dispatcher: gemini-spark-pool-a
runtime: gemini-spark
instance: <stable name for this Spark schedule>

Execute up to the configured productive `max_tasks_per_run` allowance. Use a separate
branch/PR per repository-changing task. Verify results and post DONE, BLOCKED, or
NEEDS_REVIEW with durable evidence. A task-local BLOCKED result does not consume the
productive allowance; continue to another independent eligible task when safe.
```

Gemini Spark supports scheduled tasks directly in its UI. The GitHub/MCP connection is
only the tool transport; Maestaris's Issue protocol remains the coordination layer.

Official Spark schedule documentation:
https://support.google.com/gemini/answer/17094710

## ChatGPT scheduled worker prompt

Use the same semantics, but identify the schedule separately:

```text
dispatcher: chatgpt-pool-a
runtime: chatgpt
instance: <stable ChatGPT schedule name>
```

The same queue can therefore survive one provider being unavailable or rate-limited.

## Orchestrator behavior

The orchestrator should not care which model provider completed a task. Review:

- assignment scope;
- ACK ownership/lease;
- linked PR/commit/check/artifact evidence;
- terminal worker report;
- substantive result.

Provider/runtime metadata is useful for debugging, capacity planning, and Project
dashboards, not for deciding whether evidence is true.


## Review backpressure

Worker throughput must not hide a failed reviewer. Before a dispatcher claims another
READY task, it counts terminal reports it previously posted that still lack a later
orchestrator review. When that count reaches
`defaults.max_pending_reviews_per_dispatcher`, the dispatcher stops claiming new work.

The default is 4. This is deliberately high enough that short review stalls do not
starve both worker pools, while still bounding an unattended backlog. Because review is
a persistent drain, reaching the limit is a health signal rather than a normal steady
state. Projects may tune the limit for their review capacity.
