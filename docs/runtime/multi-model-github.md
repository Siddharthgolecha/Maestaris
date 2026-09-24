# Multi-model GitHub runtimes

Maestaris's protocol is provider-neutral. GitHub carries durable task state; the model/runtime only changes **how a worker is invoked, authenticated, and given repository access**.

This guide was checked against vendor documentation on 2026-09-22. Provider products change quickly, so treat the linked official documentation as authoritative for current availability and authentication details.

## The invariant protocol

Every runtime should preserve the same lifecycle:

```text
open Maestaris task Issue
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

## Recommended default: UI first

For normal Maestaris use, start with the provider's **web/UI connection path** when it gives the worker enough GitHub access. API keys, CLIs, and GitHub Actions are optional escalation paths for unattended or event-driven automation; they should not be presented as requirements for ordinary use.

A useful progression is:

1. connect GitHub in the provider UI;
2. verify that the current surface can read the repository and, if needed, perform durable GitHub writes;
3. use manual or scheduled polling from that UI;
4. move to CLI/API/Actions only when you specifically need headless execution, GitHub-event-driven invocation, stronger repository mutation, or organization automation.

Authentication and write capability differ by provider and product surface. Never assume that a UI connection is write-capable merely because it can read repository context.

## Runtime comparison

| Runtime | Repository access | Invocation | Can GitHub events invoke it directly? | Authentication | Maestaris fit |
| --- | --- | --- | --- | --- | --- |
| ChatGPT web + GitHub app/plugin | Authorized repository content is retrieved on demand; the standard GitHub connection is documented as read-only for repository analysis/search | Interactive chat or scheduled polling | **Ordinary chat: no.** Eligible ChatGPT Work users can create event-triggered tasks for supported GitHub **pull-request activity** | UI connection/authorization; no API key required for ordinary connected-app use | Strong UI-first orchestrator/worker surface; use an available write-capable GitHub tool/Codex when mutation is required |
| Gemini web / Spark + GitHub | UI-first options include importing a GitHub repository for code context and, for eligible Spark users, adding custom MCP connected apps | Interactive Gemini chat or Spark task/schedule | Spark can run its own schedules/monitors, but GitHub itself does not directly wake a normal Gemini chat merely because a repository event happened | UI account connection/OAuth; custom MCP apps can be added by MCP server URL; no model API key is inherently required for this path | Strong UI-first option when the connected app exposes the GitHub tools Maestaris needs |
| Gemini CLI | Local/runner checkout plus CLI tools; project context can live in `GEMINI.md` | Interactive CLI, headless/non-interactive CLI, scripts | Not by itself; GitHub Actions can invoke Gemini CLI on GitHub events | Google sign-in, Gemini API key, or supported Google Cloud/Vertex authentication depending on deployment | Optional terminal/headless worker |
| `google-github-actions/run-gemini-cli` | GitHub Actions checkout/context and configured tools | GitHub workflow | **Yes.** Supports issue/PR events, comments/mentions, schedules, and custom workflows | `GEMINI_API_KEY` for simple setup; Google Cloud auth options are also supported | Strong optional event-driven adapter |
| Claude web + GitHub integration | User selects repository files/folders as chat/project context; connected GitHub access is configured through the UI | Interactive Claude chat/project | No documented direct chat wake-up from GitHub Issue events | UI GitHub connection/authentication; no Anthropic API key required for ordinary connected-chat use | Strong UI-first context surface; use write-capable connectors/Claude Code when durable repository mutation is required |
| Claude Code | Local/runner checkout with Claude Code tools and `CLAUDE.md` project instructions | Interactive CLI or programmatic/SDK use | Not by itself; Actions can invoke it | Anthropic/API or supported cloud-provider authentication | Strong terminal worker |
| `anthropics/claude-code-action` | GitHub runner plus Issue/PR context and configured GitHub permissions | GitHub workflow | **Yes.** Can react to Issue/PR comments, PR events, assignments, schedules, and explicit automation prompts | `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, Anthropic workload identity federation, or supported Bedrock/Vertex/Foundry paths | Strong optional event-driven adapter |

The important distinction is **chat connection versus execution runtime**. A chat product that can read GitHub context is not automatically a webhook target and is not automatically allowed to mutate the repository.

## ChatGPT / OpenAI

### Connected GitHub access

OpenAI documents the ChatGPT GitHub connection as live, on-demand access to repositories authorized through the GitHub app. It can retrieve code, README files, and other repository documentation. It does **not** create a synchronized GitHub index. Availability varies by plan, workspace, and product surface.

The GitHub app connection is documented as read-only for analyzing and searching repository content. OpenAI directs users who want to generate, edit, and push code directly to GitHub to Codex.

For Maestaris this means a normal connected ChatGPT conversation can reason over repository state when the relevant GitHub tools are exposed, but write capability must come from the runtime/tool surface actually available to that conversation. Never assume that connecting GitHub alone grants write access.

### Scheduled polling

