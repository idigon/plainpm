# /archive — Archive Closed Tasks

You are a project management assistant. Move closed tasks (done or cancelled) older than a threshold to the archive directory.

## Arguments

The user may optionally specify:
- A number of days: "archive tasks done more than 30 days ago"
- A specific project: "archive project-alpha"
- Both: "archive project-alpha tasks older than 14 days"
- Nothing: defaults to all projects, 30 days

## Instructions

### Step 1 — Read conventions

1. Read `CLAUDE.md` for conventions (statuses, file locations, date format).

### Step 2 — Find closed tasks to archive

1. Scan `data/projects/**/tasks/**/*.md` and `data/tasks/**/*.md` for all task files.
2. For each task, check:
   - `status` is `done` with a `completed_date` older than the threshold (default: 30 days), **or**
   - `status` is `cancelled` with a `cancelled_date` older than the threshold
3. If a project was specified, scope to only that project's tasks.

### Step 3 — Show preview and confirm

Before moving any files, show the user a table of tasks that will be archived:

| ID | Task | Project | Status | Closed | Days Ago |
|----|------|---------|--------|--------|----------|

`Closed` is the `completed_date` (done) or `cancelled_date` (cancelled).

Then ask for confirmation before proceeding.

### Step 4 — Move tasks to archive

For each confirmed task:

1. Determine the archive path:
   - Project tasks: `data/archive/<project-slug>/YYYY/<TASK-ID>.md`
   - Standalone tasks: `data/archive/_standalone/YYYY/<TASK-ID>.md`
   - `YYYY` is the year from the task's `completed_date` (done) or `cancelled_date` (cancelled)
   - Create directories if they don't exist
2. Move the file from its current location to the archive path.
3. The task file content stays unchanged — no modifications to front matter.

Archived tasks disappear from the dashboards' task lists, but they still count toward project and stream **progress**, and their IDs are never reused.

### Step 5 — Show summary

Show the user:
- Number of tasks archived
- Archive location(s)
- If no tasks matched the criteria, say so

### Step 6 — Validate

Run `python scripts/dashboard.py check`. If it reports errors or warnings in any file you moved, fix them before finishing (ask the user when a fix needs a decision). Don't touch other files — if the check reports issues elsewhere, just mention how many and suggest `/check`.

$ARGUMENTS
