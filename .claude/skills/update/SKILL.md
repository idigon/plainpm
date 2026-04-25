---
name: update
description: Apply field changes to one or more existing plainpm tasks from natural language. TRIGGER when the user references one or more task IDs (matching `[A-Z]+(-[A-Z]+)?-\d{3}` such as `ALPHA-BE-001`, `ALPHA-002`, or `TASK-001`) together with a change to status, priority, owner, due date, tags, dependencies, or an update note. Examples: "Move ALPHA-BE-001 to in-progress", "ALPHA-001 is blocked", "reassign ALPHA-002 to Carlos", "set ALPHA-BE-001 due date to Friday", "ALPHA-BE-003 is blocked by ALPHA-BE-001", "add tag urgent to ALPHA-002". SKIP if the user is marking a task complete or closing it (use `done` instead). SKIP if the user is creating a new task (use `new-task`).
---

Read and follow the instructions in `prompts/commands/update.md` exactly.