Ordinary ChatGPT conversations are not webhook endpoints. The portable Maestaris pattern is therefore:

1. schedule or manually invoke the orchestrator/worker conversation;
2. search the repository for open Maestaris task Issues;
3. read Issue history and dependencies;
4. claim eligible work with an ACK if write-capable GitHub tooling is available;
5. do the bounded work and report durable evidence.

This is eventual execution by polling, not GitHub event delivery to an ordinary sidebar chat.

### Event-triggered Work tasks

OpenAI now documents event-triggered tasks in ChatGPT Work for eligible users. GitHub triggers currently cover supported **pull-request activity** in authorized `github.com` repositories, including trigger-dependent PR open/ready/close, review, comment, commit-update, and merge activity.

Do not generalize this into "any GitHub Issue comment wakes ChatGPT." OpenAI's current documentation describes GitHub PR activity, not arbitrary Maestaris Issue-comment wakeups. Self-hosted GitHub Enterprise is also not supported for these event-triggered GitHub tasks.

Therefore Maestaris should keep scheduled/manual polling as a first-class ChatGPT runtime even when Work event triggers are available.

### Practical ChatGPT setup

1. Connect GitHub in ChatGPT Apps/Plugins and authorize only the repositories the worker needs.
2. Give the chat a role such as: `Use Maestaris on owner/repo. Act as worker pool A.`
3. For unattended ordinary-chat operation, schedule the worker to poll GitHub at an appropriate cadence.
4. Keep the Issue/ACK/result protocol unchanged.
5. If using Work event triggers, use them only for the PR events OpenAI currently supports; they are an optimization, not a replacement for Maestaris's portable polling semantics.

Official sources:

- https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt
- https://help.openai.com/en/articles/10291617-tasks-in-chatgpt
- https://help.openai.com/en/articles/11487775-connectors-in-chatgpt

## Gemini / Google

### Gemini web app and Spark

For ordinary Maestaris use, the Gemini website can be the first choice; an API key is not required merely to work through the UI.

Google documents two relevant UI paths:

1. **GitHub repository import** in the Gemini web app. This attaches a repository/branch for code understanding. It is context-oriented: Google notes that the imported repository is not continuously synced, and this path does not expose commit history, pull requests, or repository writes.
2. **Gemini Spark custom connected apps** for eligible users. Spark can connect a custom app from an MCP server URL and use it from the Gemini web/mobile experience.

A practical GitHub-capable Spark setup used with Maestaris is to add a custom MCP app using GitHub's remote MCP endpoint:

```text
https://api.githubcopilot.com/mcp/
```

GitHub documents OAuth-capable setup for its remote MCP server, so this path can be configured through an interactive authorization flow rather than by embedding a model API key in Maestaris. Exact OAuth screens and account eligibility are provider/client-specific and can change.

The important Maestaris test is capability, not setup style: after connecting the app, verify that Gemini can actually read Issues and, if the workflow requires it, write ACK/result comments and PR-related changes. If the UI connection is read-only, keep it for context and use a write-capable runtime for durable Maestaris events.

Official UI sources:

- https://support.google.com/gemini/answer/16176929
- https://support.google.com/gemini/answer/17209137
- https://support.google.com/gemini/answer/17094507
- https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp-in-your-ide/set-up-the-github-mcp-server

### Gemini CLI

Gemini CLI is an optional terminal/headless path when UI operation is not enough. Project-specific instructions can be stored in `GEMINI.md`, which maps naturally to Maestaris's repository-local instruction model.

A terminal worker can clone/check out the repository, read `AGENTS.md`, inspect the Maestaris Issue through GitHub tooling, ACK it, work on a branch, and report the result. The Maestaris protocol does not depend on the model being ChatGPT.

### Gemini CLI GitHub Action

Google's `run-gemini-cli` Action is the event-driven path. Google's official repository documents:

- automation on GitHub events and schedules;
- issue triage and pull-request review;
- on-demand `@gemini-cli` assistance in Issues and PRs;
- custom workflows and access to other CLIs such as `gh`;
- `GEMINI.md` for project context;
- `/setup-github` as the recommended guided setup path;
- `GEMINI_API_KEY` as the simple API-key setup, with Google Cloud authentication options available for other deployments.

For Maestaris, an Action can be configured to inspect a newly READY task or an Issue comment and run a worker immediately. It should still post the same `[WORKER:<name>:v1]` ACK and terminal report used by every other runtime.

### Practical Gemini setup

**UI-first path:**

1. Open Gemini web/Spark and connect GitHub through the available UI.
2. For code-context-only work, use Gemini's GitHub repository import.
3. For a tool-capable Spark setup, add a custom MCP app using the GitHub remote MCP server URL and complete the interactive authorization flow exposed by the client.
4. Tell the worker to read Maestaris's `AGENTS.md` and operate on the repository.
5. Verify read/write capabilities with a low-risk test Issue before relying on the connection for ACK/result writes.
6. Use Spark scheduling if it fits the account/product surface.

**Optional automation path:**

