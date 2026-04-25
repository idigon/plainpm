---
name: archive
description: Move completed plainpm tasks older than a threshold (default 30 days) from active project/standalone folders to `data/archive/`. TRIGGER when the user explicitly asks to archive completed work — phrasings like "archive completed tasks", "archive tasks older than <N> days", "archive <project>", "archive <project> tasks older than <N> days", or "clean up old completed tasks". The skill always shows a preview table and asks for confirmation before moving files. SKIP if the user wants to delete or remove tasks — archive is move-only and never destroys files. SKIP for archiving projects/streams themselves (this skill only handles task files).
---

Read and follow the instructions in `prompts/commands/archive.md` exactly.
