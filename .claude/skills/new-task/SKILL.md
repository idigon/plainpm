---
name: new-task
description: Create a new plainpm task from natural language. TRIGGER when the user wants to create, add, or open a new task — phrasings like "create a task", "add a task", "new task for <Name>", "<Name> needs to <verb> by <date>", "I need to <verb> by <date>" (self-assignment), or any sentence that proposes work to be tracked with an owner and/or deadline. Also TRIGGER when the user describes a to-do that should be captured as a task in `data/projects/` or `data/tasks/`. SKIP if the sentence references an existing task ID (e.g. `ALPHA-BE-001`) — that is an `update` or `done` operation, not a new task. SKIP for meeting transcripts (use `process-meeting`) and for free-form notes/decisions (use `new-note`).
---

Read and follow the instructions in `prompts/commands/new_task.md` exactly.
