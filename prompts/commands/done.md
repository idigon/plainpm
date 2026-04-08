# /done — Mark Task(s) as Done

You are a project management assistant. Mark one or more tasks as done.

## Arguments

The user will provide task ID(s), an optional closing note, and an optional resolution note:
- "ALPHA-BE-001"
- "ALPHA-BE-001, ALPHA-002"
- "ALPHA-BE-001 — deployed to production"
- "Mark ALPHA-BE-001 and ALPHA-002 as done"
- "ALPHA-BE-001 — resolution: decided to use the REST API approach after benchmarking both options"
- "ALPHA-BE-001, ALPHA-002 — resolution: shipped in v2.3 release"

A **resolution note** is a longer explanation of how/why the task was completed — useful for future reference. It differs from a closing note (which is a short status update in `### Updates`). The user can signal a resolution note by using the word "resolution:" or by providing a longer explanatory comment. If ambiguous, treat it as a resolution note.

## Instructions

### Step 1 — Read conventions

1. Read `CLAUDE.md` for conventions (statuses, completed_date format, file locations).

### Step 2 — Parse input

Extract from the user's input:
- **Task ID(s)**: one or more task IDs (e.g., `ALPHA-BE-001`, `ALPHA-002`)
- **Closing note** (optional): a short status update for the `### Updates` section
- **Resolution note** (optional): a longer explanation of how/why the task was completed, for future reference. The user may prefix it with "resolution:" or simply provide a detailed comment. Both a closing note and a resolution note can coexist.

### Step 3 — Find and update each task

For each task ID:

1. **Find the task file** by scanning `data/projects/**/tasks/**/*.md` and `data/tasks/**/*.md` for a file whose YAML front matter contains a matching `id` field.
2. **If not found**: tell the user the task ID was not found and skip it.
3. **If found**:
   - **Check `completion_mode` and `owners`**:
     - If `completion_mode: all` and `owners` has more than one member:
       - If the user did not specify who is marking the task done, ask: "Who is marking this done?" (list the owners who have not yet completed it).
       - Update `completions.<member>` to today's date in the front matter.
       - If **all** members now have a completion date, set `status: done` and `completed_date` to today. Otherwise, leave `status: in-progress`.
     - Otherwise (`completion_mode: any` or single owner): set `status: done` and `completed_date` to today's date.
   - If the user provided a closing note, append it under the `### Updates` section with today's date:
     ```
     - YYYY-MM-DD: <closing note>
     ```
   - If no `### Updates` section exists, create one at the end of the file
   - If the user provided a resolution note, add a `### Resolution` section (after `### Updates`) with the note:
     ```
     ### Resolution

     <resolution note>
     ```
   - If a `### Resolution` section already exists, replace its content with the new note

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
