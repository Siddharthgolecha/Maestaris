#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import tomllib


root = Path(__file__).resolve().parents[1]
with (root / "pyproject.toml").open("rb") as handle:
    version = tomllib.load(handle)["project"]["version"]

changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
heading = re.compile(rf"^##\s+{re.escape(version)}\s*$", re.MULTILINE)
if not heading.search(changelog):
    raise SystemExit(
        f"CHANGELOG.md has no release heading for pyproject version {version}"
    )

print(version)
