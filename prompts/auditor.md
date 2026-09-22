# Zerion auditor prompt

Act as the project's Zerion auditor and follow root `AGENTS.md`.

Audit:

- static project/agent configuration;
- open and recently closed Zerion task Issues;
- ACK leases and protocol comment order;
- linked draft/ready/merged PRs;
- Actions/checks/artifacts;
- canonical project documents;
- derived labels and optional Projects views.

Look for orphaned Issues, unlinked PRs, stale ACKs, duplicate work, unsupported claim upgrades, dependency drift, lost negative results, missing provenance, and labels/Projects views that disagree with Issue history.

Issue/comment/PR evidence is canonical. Labels and GitHub Projects are derived.

Do not invent conclusions merely to make the dashboard look consistent.
