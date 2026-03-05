# /update — Batch Update Tasks from Natural Language

You are a project management assistant. Apply updates to one or more tasks based on natural language input.

## Arguments

The user will describe changes in plain language:
- "Move ALPHA-BE-001 to in-progress"
- "Reassign ALPHA-002 to Carlos, raise priority to high"
- "Set ALPHA-BE-001 due date to next Friday"
- "Add tag 'urgent' to ALPHA-BE-001 and ALPHA-002"
- "ALPHA-BE-001: blocked — waiting on API credentials"

## Instructions

### Step 1 — Read conventions and context

1. Read `CLAUDE.md` for conventions (statuses, priorities, date format, file locations).
2. Read `data/team/*.md` files to match owner names (use `first_name` for matching).

### Step 2 — Parse input

Extract from the user's input:
- **Task ID(s)**: which tasks to update
- **Field changes**: what to change on each task

Supported fields:
- `status`: must be one of `todo`, `in-progress`, `blocked`, `done`
- `priority`: must be one of `critical`, `high`, `medium`, `low`
- `owner`: match to a team member's `first_name`. Self-references ("me", "my", "myself") resolve to the current user — in solo mode (one team member), that's the only person; in team mode, resolve to the member with `self: true`. If no `self: true` exists, ask.
- `due_date`: parse relative dates ("Friday" -> next Friday, "next week" -> next Monday). Format as YYYY-MM-DD.
- `tags`: append new tags to existing list (do not remove existing tags)
- **Update note**: if the user provides context (e.g., "blocked — waiting on X"), add it under `### Updates`

### Step 3 — Find and update each task

For each task ID:

1. **Find the task file** by scanning `data/projects/**/tasks/**/*.md` for a file whose YAML front matter contains a matching `id` field.
2. **If not found**: tell the user the task ID was not found and skip it.
3. **If found**:
   - Apply the requested changes to the YAML front matter
   - If reassigning `owner`, verify the name matches a team member in `data/team/*.md`. If no match, ask the user.
   - If changing `status` to `done`, also set `completed_date` to today's date (YYYY-MM-DD)
   - If adding an update note, append under `### Updates` with today's date:
     ```
     - YYYY-MM-DD: <note>
     ```
   - If no `### Updates` section exists, create one at the end of the file

### Step 4 — Show summary

Show a summary table of all changes made:
- Columns: ID, Field, Old Value, New Value

If any task IDs were not found, list them separately.

### If anything is ambiguous

- Which task? Ask the user.
- Which field to change? Ask the user.
- Owner name doesn't match any team member? Ask the user.

$ARGUMENTS
