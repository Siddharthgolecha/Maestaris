# Multi-AI orchestration

Zerion does not require every scheduled worker to run on the same model provider.

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

Existing Zerion workers that omit `runtime` or `instance` remain valid.

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

When `scheduler_bootstrap.enabled` is true, an orchestrator should reconcile **two
layers**: one recurring orchestrator schedule for its runtime, then the configured
worker-pool dispatcher schedules. A provider that supports schedule management should
create missing schedules, update drifted ones, and avoid duplicates by using stable
instance names. A one-shot bootstrap chat is not enough for unattended operation
because terminal worker results still require independent recurring review.

For the default Zerion topology:

```text
pools: A, B

Gemini Spark bootstrap session
  -> ensures zerion-gemini-spark-orchestrator exists and recurs
  -> ensures zerion-gemini-spark-pool-A exists
  -> ensures zerion-gemini-spark-pool-B exists
  -> keeps all three hourly and staggered
```

This makes the user-facing bootstrap:

```text
connect GitHub to provider
      |
user creates ONE provider orchestrator
      |
prompt: "Use Zerion on OWNER/REPO as orchestrator."
      |
      +--> orchestrator reads AGENTS.md + coordination/zerion.yaml
      +--> discovers pools / cadence / identities / protocol
      +--> creates or reconciles a recurring orchestrator schedule
      +--> creates or reconciles provider-owned worker schedules
      +--> orchestrator reviews terminal results; workers service READY queue
```

GitHub is the bootstrap memory and desired-state source; the provider remains the
owner of its actual scheduled tasks.

Live schedules are intentionally not copied into GitHub as canonical state. They are
provider runtime objects. GitHub records the desired topology and all durable work.

### Gemini Spark orchestrator bootstrap prompt

Start one Gemini Spark task with instructions like:

```text
Act as the Zerion orchestrator for OWNER/REPO.

Read AGENTS.md and coordination/zerion.yaml first. Treat GitHub as the durable system
of record.

On startup, inspect scheduler_bootstrap and the configured pools. Because Gemini Spark
supports conversational schedule management, ensure there is one recurring Spark
orchestrator schedule plus one recurring worker-dispatcher schedule for every configured
Zerion pool. If this task is already the recurring orchestrator schedule, do not create
a duplicate.

Use stable schedule/instance names from the configured templates. For the default
configuration create/reconcile:
- zerion-gemini-spark-orchestrator, hourly, using the configured orchestrator minute;
- zerion-gemini-spark-pool-A, hourly, using the configured Pool A minute hint;
- zerion-gemini-spark-pool-B, hourly, using the configured Pool B minute hint.

Do not create duplicates. If a matching schedule exists, inspect and update it instead.
Each generated worker schedule must read AGENTS.md on every run, poll the shared READY
queue, respect dependencies and unexpired ACK leases, claim at most one task, and use
its stable dispatcher/runtime/instance identity in the ACK.

After reconciling worker schedules, perform the normal Zerion orchestrator duties:
review unreviewed terminal results, inspect actual PR/check/artifact evidence, post
ACCEPTED/REVISE/REJECTED, merge only when warranted, and create bounded READY work
only when useful.

Reconcile the worker schedules again on future orchestrator runs so missing, paused,
or drifted dispatcher schedules are repaired when safe.
```

Gemini Spark supports creating and editing schedules conversationally, so the
orchestrator can perform this bootstrap from the task thread. If provider capabilities
change, capability detection wins over these instructions.

## Gemini Spark scheduled worker prompt

Normally the Gemini orchestrator creates these schedules. The generated Pool A/B
schedule should use a prompt equivalent to:

```text
Act as Zerion worker dispatcher Pool A for OWNER/REPO.

Read AGENTS.md and the current Zerion configuration first. Search open zerion:task
Issues and select the highest-priority eligible READY task for this pool. Read the
Issue history before claiming anything. If another dispatcher owns an unexpired ACK,
skip it.

When claiming a task, post a normal Zerion ACK and identify this scheduler as:

dispatcher: gemini-spark-pool-a
runtime: gemini-spark
instance: <stable name for this Spark schedule>

Execute at most one bounded task per run. Use a separate branch/PR for repository
changes. Verify the result and post DONE, BLOCKED, or NEEDS_REVIEW with durable
evidence. If no eligible task exists, do nothing.
```

Gemini Spark supports scheduled tasks directly in its UI. The GitHub/MCP connection is
only the tool transport; Zerion's Issue protocol remains the coordination layer.

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

The default is 1. This keeps one completed task waiting for review without allowing an
absent orchestrator to drain the entire READY queue into an ever-growing PR backlog.
Projects that intentionally pipeline more review work may raise the limit.
