# PM Vault — Conventions & Configuration

## Data Directory

All user data (projects, team, meetings, reports) lives in the `data/` subdirectory. This separation keeps framework files (scripts, templates, prompts, agent configs) apart from personal data, so the framework repo can be shared on GitHub without exposing private information.

**Setup options:**
- **Gitignore** (default) — `data/` is listed in `.gitignore`, so it won't be pushed to the shared repo. Use a separate backup method for your data.
- **Git submodule** — Point `data/` to a private repo: `git submodule add <your-private-repo-url> data`

If `data/` doesn't exist when a command runs, the agent will offer to create the directory structure for you.

## Team Roster

Team members are defined in `data/team/*.md` files. Each has `full_name`, `first_name`, and `role` in YAML front matter. Use first names for natural language matching.

**External people** (clients, vendors, stakeholders not in `data/team/`) are NOT tracked as task owners. Their action items appear in meeting notes only — never create task files for them.

## Tag Taxonomy

Tags are freeform strings in the `tags` array. Common categories:
- `planning`, `research`, `design`, `development`, `testing`, `deployment`
- `bug`, `feature`, `improvement`, `documentation`
- `stakeholder`, `customer`, `internal`

## Status Values

Task statuses: `todo` | `in-progress` | `blocked` | `done`
Project/stream statuses: `active` | `on-hold` | `completed`

## Priority Values

| Priority | Icon | Label |
|----------|------|-------|
| Critical | 🔴 | `critical` |
| High | 🟠 | `high` |
| Medium | 🟡 | `medium` |
| Low | 🟢 | `low` |

Always display priority as icon + string (e.g., "🟠 high").

## Task ID Convention

- **Stream-level tasks**: `PROJECT-STREAM-NNN` (e.g., `ALPHA-BE-001`)
- **Project-level tasks**: `PROJECT-NNN` (e.g., `ALPHA-001`)
- IDs use uppercase. Stream abbreviations are short (2-4 chars) derived from the stream folder name.
- NNN is zero-padded to 3 digits, auto-incremented per scope.

## Links

Projects, streams, tasks, and meeting notes all support a `links` array in front matter. Each link stores both display text and URL:

```yaml
links: [{label: "Jira ticket", url: "https://jira.example.com/ALPHA-123"}, {label: "Design doc", url: "https://docs.example.com/design"}]
```

- `label`: the text displayed in reports and dashboards (used as hyperlink text)
- `url`: the full URL

When rendering links in reports or dashboards, output them as markdown hyperlinks: `[label](url)`.

## Dates

- Format: `YYYY-MM-DD`
- `due_date`: optional — tasks can have no due date
- `completed_date`: set automatically when status changes to `done`
- `created`: set when task/project/stream is created

## Working Days Calculation

Working days = Mon–Fri only. Exclude weekends (Sat, Sun). No holiday calendar — just weekdays.
Used in `/my-team` to calculate "days open" for each task.

## Meeting Processing Rules

- `.vtt` files in `data/meetings/transcripts/` → parse transcript, generate structured notes
- `.md` files → process existing manual notes
- Cross-reference attendees with team roster (`data/team/*.md`)
- **Action items**: all listed in a single "Action Items" section (notes are shared with everyone, no team/external split)
- **Task creation**: only create task files for **team members'** action items — never for external attendees
- **If uncertain** whether someone is team or external: **ask the user** before proceeding
- **Completeness over brevity**: meeting notes are the permanent record. Capture all topics discussed, all decisions (with context), all concerns raised, and all open questions. A longer note that misses nothing is always better than a concise one that drops details.

## Date-Based Organization

Tasks are organized into **year** subfolders. Meeting notes, transcripts, and reports are organized into **year/month** subfolders. This keeps folders manageable as volume grows.

- Tasks: `tasks/YYYY/TASK-ID.md`
- Meeting transcripts: `data/meetings/transcripts/YYYY/MM/`
- Meeting notes: `data/meetings/notes/YYYY/MM/` or `data/projects/<slug>/meetings/YYYY/MM/`
- Reports: `data/reports/<type>/YYYY/MM/`

When creating new files, always place them in the correct subfolder matching the current date. Dashboard scripts use `rglob` and scan all subfolders automatically.

## File Locations

| Content | Location |
|---------|----------|
| Templates | `templates/` |
| Team members | `data/team/*.md` |
| Project index | `data/projects/_index.md` |
| Project files | `data/projects/<slug>/project.md` |
| Project-level tasks | `data/projects/<slug>/tasks/YYYY/*.md` |
| Stream definitions | `data/projects/<slug>/streams/<stream-slug>/stream.md` |
| Stream tasks | `data/projects/<slug>/streams/<stream-slug>/tasks/YYYY/*.md` |
| Meeting transcripts | `data/meetings/transcripts/YYYY/MM/` |
| Processed notes | `data/meetings/notes/YYYY/MM/` or `data/projects/<slug>/meetings/YYYY/MM/` |
| Dashboard reports | `data/reports/<type>/YYYY/MM/` |
| Slash commands | `.claude/commands/` |

## Project Slugs

Use lowercase-kebab-case for all folder names (e.g., `project-alpha`, `backend-api`).

## Dashboard Scripts

The four read-only dashboards are powered by `scripts/dashboard.py` (Python, stdlib only). This ensures speed, determinism, and no token cost for scanning tasks.

```
python scripts/dashboard.py today         # Daily dashboard
python scripts/dashboard.py this_week     # Weekly dashboard
python scripts/dashboard.py my_team       # Team workload + days open
python scripts/dashboard.py weekly_report # Week summary
```

The slash commands for these dashboards invoke the script and display its output.

Every run automatically saves a snapshot to `data/reports/`:

| Command | Saved to | Date key |
|---------|----------|----------|
| `today` | `data/reports/daily/YYYY/MM/YYYY-MM-DD.md` | Today |
| `this_week` | `data/reports/weekly/YYYY/MM/YYYY-MM-DD.md` | Monday of the week |
| `my_team` | `data/reports/team/YYYY/MM/YYYY-MM-DD.md` | Today |
| `weekly_report` | `data/reports/weekly-report/YYYY/MM/YYYY-MM-DD.md` | Monday of the week |

Running the same command twice on the same day overwrites the previous snapshot for that date.

## Commands

Command prompts live in `prompts/commands/`. Each file contains the full instructions for one command.

| Command | Prompt file | Purpose |
|---------|-------------|---------|
| today | `prompts/commands/today.md` | Daily dashboard |
| this_week | `prompts/commands/this_week.md` | Weekly dashboard |
| new-task | `prompts/commands/new_task.md` | Create task from natural language |
| process-meeting | `prompts/commands/process_meeting.md` | Process .vtt/.md into notes + tasks |
| status | `prompts/commands/status.md` | Project status report |
| my-team | `prompts/commands/my_team.md` | Team workload view |
| weekly-report | `prompts/commands/weekly_report.md` | Weekly summary |

In Claude Code these are also wired as slash commands via `.claude/commands/`.

## Multi-Agent Support

This project is configured to work with multiple AI coding agents:

| Agent | Config file |
|-------|------------|
| Claude Code | `CLAUDE.md` + `.claude/commands/` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Windsurf | `.windsurf/rules/plainpm.md` |
| Cursor | `.cursor/rules/plainpm.mdc` |
| Any agent | `AGENTS.md` |

All agent configs point to the same source of truth: `CLAUDE.md` for conventions, `prompts/commands/` for command prompts.
