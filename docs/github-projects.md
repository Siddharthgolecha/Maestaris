# GitHub Projects with Zerion

GitHub Projects is an excellent **mission board** for Zerion, but it is intentionally not part of the canonical protocol.

A worker must be able to reconstruct a task from repository config plus the GitHub Issue/PR history even if the Project is deleted.

## Why Projects fits

Zerion task Issues already contain the durable work items.

The shipped GitHub Action derives labels from protocol events. GitHub Projects can auto-add matching Issues and provide board/table/roadmap views over them.

No duplicate task database is required.

## Recommended setup

Create a GitHub Project owned by your user or organization.

In the Project's **Workflows** settings, enable **Auto-add to project** for the Zerion repository with:

```text
is:issue label:"zerion:task"
```

Zerion's repository workflow adds the `zerion:task` label to valid task Issues. GitHub's auto-add workflow can therefore pick them up after creation/update.

Also enable:

- **Item added to project -> Status: Todo**
- the built-in workflow that moves closed Issues to **Done**

## Recommended views

### Active

Filter open task Issues.

### Ready

```text
label:zerion:ready
```

### Claimed

```text
label:zerion:claimed
```

### Needs review

```text
label:zerion:needs-review
```

### Blocked

```text
label:zerion:blocked
```

### Priority

For example:

```text
label:priority:P0
```

## Status labels

Zerion derives exactly one live status label from the Issue event history. READY means the work is available and has no active ACK owner:

```text
zerion:ready
zerion:claimed
zerion:blocked
zerion:needs-review
zerion:accepted
zerion:revise
zerion:rejected
```

These are dashboard/search metadata.

If a label disagrees with the Issue comments, the Issue comments are authoritative.

## Custom Project fields

You may add fields such as Worker, Project, Priority, Research phase, Release, Dispatcher, or Runtime.

Do not make custom fields mandatory for worker correctness unless every runtime you use can reliably read/write GitHub Projects.

For the default Zerion setup, structured Issue bodies remain portable across ChatGPT, Gemini Spark, Claude, API agents, and other GitHub-connected runtimes.

### Optional automatic field synchronization

Labels are always the portable fallback. If you want the native Project fields themselves to stay synchronized, enable `github.projects.field_sync` in `coordination/zerion.yaml`.

The shipped event workflow can mirror:

- `Priority` from the task Issue's `priority:` field;
- `Status` from the reduced Issue event history;
- `Worker`, `Dispatcher`, and `Runtime` from the latest ACK.

Set these repository values:

```text
Repository variable:
  ZERION_PROJECT_ID=<ProjectV2 node ID>

Repository secret:
  ZERION_PROJECT_TOKEN=<token with permission to update that Project>
```

Then set:

```yaml
github:
  projects:
    field_sync:
      enabled: true
```

The Project should contain fields matching the configured names. By default Zerion expects:

```text
Priority     single select: P0 / P1 / P2
Status       single select: Todo / In Progress / Done
Worker       text
Dispatcher   text
Runtime      text
```

The mappings are configurable in `coordination/zerion.yaml`.

A personal/user Project commonly needs credentials beyond the repository's normal `GITHUB_TOKEN`; that is why Project synchronization uses a separate optional token. If the token/project ID is absent, the workflow safely skips Project mutation and the normal labels continue to work.

The field synchronizer also adds the task Issue to the configured Project if it is not already present.

If Project fields ever disagree with Issue history, Issue history wins.

## Automation boundary

GitHub Projects and Actions react to GitHub events.

They do not wake an ordinary ChatGPT conversation.

Scheduled/manual Zerion workers still poll GitHub for eligible work.

## Advanced Projects API automation

GitHub exposes Projects through GraphQL and Actions can automate Projects with appropriate credentials.

This is optional. It may require permissions beyond the repository's normal `GITHUB_TOKEN`, so Zerion's core does not depend on it.

Prefer GitHub's built-in auto-add/status workflows when they are sufficient.
