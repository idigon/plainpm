# /done — Mark Task(s) as Done

You are a project management assistant. Mark one or more tasks as done.

## Arguments

The user will provide task ID(s) and an optional closing note:
- "ALPHA-BE-001"
- "ALPHA-BE-001, ALPHA-002"
- "ALPHA-BE-001 — deployed to production"
- "Mark ALPHA-BE-001 and ALPHA-002 as done"

## Instructions

### Step 1 — Read conventions

1. Read `CLAUDE.md` for conventions (statuses, completed_date format, file locations).

### Step 2 — Parse input

Extract from the user's input:
- **Task ID(s)**: one or more task IDs (e.g., `ALPHA-BE-001`, `ALPHA-002`)
- **Closing note** (optional): any additional text the user provides as a completion comment

### Step 3 — Find and update each task

For each task ID:

1. **Find the task file** by scanning `data/projects/**/tasks/**/*.md` for a file whose YAML front matter contains a matching `id` field.
2. **If not found**: tell the user the task ID was not found and skip it.
3. **If found**:
   - Set `status: done` in the front matter
   - Set `completed_date` to today's date (YYYY-MM-DD)
   - If the user provided a closing note, append it under the `### Updates` section with today's date:
     ```
     - YYYY-MM-DD: <closing note>
     ```
   - If no `### Updates` section exists, create one at the end of the file

### Step 4 — Check for unblocked tasks

After completing task(s), scan all open tasks for any that have the completed ID(s) in their `blocked_by` array. For each such task:
- Check if **all** IDs in its `blocked_by` are now `done`.
- If yes: notify the user that the task is now unblocked and suggest changing its status (e.g., "ALPHA-BE-003 is no longer blocked — move to todo/in-progress?").
- If no: mention that the task still has other unresolved dependencies.

### Step 5 — Show summary

Show the user a summary of what was updated:
- If **one task**: show the task ID, title, and completed_date
- If **multiple tasks**: show a table with columns: ID, Title, Completed Date
- If any downstream tasks were unblocked, list them

If any task IDs were not found, list them separately with a note.

$ARGUMENTS
