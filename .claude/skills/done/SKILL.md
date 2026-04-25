---
name: done
description: Mark one or more plainpm tasks as complete. TRIGGER when the user references task IDs (matching `[A-Z]+(-[A-Z]+)?-\d{3}` such as `ALPHA-BE-001` or `TASK-001`) and signals completion — phrasings like "mark <ID> done", "<ID> done", "I finished <ID>", "completed <ID>", "close <ID>", "done with <ID>", "<ID> — deployed/shipped/resolved", or "<ID> — resolution: ...". Multi-task completions like "mark ALPHA-001 and ALPHA-002 as done" also TRIGGER. The skill handles `completion_mode: all` partial completions and notifies about unblocked downstream tasks. SKIP for general status changes that aren't completion (use `update`). SKIP for archive/cleanup of already-done tasks (use `archive`).
---

Read and follow the instructions in `prompts/commands/done.md` exactly.
