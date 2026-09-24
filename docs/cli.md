# Maestaris CLI

The CLI is optional and intentionally small.

AI workers do not need it to operate Maestaris.

## Install

```bash
python -m pip install -e .
```

In a restricted environment with dependencies already available:

```bash
python -m pip install --no-build-isolation -e .
```

## Initialize static configuration

```bash
maestaris init my-project \
  --workers theory implementation audit \
  --repository owner/repository
```

If `--repository` is omitted, Maestaris tries to infer the GitHub repository from the local `origin` URL without contacting GitHub.

## Validate

```bash
maestaris validate
```

Validation covers static protocol topology. Live task correctness is validated through GitHub Issue/comment workflows.

## Status

```bash
maestaris status
```

This reports static project registration only and explicitly points users to GitHub for live task state.
