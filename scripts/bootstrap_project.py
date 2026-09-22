#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from zerion_orchestration.cli import main

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: bootstrap_project.py <project-name> <worker> [worker ...]")
        raise SystemExit(2)
    raise SystemExit(
        main(
            [
                "--root", str(ROOT),
                "init", sys.argv[1],
                "--workers", *sys.argv[2:],
            ]
        )
    )