1. Install Gemini CLI when terminal/headless execution is useful.
2. Add repository guidance in `GEMINI.md` that points Gemini to `AGENTS.md`.
3. Run `/setup-github`, or install the official GitHub Action workflows manually.
4. Use UI/Google sign-in where supported; if the chosen Action deployment requires credentials, store them in GitHub Secrets or use the documented Google Cloud authentication path.
5. Restrict workflow/GitHub permissions to what the worker actually needs.
6. Configure the desired event trigger and keep the normal Maestaris ACK/result protocol.

Provider-specific invocation changes; the Maestaris task format does not.

Official sources:

- https://github.com/google-gemini/gemini-cli
- https://github.com/google-github-actions/run-gemini-cli

## Claude / Anthropic

### Claude chat GitHub integration

Anthropic's Claude GitHub integration lets a user add GitHub repository files/folders to chats and Claude Projects as context. This is useful for analysis and interactive work, but it should not be confused with Claude Code's GitHub automation runtime.

For a Maestaris chat worker, treat this as context access. If the chat surface lacks GitHub write actions, it cannot establish durable ownership merely by saying it has claimed a task; the ACK must exist on GitHub.

### Claude Code

Claude Code is the stronger execution surface for repository work. `CLAUDE.md` can carry project instructions, analogous to `GEMINI.md`; in a Maestaris repository it should point the worker to the canonical root `AGENTS.md` rather than fork the protocol.

### Claude Code GitHub Action

Anthropic's official `claude-code-action` v1 can run on GitHub runners and supports interactive Issue/PR mentions as well as automation prompts. The official documentation shows triggers such as `issue_comment`, `pull_request_review_comment`, PR events, and schedules.

The current setup guide supports:

- `ANTHROPIC_API_KEY`;
- `CLAUDE_CODE_OAUTH_TOKEN` for supported Claude Code subscription-token use;
- Anthropic Workload Identity Federation, exchanging GitHub Actions OIDC for short-lived Anthropic credentials so a static API key need not be stored;
- AWS Bedrock, Google Vertex AI, and Microsoft Foundry deployment paths.

The action's own GitHub permissions should be least-privilege. Anthropic's setup documentation also notes that GitHub App tokens are useful when generated workflow activity must trigger downstream CI, because actions performed with the default `GITHUB_TOKEN` have GitHub anti-recursion limitations.

### Practical Claude setup

**UI-first path:**

1. In Claude, connect GitHub through the UI.
2. Add the relevant repository/files to the chat or Claude Project.
3. Point Claude at Maestaris's `AGENTS.md` and task Issue.
4. Use the connected web experience for the work it supports; no Anthropic API key is required merely to use the GitHub integration.
5. If the current web surface cannot perform the durable GitHub writes Maestaris needs, use Claude Code or another write-capable connector for those events.

**Optional automation path:**

1. Run Claude Code locally and use `/install-github-app`, or perform the documented GitHub App/workflow setup.
2. Prefer short-lived/workload-identity authentication where appropriate; otherwise keep provider credentials in GitHub Secrets.
3. Add a concise `CLAUDE.md` that points to `AGENTS.md` and the Maestaris task lifecycle.
4. Trigger the Action from the GitHub event appropriate to the repository.
5. Give only the GitHub permissions needed to read/modify Issues, contents, and PRs for that workflow.
6. Make the Action post a normal Maestaris ACK before work and a normal terminal event afterward.

Official sources:

- https://support.claude.com/en/articles/10167454-use-the-github-integration
- https://docs.anthropic.com/en/docs/claude-code/github-actions
- https://github.com/anthropics/claude-code-action
- https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md

## Provider-neutral worker prompt

The same core prompt can be used by ChatGPT, Gemini CLI, Claude Code, or another capable runtime:

```text
Use Maestaris on OWNER/REPO as worker pool A.
Read AGENTS.md and current repository configuration first.
Search open maestaris:task Issues, derive state from Issue history, and select the
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

See the repository security/governance workstream for Maestaris-specific hardening. This document describes runtime integration, not a complete threat model.

## Choosing a runtime

Use the provider's **web/UI connection first** when it exposes the GitHub capabilities the worker needs. This keeps setup simple and avoids unnecessary API-key infrastructure.

Use **ordinary ChatGPT polling** when the goal is to reuse persistent ChatGPT conversations without standing up API agents. This is Maestaris's most distinctive path.

Use **Gemini Spark/web or Claude web** for UI-first connected operation when their current connected-app surface is sufficient.

Use **Gemini CLI or Claude Code locally** when a terminal-native worker is desirable and a human or external scheduler can invoke it.

Use **Gemini/Claude GitHub Actions** when true GitHub-event-driven execution is more important than preserving an ordinary-chat runtime. These are optional adapters, not a reason to change Maestaris's durable Issue protocol.

Use **ChatGPT Work event triggers** when available and the desired event is one of the currently supported GitHub PR activities. Keep polling for Issue-centric worker dispatch unless OpenAI explicitly adds an Issue event trigger surface.
