# plainpm — Instructions

A complete guide to using your markdown-based project management system. Covers both slash commands (automated) and manual operations.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Slash Commands (Automated)](#slash-commands)
3. [Managing Projects](#managing-projects)
4. [Managing Streams](#managing-streams)
5. [Managing Tasks](#managing-tasks)
6. [Managing Team Members](#managing-team-members)
7. [Meeting Areas](#meeting-areas)
8. [Meeting Processing](#meeting-processing)
9. [Dashboards & Reports](#dashboards--reports)
10. [Day-to-Day Workflows](#day-to-day-workflows)
11. [File Reference](#file-reference)

---

## Getting Started

### Opening plainpm

Open your AI coding agent from the project root directory so it picks up the configuration automatically:

- **Claude Code**: `cd plainpm && claude` (reads `CLAUDE.md` + `.claude/commands/`)
- **VS Code + Copilot**: open the `plainpm/` folder (reads `.github/copilot-instructions.md`)
- **Windsurf**: open the `plainpm/` folder (reads `.windsurf/rules/plainpm.md`)
- **Cursor**: open the `plainpm/` folder (reads `.cursor/rules/plainpm.mdc`)

### Data directory setup

All user data lives in the `data/` subdirectory. If it doesn't exist yet, any write command (`/new-task`, `/new-note`, `/process-meeting`) will offer to create it for you.

To set it up manually:
```
mkdir -p data/projects data/team data/meetings/transcripts data/meetings/notes data/reports
```

**Privacy options:**
- **Gitignore** (default) — `data/` is in `.gitignore`, so it won't be pushed to the shared repo. Use a separate backup method.
- **Private repo** — Clone a private repo into `data/` manually: `git clone <your-private-repo-url> data`. Since `data/` is gitignored, the URL is never exposed in the public repo.

### First-time setup

1. **Create the data directory** — run any command or create it manually (see above).
2. **Add yourself as a team member** — create a file in `data/team/` with your name and role (see [Managing Team Members](#managing-team-members)). This is required even for solo use.
3. **Add other team members** (optional) — create one file per person in `data/team/`.
4. **Create your first project** — use the "new task" command or create it manually (see [Managing Projects](#managing-projects)).
5. **Run the "today" dashboard** to verify everything works.

**Solo vs. team**: plainpm detects the mode automatically. With one team member file (just you), commands like "assign to me" auto-resolve to your name, and all meeting attendees besides you are treated as external.

---

## Commands

Command prompts are in `prompts/commands/`. In Claude Code, these are wired as `/slash-commands`. In other agents, ask for them by name (e.g., "run today dashboard", "create a new task", "process this meeting").

**Natural-language usage (Claude Code only).** Seven of the commands — `new-task`, `update`, `done`, `process-meeting`, `archive`, `status`, and `new-note` — are also exposed as skills, so you can just describe what you want and the right one will load automatically. For example, "Ana needs to fix the login bug by Friday" triggers `new-task`, and "mark ALPHA-001 done" triggers `done`. The slash commands still work the same way; skills are an alternative entry point, not a replacement. The four dashboards (`today`, `this_week`, `my-team`, `weekly-report`) and `agenda` remain slash-only.

| Command | Prompt file | What it does |
|---------|-------------|-------------|
| today | `prompts/commands/today.md` | Daily dashboard — overdue, due today, in-progress, blocked, not started |
| this_week | `prompts/commands/this_week.md` | Weekly dashboard — all projects, streams, and tasks in tables |
| my-team | `prompts/commands/my_team.md` | Team workload — tasks per person with days-open count |
| owner-report | `prompts/commands/owner_report.md` | Projects & streams owned by a specific person, with statuses |
| weekly-report | `prompts/commands/weekly_report.md` | Week summary — completed, in-progress, blocked, new tasks |
| new-task | `prompts/commands/new_task.md` | Create a task from natural language |
| new-note | `prompts/commands/new_note.md` | Create a note in an area, project, or stream |
| process-meeting | `prompts/commands/process_meeting.md` | Process a .vtt transcript or .md notes into structured notes + tasks |
| status | `prompts/commands/status.md` | Project status report (one project or all) |
| done | `prompts/commands/done.md` | Mark task(s) as done |
| update | `prompts/commands/update.md` | Batch update tasks from natural language |
| agenda | `prompts/commands/agenda.md` | Generate meeting agenda from open tasks |
| archive | `prompts/commands/archive.md` | Archive old completed tasks to `data/archive/` |

### new-task

Describe what you need in plain language. Examples:

```
"Ana needs to fix the login bug in project alpha backend by Friday"
"Create a task for Carlos: review design mockups, high priority, project beta design stream"
"Update the API docs for project alpha, low priority"
"I need to review the contract by Monday"   ← self-assignment
```

The command will:
- Match names to team members (including "me"/"my"/"I" → your team profile)
- Match project/stream names to existing ones
- Generate the next task ID
- Create the file in the right location
- Ask you to clarify anything ambiguous

### process-meeting

Provide a file path to a `.vtt` transcript or `.md` meeting notes:

```
"Process meeting data/meetings/transcripts/2026/02/2026-02-19-sprint-review.vtt"
"Process meeting data/meetings/notes/2026/02/draft-kickoff.md"
```

The command will:
- Parse the content and generate structured meeting notes
- Identify attendees (team vs. external)
- Create task files for every team member action item
- Append update notes to any projects, streams, or existing tasks that were discussed (see [Cross-reference updates](#cross-reference-updates))
- List external attendees' action items in the notes only (no task files)
- Ask you about anything unclear

### new-note

Create a note (not from a meeting) in any area, project, or stream:

```
"Add a note to the team area about onboarding process changes"
"Note in project alpha: decided to switch to PostgreSQL"
"Note for project beta backend stream: API versioning strategy"
"Team management note: performance review cycle starts next month"
```

The command will:
- Match the target area, project, or stream
- Create the note file in the right `notes/YYYY/MM/` subfolder
- Optionally propose cross-reference updates to the parent entity
- Optionally create tasks if the note contains action items

Notes use `type: note` in front matter (vs `type: meeting` for meeting notes) and share the same folder structure.

### status

```
"Project status for project-alpha"    # Detailed report for one project
"Portfolio status"                    # Summary across all projects
```

### owner-report

Report the projects and streams a specific person owns (co-owned entities included), each with its status and open/blocked task counts:

```
"What does Ana own?"
"Owner report for Bob"
"Which projects and streams am I the owner of?"   ← self-reference
```

Names resolve to a team member's `first_name`; "me"/"my"/"I" resolve to you. The report is also saved under `data/reports/owner/`.

### done

Mark one or more tasks as done in a single command:

```
"Done ALPHA-BE-001"
"Mark ALPHA-BE-001 and ALPHA-002 as done"
"ALPHA-BE-001 done — deployed to production"
```

The command sets `status: done` and `completed_date` to today. If you include a note, it's appended under `### Updates`.

### update

Batch update tasks, projects, and streams from natural language:

```
"Move ALPHA-BE-001 to in-progress"
"Reassign ALPHA-002 to Carlos, raise priority to high"
"Set ALPHA-BE-001 due date to next Friday"
"ALPHA-BE-001: blocked — waiting on API credentials"
"Set the owner of project alpha to Ana"
"Make Ana and Bob co-owners of the backend stream in project alpha"
```

For **tasks**, supports changing `status`, `priority`, `owners`, `due_date`, `tags`, dependencies, and adding update notes. For **projects and streams**, supports changing `owners` (co-ownership allowed) and `status`. If anything is ambiguous, the command will ask you to clarify.

### agenda

Generate a meeting agenda from open tasks:

```
"Generate agenda for project-alpha"
"Meeting agenda"
```

Builds sections for blockers, overdue, in-progress, due this week, and new/unassigned tasks. Output is displayed only — not saved automatically.

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
   owners: [Ana]          # project owner(s); [Ana, Bob] for co-ownership, [] for unassigned
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

The `owners` array holds team-member `first_name` values. Two or more names means co-ownership. A project's owner is independent of who owns its tasks. Reassign later with `/update` (e.g., "set the owner of project alpha to Ana") or by editing the front matter. See the `owner-report` command to list everything a person owns.

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

Set status to `completed`. The project folder stays in place. Dashboard scripts skip `done` tasks but still list the project. Use the `/archive` command to move old completed tasks to `data/archive/`.

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
   owners: [Ana]          # stream owner(s); [Ana, Bob] for co-ownership, [] for unassigned
   summary: API migration and new endpoint development
   created: 2026-02-19
   links: []
   ---

   ## Backend API

   ### Overview
   What this stream covers.
   ```

The stream's `owners` array works exactly like a project's — team-member `first_name` values, multiple names for co-ownership, independent of task ownership. Reassign with `/update` (e.g., "make Ana and Bob co-owners of the backend stream in project alpha") or by editing the front matter.

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
   - Standalone task: `TASK-NNN` (e.g., `TASK-001`) — for tasks not tied to any project

2. Create the file in the current year subfolder:
   - Stream task: `data/projects/project-alpha/streams/backend-api/tasks/2026/ALPHA-BE-002.md`
   - Project-level task: `data/projects/project-alpha/tasks/2026/ALPHA-003.md`
   - Standalone task: `data/tasks/2026/TASK-001.md`

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

### Adding dependencies

Use `blocked_by` to declare that a task depends on other tasks:
```yaml
blocked_by: [ALPHA-BE-001, ALPHA-003]
```

When those tasks are marked done via `/done`, the agent checks if this task is now unblocked and suggests updating its status.

You can also set dependencies via commands:
```
"ALPHA-BE-003 is blocked by ALPHA-BE-001"
"Create a task to deploy frontend, after ALPHA-BE-002"
```

### Unblocking a task

Change status back to the appropriate value:
```yaml
status: in-progress    # or: todo
```

If the task had `blocked_by` entries, they remain in the front matter as a historical record of what the dependency was. You can clear them if you prefer:
```yaml
blocked_by: []
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
source_meeting: data/meetings/notes/2026/02/2026-02-19-sprint-review.md
```

This is set automatically by the process-meeting command but can be added manually too.

### Archiving completed tasks

Use the `/archive` command to move old completed tasks out of the active project folders:

```
"Archive tasks done more than 30 days ago"
"Archive project-alpha tasks older than 14 days"
```

Archived tasks are moved to `data/archive/<project-slug>/YYYY/` (year from `completed_date`). Dashboards only scan `data/projects/`, so archived tasks disappear from all views automatically. The task files are unchanged — you can move them back if needed.

---

## Managing Team Members

### Adding yourself (required)

Create a file for yourself first — this enables self-assignment ("assign to me", "my task", "I need to...") and ensures your action items from meetings become tasks.

`data/team/your-name.md`:
```yaml
---
type: team-member
full_name: Your Full Name
first_name: YourFirstName
role: Your Role
self: true
---

## Notes

```

The `self: true` flag tells plainpm that this is you. When you say "assign to me" or "I need to...", commands resolve to this profile. Only one team member should have `self: true`.

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

Your own team file is essential — it enables self-assignment in commands ("me", "my", "I") and ensures your meeting action items become tasks. Set `self: true` in your front matter so plainpm knows which member is you. In solo mode (one team member), "me" auto-resolves regardless of the flag.

---

## Meeting Areas

Meeting areas let you group recurring meetings that aren't tied to a specific project — for example, team syncs, partner engagements, 1:1s, all-hands sessions, or vendor calls. Each area is just a folder with an `area.md` definition file. Adding a new area never requires creating a project.

### Creating a new meeting area

1. Choose a slug (lowercase-kebab-case): e.g., `team-syncs`, `partner-engagements`
2. Create the folder structure:
   ```
   data/meetings/areas/team-syncs/
   ├── area.md
   └── notes/
       └── 2026/               # Year/month subfolders for notes
   ```
3. Write `area.md` using the template (`templates/area.md`):
   ```yaml
   ---
   type: area
   slug: team-syncs
   summary: Weekly team sync meetings
   created: 2026-03-06
   ---

   ## Team Syncs

   ### Description
   Weekly sync with the full team. Covers priorities, blockers, and coordination.

   ### Cadence
   Every Monday at 10:00 AM

   ### Typical Attendees
   - Full engineering team
   ```
4. Start dropping notes in `data/meetings/areas/team-syncs/notes/YYYY/MM/`.

That's it — no project file, no `_index.md` entry, no task ID prefix needed.

### Suggested areas to start with

| Area slug | What it covers |
|-----------|---------------|
| `team-syncs` | Regular team check-ins |
| `partner-engagements` | External partner or vendor meetings |
| `one-on-ones` | 1:1s with team members |
| `all-hands` | Company or department-wide meetings |
| `stakeholder-reviews` | Steering committee or exec updates |

### Writing notes for an area

Use the standard meeting notes template, and set the `area` field instead of `project`:

```yaml
---
type: meeting
date: 2026-03-06
area: team-syncs
project:
attendees: [Ana, Carlos, You]
links: []
source_transcript:
---

## Team Sync — Mar 6

### Summary
...

### Decisions
...

### Action Items
- **Ana**: Follow up on API rate limits → `ALPHA-BE-005`
- **Carlos**: Share updated roadmap with stakeholders

### Notes
...
```

Save the file to `data/meetings/areas/team-syncs/notes/YYYY/MM/YYYY-MM-DD-meeting-title.md`.

### Processing a meeting in an area

When running the `process-meeting` command, tell the agent which area the meeting belongs to:

```
"Process meeting data/meetings/transcripts/2026/03/2026-03-06-team-sync.vtt — this is a team sync"
"Process meeting path/to/notes.md, area: partner-engagements"
```

The agent will:
- Save the structured notes to `data/meetings/areas/<area-slug>/notes/YYYY/MM/`
- Create task files for team members' action items (same rules as any meeting)
- Set the `area` field in the meeting notes front matter

### Listing your areas

Browse `data/meetings/areas/` to see all defined areas. Each subfolder has an `area.md` with its description and cadence.

### Searching across an area

Ask your agent directly:
- "Find all team sync notes from February"
- "What decisions were made in partner engagement meetings this quarter?"
- "Show action items from team syncs in January"

The agent will scan the area's notes folder and answer.

---

## Meeting Processing

### Workflow with transcripts (.vtt)

1. After a meeting, save the `.vtt` transcript to `data/meetings/transcripts/YYYY/MM/`
   - Name it descriptively: `2026-02-19-sprint-review.vtt`
2. Ask your agent to process the meeting: "Process meeting data/meetings/transcripts/2026/02/2026-02-19-sprint-review.vtt"
3. The agent will:
   - Parse the transcript
   - Generate structured notes
   - Identify team members vs. external attendees
   - Create task files for team members' action items (in the current year subfolder)
   - Save notes to `data/meetings/notes/YYYY/MM/` or `data/projects/<slug>/meetings/YYYY/MM/`
4. Review the output and confirm

### Workflow with manual notes (.md)

1. Write your meeting notes as a `.md` file (anywhere — desktop, temp folder, etc.)
2. Ask your agent to process the meeting: "Process meeting path/to/your/notes.md"
3. The agent will restructure the notes and extract action items

### Writing meeting notes directly

If you prefer to write notes directly without processing:

`data/meetings/notes/2026/02/2026-02-19-sprint-review.md`:
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

### Cross-reference updates

When processing a meeting, the agent also scans the discussion for references to existing projects, streams, and tasks. For each entity that was meaningfully discussed (not just mentioned in passing), it **proposes** a dated one-liner for the entity's `### Updates` section — but always asks for your approval first.

The agent shows you each proposed update alongside the entity's existing latest update, so you can see the full picture:

```
Proposed updates from this meeting:

1. **roles / phase-1** (stream) — data/projects/roles/streams/phase-1/stream.md
   Latest existing update: `- 2026-03-11: Sales enablement training scheduled April 2nd. Nashat building materials.`
   Proposed: `- 2026-03-17: Training materials ready, dry run scheduled for March 28 (source: [Team Sync — Mar 17](...))`
```

For each proposed update, you can:
- **Approve** — append as-is
- **Edit** — provide your own text (e.g., merge the existing and new update into one)
- **Replace** — replace the existing latest update instead of appending (when the new info supersedes it)
- **Skip** — don't touch this entity

You can respond per-entity or in bulk (e.g., "approve all", "skip 1, approve the rest").

**What gets proposed:**
- **Projects** (`project.md`): when the meeting discussed project-level status, decisions, risks, or timeline changes
- **Streams** (`stream.md`): when the meeting discussed a specific stream's progress, scope, or blockers
- **Existing tasks**: when the meeting discussed progress, decisions, or blockers on a known open task

**What doesn't get proposed:**
- Entities only mentioned in passing with no substantive discussion
- New tasks that were just created from the meeting's action items (they already have the context in their description)

### Where meeting notes are saved

- Area meetings: `data/meetings/areas/<area-slug>/notes/YYYY/MM/`
- Project-specific meetings: `data/projects/<slug>/meetings/YYYY/MM/`
- General / cross-project meetings: `data/meetings/notes/YYYY/MM/`

---

## Dashboards & Reports

### Running dashboards

All four dashboards are script-powered for speed and consistency:

| Command | What it shows |
|---------|--------------|
| today | Overdue, due today, in-progress, blocked, not started tasks |
| this_week | All projects/streams/tasks in table format |
| my-team | Tasks grouped by team member with days-open count |
| weekly-report | Completed, in-progress, blocked, new tasks this week |

### Saved snapshots

Every dashboard run saves a snapshot to `data/reports/`:

```
data/reports/
├── daily/2026/02/2026-02-19.md              ← /today
├── weekly/2026/02/2026-02-16.md             ← /this_week (Monday date)
├── team/2026/02/2026-02-19.md               ← /my-team
└── weekly-report/2026/02/2026-02-16.md      ← /weekly-report (Monday date)
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

1. Drop the `.vtt` transcript in `data/meetings/transcripts/YYYY/MM/`
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
├── data/                            # User data (gitignored, or separate private repo)
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
│   │           └── YYYY/MM/         # Project meeting notes by year/month
│   ├── tasks/                       # Standalone tasks (not tied to any project)
│   │   └── YYYY/                    # Grouped by year
│   ├── meetings/
│   │   ├── transcripts/
│   │   │   └── YYYY/MM/             # Raw .vtt files by year/month
│   │   ├── notes/
│   │   │   └── YYYY/MM/             # General meeting notes by year/month
│   │   └── areas/
│   │       └── <area-slug>/         # One folder per meeting area
│   │           ├── area.md          # Area definition (from templates/area.md)
│   │           └── notes/
│   │               └── YYYY/MM/     # Area meeting notes by year/month
│   ├── team/                        # One .md per team member
│   └── reports/                     # Dashboard snapshots
│       ├── daily/YYYY/MM/
│       ├── weekly/YYYY/MM/
│       ├── team/YYYY/MM/
│       └── weekly-report/YYYY/MM/
```

Tasks are organized into year subfolders (e.g., `tasks/2026/`). Meeting notes, transcripts, and reports are organized into year/month subfolders (e.g., `2026/02/`) to keep folders manageable at high volume. Dashboard scripts use `rglob` and scan all subfolders automatically.

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
| Standalone task | `TASK-NNN` | `TASK-001` |

- `PROJECT`: uppercase project abbreviation derived from slug
- `STREAM`: 2-4 char uppercase abbreviation from stream folder name
- `TASK`: literal prefix for standalone tasks (not tied to any project)
- `NNN`: zero-padded, auto-incremented per scope
