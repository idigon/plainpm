---
name: new-note
description: Create a free-form plainpm note attached to a meeting area, project, or stream — used for decisions, observations, or context that isn't tied to a meeting transcript. TRIGGER when the user wants to record a note — phrasings like "add a note to the <area> area", "note in project <X>: ...", "<area> note: ...", "note for project <X> <stream> stream: ...", "write a note about ...", "team management note: ...", or any sentence asking to capture information against a project/stream/area. The skill places the note under `notes/YYYY/MM/` of the target context and may propose cross-reference updates and action-item tasks. SKIP if the input is clearly a task assignment with an owner/deadline (use `new-task`). SKIP if the input is a meeting transcript or `.vtt`/raw-notes file (use `process-meeting`).
---

Read and follow the instructions in `prompts/commands/new_note.md` exactly.
