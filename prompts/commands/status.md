# /status — Project Status Report

You are a project management assistant. Generate a status report for one or all projects.

## Arguments

Optional: a project name or slug. If not provided, show summary for all projects.

## Instructions

1. Read `CLAUDE.md` for conventions.
2. Read `projects/_index.md` for the project list.

### If a specific project is provided:

3. Read `projects/<slug>/project.md` for overview, goals, key dates.
4. Scan all streams in `projects/<slug>/streams/*/stream.md`.
5. Scan all tasks across all year subfolders (project-level + all streams).
6. Generate a detailed report:

```
# 📈 Status Report: [Project Name]
**Status**: active | on-hold | completed
**Last updated**: [today]

## Overview
[From project.md]

## Task Summary
| Status | Count |
|--------|-------|
| Todo | X |
| In Progress | X |
| Blocked | X |
| Done | X |

## Streams

### [Stream Name] (status)
**Tasks**: X open / Y total

| ID | Task | Owner | Priority | Status | Due |
|----|------|-------|----------|--------|-----|
...

### (Project-level tasks)
...

## Blockers & Risks
[List any blocked tasks with details]

## Recent Completions
[Tasks marked done in the last 7 days]
```

### If no project specified:

3. Show a summary across all projects:

```
# 📈 Portfolio Status

| Project | Status | Open Tasks | Blocked | Overdue |
|---------|--------|------------|---------|---------|
| Project Alpha | active | 5 | 1 | 0 |
| Project Beta | active | 3 | 0 | 2 |
```

Then for each project, show a brief breakdown:
- Number of tasks by status
- Any blocked or overdue tasks highlighted

$ARGUMENTS
