#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

if len(sys.argv) < 3:
    print("usage: bootstrap_project.py <project-name> <worker> [worker ...]")
    raise SystemExit(2)

project = sys.argv[1]
workers = sys.argv[2:]
valid = re.compile(r"^[a-z0-9][a-z0-9-]*$")
for value in [project, *workers]:
    if not valid.match(value):
        raise SystemExit(f"invalid name {value!r}: use lowercase letters, digits, and hyphens")

project_path = ROOT / "coordination" / "projects" / f"{project}.yaml"
if project_path.exists():
    raise SystemExit(f"already exists: {project_path}")

project_yaml = f"""schema: 1
project: {project}
title: {project.replace('-', ' ').title()}
status: active
repository: owner/repository
runtime: runtime-defined

canonical_paths:
  - README.md

orchestrator: orchestrator
auditor: {workers[-1] if workers else 'null'}

active_workers:
""" + "".join(f"  - {w}\n" for w in workers) + """dormant_workers: []

mailboxes:
""" + "".join(f"  {w}: null\n" for w in workers)

project_path.write_text(project_yaml)

for i, worker in enumerate(workers):
    agent_path = ROOT / "coordination" / "agents" / f"{worker}.yaml"
    if agent_path.exists():
        print(f"skip existing agent: {agent_path.name}")
        continue
    pool = "A" if i % 2 == 0 else "B"
    agent_path.write_text(f"""schema: 1
agent: {worker}
project: {project}
role: specialist
dispatcher_pool: {pool}
status: active

mailbox:
  transport: pull_request
  pr: null

project_paths:
  - .

current_task: null
current_objective: null
""")
    marker = ROOT / "coordination" / "mailboxes" / f"{worker}.md"
    marker.write_text(f"# Mailbox marker: {worker}\n")

print(f"bootstrapped project {project} with {len(workers)} worker(s)")
print("next: create one draft mailbox PR per worker and record its PR number")
