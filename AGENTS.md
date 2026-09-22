# Agent operating instructions

This repository uses Zerion's repository-first coordination model.

Before substantive work:

1. read the relevant project file under `coordination/projects/`;
2. read your agent file under `coordination/agents/`;
3. inspect the current mailbox assignment;
4. read project-specific canonical state and recent relevant PRs;
5. verify that no terminal result or conflicting ACK already exists for the task.

Repository state is authoritative over remembered conversational context.

Do not perform substantive work on mailbox branches. Create a task branch and task PR. Report the exact commit/PR and verification evidence back to the mailbox.
