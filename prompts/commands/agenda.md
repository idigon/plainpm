# /agenda — Generate Meeting Agenda from Open Tasks

You are a project management assistant. Generate a structured meeting agenda based on current task data.

## Arguments

The user may optionally specify a project:
- "Generate agenda for project-alpha"
- "Meeting agenda"
- "Agenda for project-beta"

If no project is specified, generate an agenda across all projects.

## Instructions

### Step 1 — Read conventions

1. Read `CLAUDE.md` for conventions (statuses, priorities, date format, file locations, working days calculation).

### Step 2 — Gather task data

Run `python scripts/dashboard.py today` to get a snapshot of current task state. Alternatively, read task files directly by scanning `data/projects/**/tasks/**/*.md` and `data/tasks/**/*.md`.

If a project was specified, scope to only that project's tasks. Otherwise, include all projects.

### Step 3 — Build agenda sections

Organize tasks into the following sections:

1. **Blockers** — all tasks with `status: blocked`
   - These need discussion to unblock. Include any update notes that explain the blocker.

2. **Overdue** — tasks with `due_date` before today and `status` not `done`
   - These need a status check. How far overdue? Still relevant?

3. **In Progress** — tasks with `status: in-progress`
   - Quick status round. Any risks or issues?

4. **Due This Week** — tasks with `due_date` within the current week (Mon-Sun) and `status` not `done`
   - Upcoming deadlines to be aware of.

5. **New / Unassigned** — tasks with `status: todo` and either no `owner` or recently created (within last 7 days)
   - Need assignment or prioritization discussion.

### Step 4 — Format output

For each section, list tasks with:
- Task ID
- Title
- Owner (or "Unassigned")
- Priority (with icon, e.g., "🟠 high")
- Due date (or "No due date")

Output as a markdown document with a header showing:
- Date of the agenda
- Project scope (specific project or "All Projects")

Example format:
```markdown
# Meeting Agenda — 2026-02-25

**Scope**: Project Alpha

---

## Blockers (2)

| ID | Task | Owner | Priority | Due |
|----|------|-------|----------|-----|
| ALPHA-BE-001 | Fix auth endpoint | Ana | 🟠 high | 2026-02-20 |

> Blocker note: Waiting on third-party API credentials

...
```

### Step 5 — Display only

Display the agenda to the user. Do **NOT** save to a file automatically. The user can copy/paste or ask to save it.

If there are no tasks in any section, show the section header with "None" so the user knows it was checked.

$ARGUMENTS
