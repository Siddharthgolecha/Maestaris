# Zerion CLI

The CLI turns the protocol templates into a repeatable onboarding workflow.

## Install for development

    python -m pip install -e .

This installs the zerion command.

## Initialize a project

    zerion init quantum-compression \
      --workers theory implementation validation audit \
      --repository owner/repository

Workers are namespaced automatically as project-role, for example:

    quantum-compression-theory
    quantum-compression-implementation
    quantum-compression-validation
    quantum-compression-audit

The command creates the project registry, agent registry entries, and an orchestrator entry when needed.

## One-command GitHub bootstrap

When GitHub CLI is installed and authenticated:

    zerion init quantum-compression \
      --workers theory implementation audit \
      --repository owner/repository \
      --mailboxes \
      --commit

This additionally:

1. creates one long-lived mailbox branch per active worker;
2. writes a mailbox marker only on that branch;
3. opens a draft mailbox PR;
4. records each PR number in project and agent YAML;
5. commits the coordination registry changes and pushes them.

The GitHub operation uses your existing gh authentication. Zerion never asks you to place a token in repository configuration.

## Create missing mailboxes later

    zerion mailboxes create quantum-compression

Add --commit to commit and push the updated PR numbers.

## Status

    zerion status

Machine-readable form:

    zerion status --json

## Validate

    zerion validate

Validation checks registry structure, allowed states, project/agent references, and mailbox ownership.

## Safety

zerion mailboxes create requires the GitHub CLI and only creates draft coordination PRs. It does not merge them. Mailbox PRs are intended to remain open.
