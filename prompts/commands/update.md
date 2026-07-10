# /update — Batch Update Tasks, Projects, and Streams from Natural Language

You are a project management assistant. Apply updates to one or more tasks, projects, or streams based on natural language input.

## Arguments

The user will describe changes in plain language:
- "Move ALPHA-BE-001 to in-progress"
- "Reassign ALPHA-002 to Carlos, raise priority to high"
- "Set ALPHA-BE-001 due date to next Friday"
- "Add tag 'urgent' to ALPHA-BE-001 and ALPHA-002"
- "ALPHA-BE-001: blocked — waiting on API credentials"
- "ALPHA-BE-003 is blocked by ALPHA-BE-001"
- "Remove dependency on ALPHA-001 from ALPHA-BE-003"
- "Set the owner of project alpha to Ana" (project owner)
- "Make Ana and Bob co-owners of the backend stream in project alpha" (stream co-owners)
- "Put project beta on hold" (project status)

## Instructions

### Step 1 — Read conventions and context

1. Read `CLAUDE.md` for conventions (statuses, priorities, date format, file locations).
2. Read `data/team/*.md` files to match owner names (use `first_name` for matching).

### Step 2 — Parse input

First, determine the **target type** for each requested change:
- **Task** — the user names a task ID (e.g., `ALPHA-BE-001`) or clearly refers to a task.
- **Project** — the user names a project (e.g., "project alpha") and no task ID.
- **Stream** — the user names a stream within a project (e.g., "the backend stream in project alpha").

Then extract:
- **Target(s)**: which task(s), project(s), or stream(s) to update
- **Field changes**: what to change on each target

Supported fields for **tasks**:
- `status`: must be one of `todo`, `in-progress`, `blocked`, `done`
- `priority`: must be one of `critical`, `high`, `medium`, `low`
- `owners`: list of team member `first_name` values. Self-references ("me", "my", "myself") resolve to the current user. When assigning multiple owners and `completion_mode` is not specified, ask: "Should this task be done when any one person completes it (`any`), or does each person need to complete it independently (`all`)?" Update `completion_mode` accordingly.
- `due_date`: parse relative dates ("Friday" -> next Friday, "next week" -> next Monday). Format as YYYY-MM-DD.
- `tags`: append new tags to existing list (do not remove existing tags)
- `blocked_by`: add or remove task IDs from the dependency list. Verify referenced IDs exist before adding. When removing, also check if this resolves all dependencies and suggest unblocking.
- **Update note**: if the user provides context (e.g., "blocked — waiting on X"), add it under `### Updates`

Supported fields for **projects** and **streams**:
- `owners`: list of team member `first_name` values (co-ownership = multiple names). Self-references resolve to the current user. Projects/streams have **no** `completion_mode` — do not ask about it. Use `owners: []` for unassigned.
- `status`: must be one of `active`, `on-hold`, `completed`.
- **Update note**: if the user provides context, add it under `### Updates`.

### Step 3 — Find and update each target

**For each task ID:**

1. **Find the task file** by scanning `data/projects/**/tasks/**/*.md` and `data/tasks/**/*.md` for a file whose YAML front matter contains a matching `id` field.
2. **If not found**: tell the user the task ID was not found and skip it.
3. **If found**:
   - Apply the requested changes to the YAML front matter
   - If reassigning `owners`, verify each name matches a team member in `data/team/*.md`. If any name doesn't match, ask the user.
   - If changing `status` to `done`, also set `completed_date` to today's date (YYYY-MM-DD)
   - If adding an update note, append under `### Updates` following the **Same-Day Updates** convention in `CLAUDE.md`:
     - If no entry exists for today's date: add `- YYYY-MM-DD: <note>`
     - If a single-line entry for today already exists: convert it to the grouped format and add the new note as a sub-bullet
     - If a grouped entry for today already exists: append the new note as a sub-bullet
   - If no `### Updates` section exists, create one at the end of the file

**For each project or stream:**

1. **Find the file**:
   - Project: `data/projects/<slug>/project.md` (match the named project to an existing slug; if ambiguous, ask).
   - Stream: `data/projects/<slug>/streams/<stream-slug>/stream.md` (the stream must be identified within a specific project; if the project or stream is ambiguous, ask).
2. **If not found**: tell the user and skip it.
3. **If found**:
   - Apply the requested `owners` and/or `status` changes to the YAML front matter.
   - If reassigning `owners`, verify each name matches a team member in `data/team/*.md`. If any name doesn't match, ask the user.
   - If adding an update note, append it under `### Updates` following the **Same-Day Updates** convention (same rules as tasks above).

### Step 4 — Show summary

Show a summary table of all changes made:
- Columns: Target, Field, Old Value, New Value
- Target is the task ID, project name, or "project / stream" for a stream.

If any targets were not found, list them separately.

### If anything is ambiguous

- Which task, project, or stream? Ask the user.
- Which field to change? Ask the user.
- Owner name doesn't match any team member? Ask the user.

$ARGUMENTS
