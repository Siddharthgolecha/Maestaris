# GitHub Projects with Maestaris

GitHub Projects is an excellent **mission board** for Maestaris, but it is intentionally not part of the canonical protocol.

A worker must be able to reconstruct a task from repository config plus the GitHub Issue/PR history even if the Project is deleted.

## Why Projects fits

Maestaris task Issues already contain the durable work items.

The shipped GitHub Action derives labels from protocol events. GitHub Projects can auto-add matching Issues and provide board/table/roadmap views over them.

No duplicate task database is required.

## Recommended setup

Create a GitHub Project owned by your user or organization.

In the Project's **Workflows** settings, enable **Auto-add to project** for the Maestaris repository with:

```text
is:issue label:"maestaris:task"
```

Maestaris's repository workflow adds the `maestaris:task` label to valid task Issues. GitHub's auto-add workflow can therefore pick them up after creation/update.

Also enable:

- **Item added to project -> Status: Todo**
- the built-in workflow that moves closed Issues to **Done**

## Recommended views

### Active

Filter open task Issues.

### Ready

```text
label:maestaris:ready
```

### Claimed

```text
label:maestaris:claimed
```

### Needs review

```text
label:maestaris:needs-review
```

### Blocked

```text
label:maestaris:blocked
```

### Priority

For example:

```text
label:priority:P0
```

## Status labels

Maestaris derives exactly one live status label from the Issue event history. READY means the work is available and has no active ACK owner:

```text
maestaris:ready
maestaris:claimed
maestaris:blocked
maestaris:needs-review
maestaris:accepted
maestaris:revise
maestaris:rejected
```

These are dashboard/search metadata.

If a label disagrees with the Issue comments, the Issue comments are authoritative.

## Custom Project fields

You may add fields such as Worker, Project, Priority, Research phase, Release, Dispatcher, or Runtime.

Do not make custom fields mandatory for worker correctness unless every runtime you use can reliably read/write GitHub Projects.

For the default Maestaris setup, structured Issue bodies remain portable across ChatGPT, Gemini Spark, Claude, API agents, and other GitHub-connected runtimes.

### Optional automatic field synchronization

Labels are always the portable fallback. If you want the native Project fields themselves to stay synchronized, enable `github.projects.field_sync` in `coordination/maestaris.yaml`.

The shipped event workflow can mirror:

- `Priority` from the task Issue's `priority:` field;
- `Status` from the reduced Issue event history;
- `Worker`, `Dispatcher`, and `Runtime` from the latest ACK.

Set these repository values:

```text
Repository variable:
  MAESTARIS_PROJECT_ID=<ProjectV2 node ID>

Repository secret:
  MAESTARIS_PROJECT_TOKEN=<token with permission to update that Project>
```

Then set:

```yaml
github:
  projects:
    field_sync:
      enabled: true
```

The Project should contain fields matching the configured names. By default Maestaris expects:

```text
Priority     single select: P0 / P1 / P2
Status       single select: Todo / In Progress / Done
Worker       text
Dispatcher   text
Runtime      text
```

The mappings are configurable in `coordination/maestaris.yaml`.

A personal/user Project commonly needs credentials beyond the repository's normal `GITHUB_TOKEN`; that is why Project synchronization uses a separate optional token. If the token/project ID is absent, the workflow safely skips Project mutation and the normal labels continue to work.

The field synchronizer also adds the task Issue to the configured Project if it is not already present.

If Project fields ever disagree with Issue history, Issue history wins.

## Automation boundary

GitHub Projects and Actions react to GitHub events.

They do not wake an ordinary ChatGPT conversation.

Scheduled/manual Maestaris workers still poll GitHub for eligible work.

## Advanced Projects API automation

GitHub exposes Projects through GraphQL and Actions can automate Projects with appropriate credentials.

This is optional. It may require permissions beyond the repository's normal `GITHUB_TOKEN`, so Maestaris's core does not depend on it.

Prefer GitHub's built-in auto-add/status workflows when they are sufficient.
