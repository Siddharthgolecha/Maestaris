# Reusable Zerion workflow

A repository that already contains Zerion configuration can consume the protocol validator and Issue-label synchronizer without copying Zerion's implementation scripts.

## Consumer workflow

Create `.github/workflows/zerion.yml` in the consumer repository:

```yaml
name: Zerion protocol

on:
  issues:
    types: [opened, edited, reopened, closed]
  issue_comment:
    types: [created, edited, deleted]

permissions:
  contents: read
  issues: write

jobs:
  zerion:
    uses: Siddharthgolecha/Zerion/.github/workflows/reusable-zerion.yml@v0.6.1
    with:
      zerion_ref: v0.6.1
    secrets: inherit
```

The called workflow checks out the consumer repository, checks out the selected Zerion runtime separately, validates the consumer's static Zerion configuration, validates the current Issue/comment event, and synchronizes managed labels.

`ZERION_PROJECT_ROOT` separates the consumer configuration from the reusable runtime implementation. The consumer does not need copies of `scripts/validate_github_event.py` or `scripts/sync_github_issue.py`.

## Permissions

The caller must grant:

```yaml
permissions:
  contents: read
  issues: write
```

A called workflow cannot elevate permissions granted by its caller.

ProjectV2 synchronization is optional and requires a separate Project-capable credential. Pass the Project node ID as `project_id` and the token as `project_token` only when `github.projects.field_sync.enabled` is true in the consumer's `coordination/zerion.yaml`.

Example:

```yaml
jobs:
  zerion:
    uses: Siddharthgolecha/Zerion/.github/workflows/reusable-zerion.yml@v0.6.1
    with:
      zerion_ref: v0.6.1
      project_id: ${{ vars.ZERION_PROJECT_ID }}
    secrets:
      project_token: ${{ secrets.ZERION_PROJECT_TOKEN }}
```

Do not pass model-provider credentials to this workflow.

## Version pinning

For stable repositories, pin both the reusable workflow and `zerion_ref` to the same release tag. `v0.6.1` is the first release intended for external reusable-workflow consumption.

Use `@main` only for deliberate canary testing. A consumer that calls `@main` accepts unreleased changes and should not be treated as reproducible production configuration.

For higher-assurance deployments, pin the reusable workflow to a full commit SHA and set `zerion_ref` to the same SHA.

## Compatibility policy

Zerion uses semantic versions while the protocol is pre-1.0:

- patch (`0.6.x`): compatible fixes/tooling additions within the current protocol;
- minor (`0.x.0`): may add or revise protocol/runtime capabilities and requires reading the migration notes;
- major (`1.0.0+`): reserved for a stable public compatibility contract.

The consumer repository owns its static project configuration. Upgrading Zerion changes the runtime implementation; it must not silently replace the consumer's `AGENTS.md`, project YAML, or project-specific evidence.

## Upgrade path

1. Read `CHANGELOG.md` for the target release.
2. Update the reusable workflow tag and `zerion_ref` together.
3. Open a pull request in the consumer repository.
4. Let normal CI run `zerion validate` against the consumer configuration.
5. Merge only after validation passes.

If an upgrade requires a protocol migration, perform that migration explicitly in the consumer PR rather than letting the reusable workflow mutate versioned project files.
