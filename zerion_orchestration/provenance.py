from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

KINDS = {"raw", "derived", "metadata"}


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("provenance manifest must be a JSON object")
    return data


def validate_provenance(path: Path, *, verify_files: bool = True) -> list[str]:
    """Return validation errors for a schema-1 PROVENANCE.json manifest."""
    errors: list[str] = []
    try:
        data = _load(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)]

    if data.get("schema") != 1:
        errors.append("schema must be 1")

    source = data.get("source")
    if not isinstance(source, dict) or not source.get("commit"):
        errors.append("source.commit is required")

    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        return errors + ["artifacts must be a list"]

    base = path.parent.resolve()
    seen: set[str] = set()
    for index, item in enumerate(artifacts):
        prefix = f"artifacts[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        rel = item.get("path")
        digest = item.get("sha256")
        kind = item.get("kind")
        if not isinstance(rel, str) or not rel:
            errors.append(f"{prefix}.path is required")
            continue
        if rel in seen:
            errors.append(f"duplicate artifact path: {rel}")
        seen.add(rel)
        if kind not in KINDS:
            errors.append(f"{prefix}.kind must be raw, derived, or metadata")
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append(f"{prefix}.sha256 must be a 64-character digest")
            continue
        try:
            int(digest, 16)
        except ValueError:
            errors.append(f"{prefix}.sha256 must be hexadecimal")
            continue

        target = (base / rel).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            errors.append(f"{prefix}.path escapes the bundle root")
            continue
        if verify_files:
            if not target.is_file():
                errors.append(f"missing artifact: {rel}")
            else:
                actual = hashlib.sha256(target.read_bytes()).hexdigest()
                if actual.lower() != digest.lower():
                    errors.append(f"sha256 mismatch: {rel}")

    reproduce = data.get("reproduce")
    if reproduce is not None and (
        not isinstance(reproduce, dict) or not reproduce.get("command")
    ):
        errors.append("reproduce.command is required when reproduce is present")
    return errors
