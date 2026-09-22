# Zerion CLI

The CLI is optional setup and maintenance tooling. AI agents can operate Zerion directly through a connected GitHub interface.

## Install

```bash
python -m pip install -e .
```

## Initialize

```bash
zerion init quantum-compression \
  --workers theory implementation audit \
  --repository owner/repository
```

This creates an Issue-native project, namespaced agent entries, worker state indexes, global registration, and root `AGENTS.md` only when absent.

The default path does **not** require `gh`.

## Status

```bash
zerion status
zerion status --json
```

## Validate

```bash
zerion validate
```

## Legacy mailbox compatibility

```bash
zerion init old-project --workers theory audit --mailboxes
```

or:

```bash
zerion mailboxes create old-project
```

These commands require authenticated GitHub CLI and are deprecated. They exist only for older PR-mailbox deployments.
