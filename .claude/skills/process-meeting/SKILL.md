---
name: process-meeting
description: Convert a meeting transcript or raw notes file into structured plainpm meeting notes, action-item tasks, and cross-reference updates on related projects/streams/tasks. TRIGGER when the user references a `.vtt` transcript file (typically under `data/meetings/transcripts/`) or a `.md` raw-notes file and asks to process it — phrasings like "process this meeting", "process the transcript", "summarize meeting notes from <path>", "turn this transcript into notes", or simply pasting/pointing at a transcript path. Also TRIGGER when the user provides a long verbatim transcript-style block of dialogue and asks to extract structure from it. SKIP for short ad-hoc notes the user is dictating directly (use `new-note`). SKIP if the user only wants tasks created without notes (use `new-task` for each).
---

Read and follow the instructions in `prompts/commands/process_meeting.md` exactly.
