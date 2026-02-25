# PM Vault — Instructions

A complete guide to using your markdown-based project management system. Covers both slash commands (automated) and manual operations.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Slash Commands (Automated)](#slash-commands)
3. [Managing Projects](#managing-projects)
4. [Managing Streams](#managing-streams)
5. [Managing Tasks](#managing-tasks)
6. [Managing Team Members](#managing-team-members)
7. [Meeting Processing](#meeting-processing)
8. [Dashboards & Reports](#dashboards--reports)
9. [Day-to-Day Workflows](#day-to-day-workflows)
10. [File Reference](#file-reference)

---

## Getting Started

### Opening the vault

Open your AI coding agent from the project root directory so it picks up the configuration automatically:

- **Claude Code**: `cd plainpm && claude` (reads `CLAUDE.md` + `.claude/commands/`)
- **VS Code + Copilot**: open the `plainpm/` folder (reads `.github/copilot-instructions.md`)
- **Windsurf**: open the `plainpm/` folder (reads `.windsurf/rules/plainpm.md`)
- **Cursor**: open the `plainpm/` folder (reads `.cursor/rules/plainpm.mdc`)

### Data directory setup

All user data lives in the `data/` subdirectory. If it doesn't exist yet, any write command (`/new-task`, `/process-meeting`) will offer to create it for you.

To set it up manually:
```
mkdir -p data/projects data/team data/meetings/transcripts data/meetings/notes data/reports
```

**Privacy options:**
- **Gitignore** (default) — `data/` is in `.gitignore`, so it won't be pushed to the shared repo. Use a separate backup method.
- **Git submodule** — Point `data/` to a private repo: `git submodule add <your-private-repo-url> data`

### First-time setup

1. **Create the data directory** — run any command or create it manually (see above).
2. **Add your team members** — create one file per person in `data/team/` (see [Managing Team Members](#managing-team-members)).
3. **Create your first project** — use the "new task" command or create it manually (see [Managing Projects](#managing-projects)).
4. **Run the "today" dashboard** to verify everything works.

---

## Commands

Command prompts are in `prompts/commands/`. In Claude Code, these are wired as `/slash-commands`. In other agents, ask for them by name (e.g., "run today dashboard", "create a new task", "process this meeting").

| Command | Prompt file | What it does |
|---------|-------------|-------------|
| today | `prompts/commands/today.md` | Daily dashboard — overdue, due today, in-progress, blocked |
| this_week | `prompts/commands/this_week.md` | Weekly dashboard — all projects, streams, and tasks in tables |
| my-team | `prompts/commands/my_team.md` | Team workload — tasks per person with days-open count |
| weekly-report | `prompts/commands/weekly_report.md` | Week summary — completed, in-progress, blocked, new tasks |
| new-task | `prompts/commands/new_task.md` | Create a task from natural language |
| process-meeting | `prompts/commands/process_meeting.md` | Process a .vtt transcript or .md notes into structured notes + tasks |
| status | `prompts/commands/status.md` | Project status report (one project or all) |

### new-task

Describe what you need in plain language. Examples:

```
"Ana needs to fix the login bug in project alpha backend by Friday"
"Create a task for Carlos: review design mockups, high priority, project beta design stream"
"Update the API docs for project alpha, low priority"
```

The command will:
- Match names to team members
- Match project/stream names to existing ones
- Generate the next task ID
- Create the file in the right location
- Ask you to clarify anything ambiguous

### process-meeting

Provide a file path to a `.vtt` transcript or `.md` meeting notes:

```
"Process meeting data/meetings/transcripts/2026/2026-02-19-sprint-review.vtt"
"Process meeting data/meetings/notes/2026/draft-kickoff.md"
```

The command will:
- Parse the content and generate structured meeting notes
- Identify attendees (team vs. external)
- Create task files for every team member action item
- List external attendees' action items in the notes only (no task files)
- Ask you about anything unclear

### status

```
"Project status for project-alpha"    # Detailed report for one project
"Portfolio status"                    # Summary across all projects
```

---

## Managing Projects

### Creating a new project

**Option A — Via the new-task command**: If you create a task for a project that doesn't exist yet, the command will offer to create the project for you.

**Option B — Manually**:

1. Choose a slug (lowercase-kebab-case): e.g., `project-alpha`
2. Create the folder structure:
   ```
   data/projects/project-alpha/
   ├── project.md
   ├── tasks/
   │   └── 2026/               # Year subfolder for tasks
   ├── streams/
   └── meetings/
       └── 2026/               # Year subfolder for meeting notes
   ```
3. Write `project.md` using the template:
   ```yaml
   ---
   type: project
   status: active
   summary: Brief one-line summary of the project
   created: 2026-02-19
   links: []
   ---

   ## Project Alpha

   ### Overview
   What this project is about.

   ### Goals
   - Goal 1
   - Goal 2

   ### Key Dates
   - Kickoff: 2026-02-01
   - Target launch: 2026-06-01
   ```
4. Add an entry to `data/projects/_index.md`:
   ```
   | Project Alpha | active | `data/projects/project-alpha/` |
   ```

### Adding links to a project

Edit `project.md` front matter:
```yaml
links: [{label: "Jira board", url: "https://jira.example.com/ALPHA"}, {label: "Confluence space", url: "https://confluence.example.com/alpha"}]
```

The `label` is the display text used in reports (rendered as `[label](url)`).

### Putting a project on hold

Edit `project.md` front matter:
```yaml
status: on-hold
```
Update the status column in `data/projects/_index.md` to match.

### Completing a project

Edit `project.md` front matter:
```yaml
status: completed
```
Update `data/projects/_index.md`. Completed tasks within the project remain as-is for historical record.

### Archiving a project

There is no archive mechanism — just set status to `completed`. The project folder stays in place. Dashboard scripts skip `done` tasks but still list the project.

---

## Managing Streams

### Adding a stream to a project

1. Choose a slug: e.g., `backend-api`
2. Create the folder:
   ```
   data/projects/project-alpha/streams/backend-api/
   ├── stream.md
   └── tasks/
       └── 2026/               # Year subfolder for tasks
   ```
3. Write `stream.md`:
   ```yaml
   ---
   type: stream
   project: project-alpha
   status: active
   summary: API migration and new endpoint development
   created: 2026-02-19
   links: []
   ---

   ## Backend API

   ### Overview
   What this stream covers.

   ### Owner
   Ana
   ```

### Stream abbreviations for task IDs

The task ID includes a short abbreviation of the stream name. Derive it from the folder name — uppercase first letters of each word, 2-4 chars:

| Stream folder | Abbreviation |
|---------------|-------------|
| `backend-api` | `BE` |
| `frontend` | `FE` |
| `design` | `DES` |
| `data-pipeline` | `DP` |
| `mobile-app` | `MA` |
| `qa-testing` | `QA` |

### Putting a stream on hold / completing it

Edit `stream.md` front matter:
```yaml
status: on-hold    # or: completed
```

---

## Managing Tasks

### Creating a task (automated)

Use the new-task command with a natural language description (see above).

### Creating a task (manually)

1. Determine the task ID:
   - Look at existing task files across ALL year subfolders in the target directory
   - Increment the highest NNN by 1, zero-padded to 3 digits
   - Stream task: `PROJECT-STREAM-NNN` (e.g., `ALPHA-BE-002`)
   - Project-level task: `PROJECT-NNN` (e.g., `ALPHA-003`)

2. Create the file in the current year subfolder:
   - Stream task: `data/projects/project-alpha/streams/backend-api/tasks/2026/ALPHA-BE-002.md`
   - Project-level task: `data/projects/project-alpha/tasks/2026/ALPHA-003.md`

3. Use this structure:
   ```yaml
   ---
   id: ALPHA-BE-002
   type: task
   project: project-alpha
   stream: backend-api
   owner: Ana
   status: todo
   priority: medium
   due_date: 2026-03-01
   created: 2026-02-19
   completed_date:
   tags: [development]
   links: []
   source_meeting:
   ---

   ## Fix rate limiting on API gateway

   The gateway currently allows unlimited requests. Implement rate limiting
   per API key with configurable thresholds.

   ### Updates
   ```

### Completing a task

Edit the task file's front matter — change **both** fields:
```yaml
status: done
completed_date: 2026-02-19
```

The `completed_date` is what dashboards use to track when work was finished. Always set it to the actual completion date.

### Blocking a task

```yaml
status: blocked
```

Optionally add a note under `### Updates` explaining what's blocking it:
```markdown
### Updates
- 2026-02-19: Blocked — waiting on third-party API credentials from vendor
```

### Unblocking a task

Change status back to the appropriate value:
```yaml
status: in-progress    # or: todo
```

### Starting work on a task

```yaml
status: in-progress
```

### Changing priority

```yaml
priority: high    # critical | high | medium | low
```

### Reassigning a task

Change the `owner` field to another team member's `first_name`:
```yaml
owner: Carlos
```

### Adding or changing a due date

```yaml
due_date: 2026-03-15
```

To remove a due date, clear the value:
```yaml
due_date:
```

### Adding tags

```yaml
tags: [development, bug, urgent]
```

### Adding links to a task

```yaml
links: [{label: "PR #42", url: "https://github.com/org/repo/pull/42"}, {label: "Figma mockup", url: "https://figma.com/file/abc"}]
```

Each link has a `label` (display text for reports) and `url`. Useful for linking to PRs, design files, Jira tickets, documents, etc.

### Logging updates on a task

Add dated entries under the `### Updates` section:
```markdown
### Updates
- 2026-02-19: Started investigation, root cause identified in auth middleware
- 2026-02-20: Fix implemented, PR opened
- 2026-02-21: PR merged, deployed to staging
```

### Linking a task to a meeting

If the task came from a meeting, set:
```yaml
source_meeting: data/meetings/notes/2026/2026-02-19-sprint-review.md
```

This is set automatically by the process-meeting command but can be added manually too.

---

## Managing Team Members

### Adding a team member

Create a file in `data/team/` named after the person (lowercase-kebab-case), using the template `templates/team-member.md`:

`data/team/ana-garcia.md`:
```yaml
---
type: team-member
full_name: Ana Garcia
first_name: Ana
role: Backend Developer
---

## Notes

Prefers async communication. Expert in Go and PostgreSQL.
Handles most of the API design work for Project Alpha.
```

The `first_name` is used for matching in natural language commands and as the `owner` value in tasks. Keep it unique across the team.

The `## Notes` section is freeform — use it for anything worth remembering about the person: working style, expertise, preferences, availability, etc.

### Removing a team member

Delete their file from `data/team/`. Their existing tasks will remain but won't appear under any team member in the my-team dashboard (they'll show under "Unassigned" unless you reassign them first).

**Before removing**, consider reassigning their open tasks:
1. Search for tasks with `owner: TheirFirstName`
2. Change the owner to someone else or leave blank for unassigned

### Updating a team member's role

Edit their file's front matter:
```yaml
role: Senior Backend Developer
```

### About yourself

Create a team file for yourself too. This way, tasks assigned to you show up in the my-team dashboard and the process-meeting command can create tasks for your action items.

---

## Meeting Processing

### Workflow with transcripts (.vtt)

1. After a meeting, save the `.vtt` transcript to `data/meetings/transcripts/YYYY/`
   - Name it descriptively: `2026-02-19-sprint-review.vtt`
2. Ask your agent to process the meeting: "Process meeting data/meetings/transcripts/2026/2026-02-19-sprint-review.vtt"
3. The agent will:
   - Parse the transcript
   - Generate structured notes
   - Identify team members vs. external attendees
   - Create task files for team members' action items (in the current year subfolder)
   - Save notes to `data/meetings/notes/YYYY/` or `data/projects/<slug>/meetings/YYYY/`
4. Review the output and confirm

### Workflow with manual notes (.md)

1. Write your meeting notes as a `.md` file (anywhere — desktop, temp folder, etc.)
2. Ask your agent to process the meeting: "Process meeting path/to/your/notes.md"
3. The agent will restructure the notes and extract action items

### Writing meeting notes directly

If you prefer to write notes directly in the vault without processing:

`data/meetings/notes/2026/2026-02-19-sprint-review.md`:
```yaml
---
type: meeting
date: 2026-02-19
project: project-alpha
attendees: [Ana, Carlos, You]
links: [{label: "Recording", url: "https://zoom.us/rec/abc"}, {label: "Slide deck", url: "https://docs.google.com/presentation/d/xyz"}]
source_transcript:
---

## Sprint Review — Feb 19

### Summary
Reviewed sprint progress. Backend API on track, design needs another week.

### Decisions
- Push design deadline to Feb 28
- Prioritize auth endpoint fix

### Action Items
- **Ana**: Fix auth endpoint by Friday → `ALPHA-BE-001`
- **Carlos**: Update design mockups by next Wednesday
- **ClientName**: Send updated requirements document

### Notes
General discussion about Q2 roadmap priorities.
```

Then create the corresponding task files manually if needed.

### Where meeting notes are saved

- Project-specific meetings: `data/projects/<slug>/meetings/YYYY/`
- General / cross-project meetings: `data/meetings/notes/YYYY/`

---

## Dashboards & Reports

### Running dashboards

All four dashboards are script-powered for speed and consistency:

| Command | What it shows |
|---------|--------------|
| today | Overdue, due today, in-progress, blocked tasks |
| this_week | All projects/streams/tasks in table format |
| my-team | Tasks grouped by team member with days-open count |
| weekly-report | Completed, in-progress, blocked, new tasks this week |

### Saved snapshots

Every dashboard run saves a snapshot to `data/reports/`:

```
data/reports/
├── daily/2026/2026-02-19.md              ← /today
├── weekly/2026/2026-02-16.md             ← /this_week (Monday date)
├── team/2026/2026-02-19.md               ← /my-team
└── weekly-report/2026/2026-02-16.md      ← /weekly-report (Monday date)
```

Running the same command twice on the same day overwrites that day's snapshot.

### Viewing historical reports

Browse the `data/reports/` subfolders to see past snapshots. Compare files across dates to track progress over time.

### Running dashboards from the terminal

You can run the script directly without any AI agent:
```
cd plainpm
python scripts/dashboard.py today
python scripts/dashboard.py this_week
python scripts/dashboard.py my_team
python scripts/dashboard.py weekly_report
```

Output goes to stdout and is saved to `data/reports/` simultaneously.

---

## Day-to-Day Workflows

### Morning routine

1. Run the today dashboard to see what needs attention
2. Review overdue and due-today items
3. Update task statuses as needed (start work → `in-progress`)

### Weekly planning (Monday)

1. Run the this_week dashboard for the full picture
2. Run the my-team dashboard to check team workload balance
3. Reassign or reprioritize tasks as needed
4. Create new tasks for the week with the new-task command

### After a meeting

1. Drop the `.vtt` transcript in `data/meetings/transcripts/YYYY/`
2. Run the process-meeting command to generate notes and tasks
3. Review created tasks, adjust priorities/due dates if needed

### End of week

1. Run the weekly-report dashboard for a summary of the week
2. Mark completed tasks as `done` (with `completed_date`)
3. Review blocked tasks — can any be unblocked?

### When a task is done

1. Open the task file
2. Set `status: done` and `completed_date: YYYY-MM-DD`
3. Optionally add a final entry under `### Updates`

### When priorities shift

1. Open the task file
2. Change `priority` to the new value
3. Add/change `due_date` if needed
4. Optionally note the change under `### Updates`:
   ```
   - 2026-02-19: Priority raised to high — blocking release
   ```

### When someone joins or leaves the team

**Joins**: Create their `data/team/*.md` file. Assign them tasks via the new-task command or manually.

**Leaves**: Reassign their open tasks first, then delete their team file.

### Creating a new project with streams from scratch

1. Create the project folder and `project.md` (see [Managing Projects](#managing-projects))
2. Add it to `data/projects/_index.md`
3. Create stream folders and `stream.md` for each stream (see [Managing Streams](#managing-streams))
4. Start creating tasks with the new-task command or manually

### Searching for tasks

Ask your AI agent directly:
- "Find all blocked tasks in project alpha"
- "What tasks does Ana have?"
- "Show me all critical priority tasks"

The agent will scan the task files and answer.

---

## File Reference

### Folder structure
```
plainpm/
├── CLAUDE.md                        # Conventions (single source of truth)
├── AGENTS.md                        # Cross-agent instructions
├── INSTRUCTIONS.md                  # This file
├── .claude/commands/                # Claude Code slash commands (thin wrappers)
├── .github/copilot-instructions.md  # GitHub Copilot instructions
├── .windsurf/rules/plainpm.md       # Windsurf rules
├── .cursor/rules/plainpm.mdc        # Cursor rules
├── prompts/commands/                # Shared command prompts (all agents)
├── scripts/dashboard.py             # Dashboard generator script
├── templates/                       # File templates
├── data/                            # User data (gitignored or submodule)
│   ├── projects/
│   │   ├── _index.md                # Master project list
│   │   └── <project-slug>/
│   │       ├── project.md
│   │       ├── tasks/
│   │       │   └── YYYY/            # Tasks grouped by year
│   │       ├── streams/
│   │       │   └── <stream-slug>/
│   │       │       ├── stream.md
│   │       │       └── tasks/
│   │       │           └── YYYY/    # Stream tasks grouped by year
│   │       └── meetings/
│   │           └── YYYY/            # Project meeting notes by year
│   ├── meetings/
│   │   ├── transcripts/
│   │   │   └── YYYY/                # Raw .vtt files by year
│   │   └── notes/
│   │       └── YYYY/                # General meeting notes by year
│   ├── team/                        # One .md per team member
│   └── reports/                     # Dashboard snapshots
│       ├── daily/YYYY/
│       ├── weekly/YYYY/
│       ├── team/YYYY/
│       └── weekly-report/YYYY/
```

All tasks, meeting notes, transcripts, and reports are organized into year subfolders (e.g., `2026/`). This keeps folders manageable as projects span multiple years. Dashboard scripts scan all year folders automatically.

### Status values

| Context | Values |
|---------|--------|
| Tasks | `todo` → `in-progress` → `done` (or `blocked` at any point) |
| Projects | `active` → `on-hold` or `completed` |
| Streams | `active` → `on-hold` or `completed` |

### Priority values

| Value | Icon | When to use |
|-------|------|-------------|
| `critical` | 🔴 | Blocking a release or other people's work |
| `high` | 🟠 | Important, should be done this week |
| `medium` | 🟡 | Standard priority (default) |
| `low` | 🟢 | Nice to have, no urgency |

### Task ID format

| Scope | Format | Example |
|-------|--------|---------|
| Stream task | `PROJECT-STREAM-NNN` | `ALPHA-BE-001` |
| Project-level task | `PROJECT-NNN` | `ALPHA-001` |

- `PROJECT`: uppercase project abbreviation derived from slug
- `STREAM`: 2-4 char uppercase abbreviation from stream folder name
- `NNN`: zero-padded, auto-incremented per scope
