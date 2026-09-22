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

## Gemini Spark scheduled worker prompt

Create a Spark schedule and use a prompt like:

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
