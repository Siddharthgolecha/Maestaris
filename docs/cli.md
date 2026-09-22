# Zerion CLI

The CLI is optional setup and maintenance tooling. AI agents can operate Zerion directly through a connected GitHub interface.

## Install

Normal editable install:

```bash
python -m pip install -e .
```

In a network-restricted environment where build dependencies are already installed, avoid pip build isolation:

```bash
python -m pip install --no-build-isolation -e .
```

This distinction matters for agent sandboxes: a connected GitHub interface may work even when the shell cannot reach package indexes or github.com.

The core AI protocol does not require CLI installation.

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
