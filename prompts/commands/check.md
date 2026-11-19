# /check — Data Quality Check

You are a project management assistant. Validate every plainpm data file and help the user fix what's wrong.

## Instructions

1. Check if the `data/` directory exists. If it does NOT, tell the user there is nothing to check yet (see `CLAUDE.md` for setup).

2. Run the check script:

   ```
   python scripts/dashboard.py check
   ```

   The script is read-only and does **not** save a snapshot to `data/reports/`. It scans every task (including archived tasks), project, stream, team member, area, and note under `data/` (skipping `data/reports/` and raw transcripts), and exits with code 1 when it finds errors.

3. Display the full output as-is — it is already formatted as markdown.

4. If it found problems, propose a concrete fix for each one (or for each group of similar ones), e.g. "set `completed_date: 2026-11-18` on ALPHA-BE-001", "change owner `ana` → `Ana` in ALPHA-002", "add `project-beta` to `data/projects/_index.md`". When it isn't obvious, say briefly why the problem matters:
   - **Errors** break dashboards or commands — a task silently missing from reports, an ambiguous owner, an ID that collides with another task.
   - **Warnings** are inconsistencies worth a look — a project past its target date that still says on-track, a task still `blocked` after its blockers closed, a typo'd field name.

5. **Do not change any file until the user approves.** Ask which fixes to apply (all, some, or none). Ask instead of guessing when a fix needs a decision:
   - **Missing or invalid dates** (`completed_date`, `cancelled_date`, `due_date`, …): ask for the real date. Use a date from the task's `### Updates` only when an entry clearly records that event.
   - **Duplicate task IDs**: ask which task keeps the ID. Give the other one the next free ID in its scope (scan active **and** archived tasks), rename its file to match, and update every `blocked_by` that referenced the old ID and meant this task.
   - **Health, target dates, and status**: these are the user's judgment — ask, never pick a value yourself.
   - **Owners that don't match the roster**: offer the closest `first_name` match, or adding the person to `data/team/`.

6. After applying fixes, run `python scripts/dashboard.py check` again and show the new result.

## What it checks

- **File syntax**: missing front matter, byte-order marks, multi-line YAML (plainpm only reads inline values like `[a, b]`), duplicate fields, unknown fields (likely typos), malformed `links`.
- **Allowed values**: task `status`, `priority`, `completion_mode`; project/stream `status` and `health`; every date is a real `YYYY-MM-DD`.
- **Status ↔ dates**: `done` needs `completed_date`, `cancelled` needs `cancelled_date`; leftover dates on reopened tasks; `start_date` after `due_date` (or after `target_date`); future completion dates.
- **People**: every owner matches a team member's `first_name` (with a "did you mean" hint); legacy `owner` fields; duplicate first names; more than one `self: true`.
- **Location**: a task's `project`/`stream` matches the folder it lives in; task files in the wrong place (notes folders, outside any `tasks/` folder); project/stream/area folders missing their definition file; `_index.md` in sync with the projects.
- **IDs**: format, prefix matching the task's scope, file name matching the ID, duplicate IDs across active and archived tasks, mixed prefixes within a project.
- **Dependencies**: `blocked_by` pointing to unknown tasks or to itself, dependency cycles, cancelled blockers, tasks still `blocked` after every blocker closed.
- **Multi-owner tasks**: `completions` matches `owners` for `completion_mode: all`, and agrees with `status`.
- **Schedule**: projects/streams past their `target_date` and not completed (flagging a stale `on-track`), a stream ending after its project, open tasks due after their stream's or project's target date, open tasks in completed projects/streams.
- **References**: `source_meeting` / `source_transcript` files exist; notes reference existing areas, projects, and streams.

$ARGUMENTS
