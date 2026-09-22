# Multi-model GitHub runtimes

Zerion's protocol is provider-neutral. GitHub carries durable task state; the model/runtime only changes **how a worker is invoked, authenticated, and given repository access**.

This guide was checked against vendor documentation on 2026-09-22. Provider products change quickly, so treat the linked official documentation as authoritative for current availability and authentication details.

## The invariant protocol

Every runtime should preserve the same lifecycle:

```text
open Zerion task Issue
        |
        v
      READY
        |
        | worker posts ACK
        v
     CLAIMED
        |
        | branch / PR / checks / artifacts
        v
 DONE / BLOCKED / NEEDS_REVIEW
        |
        | orchestrator review
        v
 ACCEPTED / REVISE / REJECTED
```

A provider integration must not invent a second canonical task database. GitHub Issue history remains the live control plane. Labels and Projects are derived views.

## Runtime comparison

| Runtime | Repository access | Invocation | Can GitHub events invoke it directly? | Authentication | Zerion fit |
| --- | --- | --- | --- | --- | --- |
| ChatGPT + GitHub app/plugin | Authorized repository content is retrieved on demand; the GitHub connection itself is read-only for repository analysis/search | Interactive chat or scheduled polling | **Ordinary chat: no.** Eligible ChatGPT Work users can create event-triggered tasks for supported GitHub **pull-request activity** | Install/authorize the ChatGPT GitHub app and select repositories | Strong for ordinary-chat orchestrators/workers that poll Issues; use Codex/other write-capable tooling when repository mutation is needed |
| Gemini CLI | Local/runner checkout plus CLI tools; project context can live in `GEMINI.md` | Interactive CLI, headless/non-interactive CLI, scripts | Not by itself; GitHub Actions can invoke Gemini CLI on GitHub events | Google sign-in, Gemini API key, or supported Google Cloud/Vertex authentication depending on deployment | Strong for terminal workers and custom automation |
| `google-github-actions/run-gemini-cli` | GitHub Actions checkout/context and configured tools | GitHub workflow | **Yes.** Supports issue/PR events, comments/mentions, schedules, and custom workflows | `GEMINI_API_KEY` for simple setup; Google Cloud auth options are also supported | Strong optional event-driven adapter |
| Claude chat + GitHub integration | User selects repository files/folders as chat/project context | Interactive Claude chat | No documented direct chat wake-up from GitHub Issue events | Authenticate/connect GitHub in Claude | Useful read/context surface; use Claude Code for agentic repository work |
| Claude Code | Local/runner checkout with Claude Code tools and `CLAUDE.md` project instructions | Interactive CLI or programmatic/SDK use | Not by itself; Actions can invoke it | Anthropic/API or supported cloud-provider authentication | Strong terminal worker |
| `anthropics/claude-code-action` | GitHub runner plus Issue/PR context and configured GitHub permissions | GitHub workflow | **Yes.** Can react to Issue/PR comments, PR events, assignments, schedules, and explicit automation prompts | `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, Anthropic workload identity federation, or supported Bedrock/Vertex/Foundry paths | Strong optional event-driven adapter |

The important distinction is **chat connection versus execution runtime**. A chat product that can read GitHub context is not automatically a webhook target and is not automatically allowed to mutate the repository.

## ChatGPT / OpenAI

### Connected GitHub access

OpenAI documents the ChatGPT GitHub connection as live, on-demand access to repositories authorized through the GitHub app. It can retrieve code, README files, and other repository documentation. It does **not** create a synchronized GitHub index. Availability varies by plan, workspace, and product surface.

The GitHub app connection is documented as read-only for analyzing and searching repository content. OpenAI directs users who want to generate, edit, and push code directly to GitHub to Codex.

For Zerion this means a normal connected ChatGPT conversation can reason over repository state when the relevant GitHub tools are exposed, but write capability must come from the runtime/tool surface actually available to that conversation. Never assume that connecting GitHub alone grants write access.

### Scheduled polling

Ordinary ChatGPT conversations are not webhook endpoints. The portable Zerion pattern is therefore:

1. schedule or manually invoke the orchestrator/worker conversation;
2. search the repository for open Zerion task Issues;
3. read Issue history and dependencies;
4. claim eligible work with an ACK if write-capable GitHub tooling is available;
5. do the bounded work and report durable evidence.

This is eventual execution by polling, not GitHub event delivery to an ordinary sidebar chat.

### Event-triggered Work tasks

OpenAI now documents event-triggered tasks in ChatGPT Work for eligible users. GitHub triggers currently cover supported **pull-request activity** in authorized `github.com` repositories, including trigger-dependent PR open/ready/close, review, comment, commit-update, and merge activity.

Do not generalize this into "any GitHub Issue comment wakes ChatGPT." OpenAI's current documentation describes GitHub PR activity, not arbitrary Zerion Issue-comment wakeups. Self-hosted GitHub Enterprise is also not supported for these event-triggered GitHub tasks.

Therefore Zerion should keep scheduled/manual polling as a first-class ChatGPT runtime even when Work event triggers are available.

### Practical ChatGPT setup

1. Connect GitHub in ChatGPT Apps/Plugins and authorize only the repositories the worker needs.
2. Give the chat a role such as: `Use Zerion on owner/repo. Act as worker pool A.`
3. For unattended ordinary-chat operation, schedule the worker to poll GitHub at an appropriate cadence.
4. Keep the Issue/ACK/result protocol unchanged.
5. If using Work event triggers, use them only for the PR events OpenAI currently supports; they are an optimization, not a replacement for Zerion's portable polling semantics.

Official sources:

- https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt
- https://help.openai.com/en/articles/10291617-tasks-in-chatgpt
- https://help.openai.com/en/articles/11487775-connectors-in-chatgpt

## Gemini / Google

### Gemini CLI

Gemini CLI is suitable for interactive terminal use and automation. Project-specific instructions can be stored in `GEMINI.md`, which maps naturally to Zerion's repository-local instruction model.

A terminal worker can clone/check out the repository, read `AGENTS.md`, inspect the Zerion Issue through GitHub tooling, ACK it, work on a branch, and report the result. The Zerion protocol does not depend on the model being ChatGPT.

### Gemini CLI GitHub Action

Google's `run-gemini-cli` Action is the event-driven path. Google's official repository documents:

- automation on GitHub events and schedules;
- issue triage and pull-request review;
- on-demand `@gemini-cli` assistance in Issues and PRs;
- custom workflows and access to other CLIs such as `gh`;
- `GEMINI.md` for project context;
- `/setup-github` as the recommended guided setup path;
- `GEMINI_API_KEY` as the simple API-key setup, with Google Cloud authentication options available for other deployments.

For Zerion, an Action can be configured to inspect a newly READY task or an Issue comment and run a worker immediately. It should still post the same `[WORKER:<name>:v1]` ACK and terminal report used by every other runtime.

### Practical Gemini setup

Simple path:

1. Install Gemini CLI.
2. Add repository guidance in `GEMINI.md` that tells Gemini to read `AGENTS.md` and preserve the Zerion protocol.
3. Run `/setup-github`, or install the official example workflows manually.
4. Store `GEMINI_API_KEY` in GitHub Actions secrets when using API-key authentication; never commit it.
5. Restrict workflow/GitHub permissions to what the worker actually needs.
6. Configure the workflow trigger you want (`issues`, `issue_comment`, PR events, schedule, or manual dispatch).
7. In the workflow prompt, tell the worker to derive state from Issue history and ACK before substantive work.

Provider-specific invocation changes; the Zerion task format does not.

Official sources:

- https://github.com/google-gemini/gemini-cli
- https://github.com/google-github-actions/run-gemini-cli

## Claude / Anthropic

### Claude chat GitHub integration

Anthropic's Claude GitHub integration lets a user add GitHub repository files/folders to chats and Claude Projects as context. This is useful for analysis and interactive work, but it should not be confused with Claude Code's GitHub automation runtime.

For a Zerion chat worker, treat this as context access. If the chat surface lacks GitHub write actions, it cannot establish durable ownership merely by saying it has claimed a task; the ACK must exist on GitHub.

### Claude Code

Claude Code is the stronger execution surface for repository work. `CLAUDE.md` can carry project instructions, analogous to `GEMINI.md`; in a Zerion repository it should point the worker to the canonical root `AGENTS.md` rather than fork the protocol.

### Claude Code GitHub Action

Anthropic's official `claude-code-action` v1 can run on GitHub runners and supports interactive Issue/PR mentions as well as automation prompts. The official documentation shows triggers such as `issue_comment`, `pull_request_review_comment`, PR events, and schedules.

The current setup guide supports:

- `ANTHROPIC_API_KEY`;
- `CLAUDE_CODE_OAUTH_TOKEN` for supported Claude Code subscription-token use;
- Anthropic Workload Identity Federation, exchanging GitHub Actions OIDC for short-lived Anthropic credentials so a static API key need not be stored;
- AWS Bedrock, Google Vertex AI, and Microsoft Foundry deployment paths.

The action's own GitHub permissions should be least-privilege. Anthropic's setup documentation also notes that GitHub App tokens are useful when generated workflow activity must trigger downstream CI, because actions performed with the default `GITHUB_TOKEN` have GitHub anti-recursion limitations.

### Practical Claude setup

1. Run Claude Code locally and use `/install-github-app`, or perform the documented manual GitHub App/workflow setup.
2. Prefer short-lived/workload-identity authentication where appropriate; otherwise keep provider credentials in GitHub Secrets.
3. Add a concise `CLAUDE.md` that points to `AGENTS.md` and the Zerion task lifecycle.
4. Trigger the Action from the GitHub event appropriate to the repository.
5. Give only the GitHub permissions needed to read/modify Issues, contents, and PRs for that workflow.
6. Make the Action post a normal Zerion ACK before work and a normal terminal event afterward.

Official sources:

- https://support.claude.com/en/articles/10167454-use-the-github-integration
- https://docs.anthropic.com/en/docs/claude-code/github-actions
- https://github.com/anthropics/claude-code-action
- https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md

## Provider-neutral worker prompt

The same core prompt can be used by ChatGPT, Gemini CLI, Claude Code, or another capable runtime:

```text
Use Zerion on OWNER/REPO as worker pool A.
Read AGENTS.md and current repository configuration first.
Search open zerion:task Issues, derive state from Issue history, and select the
highest-priority eligible READY task for this pool. Respect dependencies and
unexpired ACK leases. Post a protocol ACK before substantive work. Work on a
separate branch/PR when repository changes are required. Verify the result and
post DONE, BLOCKED, or NEEDS_REVIEW with durable evidence. Do not invent work
when no eligible task exists.
```

Only the wrapper differs:

- **ChatGPT ordinary chat:** invoke manually or on a schedule and let it poll.
- **ChatGPT Work:** optionally use supported PR-event triggers.
- **Gemini CLI / Claude Code locally:** invoke interactively or headlessly against a checkout.
- **Gemini / Claude GitHub Actions:** let GitHub events invoke the workflow.

## Security and permissions

Regardless of provider:

- never place model-provider credentials in Issues, prompts committed to the repository, logs, or source files;
- prefer GitHub Secrets, OIDC/workload identity, or other documented short-lived credentials;
- grant the workflow only the GitHub permissions required for the task;
- treat Issue/PR/comment text and fork contributions as untrusted input;
- do not expose secrets to untrusted fork workflows;
- keep branch protection/rulesets and required checks outside the model's ability to silently bypass them;
- remember that model/API cost and GitHub Actions runner cost are separate concerns;
- require durable checks/evidence before an orchestrator promotes a substantive result.

See the repository security/governance workstream for Zerion-specific hardening. This document describes runtime integration, not a complete threat model.

## Choosing a runtime

Use **ordinary ChatGPT polling** when the goal is to reuse persistent ChatGPT conversations without standing up API agents. This is Zerion's most distinctive path.

Use **Gemini CLI or Claude Code locally** when a terminal-native worker is desirable and a human or external scheduler can invoke it.

Use **Gemini/Claude GitHub Actions** when true GitHub-event-driven execution is more important than preserving an ordinary-chat runtime. These are optional adapters, not a reason to change Zerion's durable Issue protocol.

Use **ChatGPT Work event triggers** when available and the desired event is one of the currently supported GitHub PR activities. Keep polling for Issue-centric worker dispatch unless OpenAI explicitly adds an Issue event trigger surface.
