# Manual chat runtime

Zerion does not require autonomous scheduling.

A user can maintain one orchestrator conversation and one or more specialist conversations, using GitHub mailboxes for hand-offs.

At the start of each turn, the worker reconstructs state from its configuration, mailbox, canonical project files, recent task PRs, and CI rather than relying solely on prior chat context.
