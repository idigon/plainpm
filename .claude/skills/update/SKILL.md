---
name: update
description: Apply field changes to one or more existing plainpm tasks from natural language. TRIGGER when the user references one or more task IDs (matching `[A-Z]+(-[A-Z]+)?-\d{3}` such as `ALPHA-BE-001`, `ALPHA-002`, or `TASK-001`) together with a change to status, priority, owner, start or due date, tags, dependencies, or an update note — including cancelling a task. Also TRIGGER for changes to a project or stream's owner, status, health (on-track / at-risk / off-track), start date, or target date. Examples: "Move ALPHA-BE-001 to in-progress", "ALPHA-001 is blocked", "reassign ALPHA-002 to Carlos", "set ALPHA-BE-001 due date to Friday", "ALPHA-BE-004 starts Monday", "ALPHA-BE-003 is blocked by ALPHA-BE-001", "add tag urgent to ALPHA-002", "cancel ALPHA-002", "we're not doing ALPHA-BE-003 anymore", "drop TASK-004", "project alpha is at risk", "target date for the backend stream is Dec 15". SKIP if the user is marking a task complete (use `done` instead) — but cancelling/dropping a task is NOT completing it and stays here. SKIP if the user is creating a new task (use `new-task`).
---

Read and follow the instructions in `prompts/commands/update.md` exactly.
