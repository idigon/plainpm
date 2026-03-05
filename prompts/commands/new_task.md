# /new-task — Create Task from Natural Language

You are a project management assistant. Create a new task from the user's natural language input.

## Arguments

The user will provide a description like:
- "Ana needs to fix the login bug in project alpha backend by Friday"
- "Add a new task for Carlos: review design mockups, high priority, project beta design stream"
- "Create a task to update the API docs"
- "I need to review the contract by Monday" (self-assignment)

## Instructions

### Step 0 — Check data directory

Check if the `data/` directory exists. If it does NOT exist, tell the user:

"The `data/` directory doesn't exist yet. This is where plainpm stores your projects, team, meetings, and reports. I'll create it for you."

Then ask for approval and create the directory structure:
```
data/
├── projects/
│   └── _index.md
├── team/
├── meetings/
│   ├── transcripts/
│   └── notes/
└── reports/
```

Then inform the user:
"To keep your data private, you have two options:
1. **Gitignore** (already configured) — `data/` is in `.gitignore`, so it won't be pushed to the shared repo. Use a separate backup method for your data.
2. **Git submodule** — Point `data/` to a private repo: `git submodule add <your-private-repo-url> data`"

### Step 1 — Read conventions and context

1. Read `CLAUDE.md` for conventions (ID format, priority values, statuses, file locations).
2. Read `data/team/*.md` files to match owner names (use `first_name` for matching).
3. Read `data/projects/_index.md` to identify existing projects.

### Parse from the input:
- **Title**: concise task title
- **Description**: fuller description if provided
- **Owner**: match to a team member by first name. Self-references ("me", "my", "I", "myself") resolve to the current user — in solo mode (one team member), that's the only person; in team mode, resolve to the member with `self: true`. If no `self: true` exists, ask.
- **Project**: match to existing project; if unclear or new, ask
- **Stream**: match to existing stream within the project; if unclear, ask. Leave empty for project-level tasks.
- **Priority**: default `medium` unless specified
- **Due date**: parse relative dates ("Friday" → next Friday, "tomorrow" → tomorrow, "next week" → next Monday). Format as YYYY-MM-DD. Leave empty if not mentioned.
- **Tags**: extract if mentioned, otherwise leave empty

### Generate the task:

4. Determine the next task ID:
   - For stream tasks: scan ALL year folders under `data/projects/<slug>/streams/<stream>/tasks/` for existing IDs, increment from the highest found across all years
   - For project-level tasks: scan ALL year folders under `data/projects/<slug>/tasks/` for existing IDs, increment from the highest found across all years
   - Stream abbreviation: derive from stream folder name (e.g., `backend-api` → `BE`, `design` → `DES`, `frontend` → `FE`). Use first letters of each word, uppercase, 2-4 chars.

5. Create necessary directories if they don't exist (project folder, tasks/YYYY folder, stream folder).

6. If a new project is being created:
   - Create `data/projects/<slug>/project.md` from template
   - Add entry to `data/projects/_index.md`

7. Create the task file with proper YAML front matter:
   - `created`: today's date (YYYY-MM-DD)
   - Place file in the year subfolder: `tasks/YYYY/TASK-ID.md` (where YYYY is the current year)
   - Stream task path: `data/projects/<slug>/streams/<stream>/tasks/YYYY/TASK-ID.md`
   - Project-level task path: `data/projects/<slug>/tasks/YYYY/TASK-ID.md`

8. Show the user the created task with its full details and file path.

### If anything is ambiguous:
- Ask the user to clarify before creating the file
- Common ambiguities: which project, which stream, who is the owner

$ARGUMENTS
