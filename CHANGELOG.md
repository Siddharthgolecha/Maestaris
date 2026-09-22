# Changelog

## 0.5.0

Breaking protocol release.

- Remove `coordination/state/` and all mutable worker-state YAML.
- Remove permanent PR-mailbox transport and shell-GitHub mailbox bootstrap.
- Make GitHub Issues/comments/PRs/checks the only live orchestration state.
- Bump the Zerion protocol to v3.
- Keep repository YAML limited to stable project/agent topology.
- Add event-history reduction for assigned, claimed, blocked, needs-review, accepted, revise, and rejected states.
- Add GitHub Action synchronization of `zerion:*` status labels and `priority:*` labels.
- Preserve unrelated user labels during synchronization.
- Add GitHub Projects guidance with built-in auto-add and Todo/Done workflows.
- Rewrite README around the intended ordinary-ChatGPT + scheduled-polling + GitHub workflow.
- Explicitly document that GitHub events trigger Actions but do not wake ordinary ChatGPT conversations.
- Make the CLI static-configuration-only and remove live-state/mailbox commands.
- Infer repository name from local git origin without requiring GitHub network access.
- Add a breaking v0.5 migration guide.

## 0.4.0

- Make GitHub Issues the preferred Zerion task/control-plane primitive.
- Use Issue comments for ACK, terminal worker reports, and orchestrator review events.
- Encourage linked draft task PRs for visible work in progress.
- Map accepted/rejected terminal tasks to GitHub completed/not-planned close reasons.
- Add optional native PR review mapping for ACCEPTED and REVISE decisions.
- Add structured Zerion task Issue template.
- Add GitHub Actions validation for Zerion task Issues and protocol comments.
- Add `task.issue` to worker state and remove permanent mailbox requirements from new projects.
- Keep PR-backed mailboxes as deprecated compatibility transport.
- Make default initialization independent of shell-level `gh`.
- Add GitHub-native integration, migration, scaling, and recovery documentation.
- Dogfood finding: connected GitHub access can work even when shell GitHub networking is unavailable.

## 0.3.0

- Make root `AGENTS.md` the normative Zerion entry point for AI agents.
- Add `coordination/zerion.yaml` as the global protocol, pool, defaults, and project registry.
- Add a machine-readable worker-state index.
- Distinguish configuration, current-state index, mailbox event log, and substantive task evidence.
- Extend validation to detect registry/state drift.
- Update role prompts to use deterministic repository bootstrap.

## 0.2.0

- Add installable Zerion CLI.
- Add project initialization and validation helpers.
- Add automatic PR-mailbox bootstrap.
- Add CLI tests and CI coverage.

## 0.1.0

- Initial repository-first orchestration protocol and public templates.
