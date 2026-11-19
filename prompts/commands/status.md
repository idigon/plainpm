# /status — Project Status Report

You are a project management assistant. Generate a status report for one or all projects.

## Arguments

Optional: a project name or slug. If not provided, show summary for all projects.

## Definitions

- **Open** tasks: `todo`, `in-progress`, or `blocked`. `done` and `cancelled` are closed.
- **Overdue**: an open task whose `due_date` is before today.
- **Progress**: done ÷ (all tasks − cancelled), shown as `60% (6/10)`. Include the project's archived tasks in `data/archive/<slug>/` so archiving doesn't change progress. Show `—` when there are no tasks.
- **Health** (`on-track` | `at-risk` | `off-track`) is set by the user — report it, never infer or change it. Display as icon + label: 🟢 on-track, 🟡 at-risk, 🔴 off-track; `Not set` when empty.
- **Late**: a project/stream whose `target_date` is before today and whose status isn't `completed` — mark the target date with ⚠️. If a late project or stream still says `on-track`, point out the mismatch in Blockers & Risks.

## Instructions

1. Read `CLAUDE.md` for conventions.
2. Read `data/projects/_index.md` for the project list.

### If a specific project is provided:

3. Read `data/projects/<slug>/project.md` for overview, goals, key dates, health, and start/target dates.
4. Scan all streams in `data/projects/<slug>/streams/*/stream.md`.
5. Scan all tasks across all year subfolders (project-level + all streams), plus `data/archive/<slug>/**` for the progress figures.
6. Run the timeline script and keep its output for the Timeline section:

   ```
   python scripts/dashboard.py timeline <slug>
   ```

   It prints a Mermaid Gantt chart (project window and target milestone, a bar per stream, a bar per task from `start_date`/`created` to `due_date`) plus notes about anything it couldn't place. It also saves a snapshot to `data/reports/timeline/YYYY/MM/`.
7. Generate a detailed report:

```
# 📈 Status Report: [Project Name]
**Status**: active | on-hold | completed
**Health**: [🟢 on-track | 🟡 at-risk | 🔴 off-track | Not set]
**Dates**: [start_date or "?"] → [target_date or "?"] (⚠️ on the target if late; "Not set" if neither)
**Progress**: [X% (done/total)]
**Owner**: [owners joined with " / ", or "Unassigned"]
**Last updated**: [today]

## Overview
[From project.md]

## Timeline
[The ```mermaid block and the notes below it, copied exactly from the timeline script output]

## Task Summary
| Status | Count |
|--------|-------|
| Todo | X |
| In Progress | X |
| Blocked | X |
| Done | X |
| Cancelled | X |

## Streams

### [Stream Name] (status)
**Owner**: [stream owners joined with " / ", or "Unassigned"]
**Health**: [...] | **Dates**: [start → target] | **Progress**: [X% (done/total)]
**Tasks**: X open / Y total (excluding cancelled)

| ID | Task | Owner | Priority | Status | Start | Due |
|----|------|-------|----------|--------|-------|-----|
...

### (Project-level tasks)
...

## Blockers & Risks
[Blocked tasks with details; overdue tasks; late streams/project; any late entity still marked on-track]

## Recent Completions
[Tasks marked done in the last 7 days]

## Recently Cancelled
[Tasks cancelled in the last 7 days, with the reason from their latest update — omit this section if there are none]
```

### If no project specified:

3. Show a summary across all projects:

```
# 📈 Portfolio Status

| Project | Owner | Status | Health | Target | Progress | Open Tasks | Blocked | Overdue |
|---------|-------|--------|--------|--------|----------|------------|---------|---------|
| Project Alpha | Alice | active | 🟡 at-risk | 2026-12-15 | 40% (4/10) | 5 | 1 | 0 |
| Project Beta | Alice / Bob | active | 🟢 on-track | ⚠️ 2026-11-01 | 75% (3/4) | 1 | 0 | 2 |
```

4. Run `python scripts/dashboard.py timeline` (no slug) and include its output under a `## Portfolio Timeline` heading — one bar per project and stream that has a `target_date`.

Then for each project, show a brief breakdown:
- Number of tasks by status
- Any blocked or overdue tasks highlighted
- Late projects/streams, and any late one still marked on-track

$ARGUMENTS
