# /new-note — Create a Note in an Area, Project, or Stream

You are a project management assistant. Create a new note from the user's natural language input.

## Arguments

The user will provide a description like:
- "Add a note to the team area about onboarding process changes"
- "Note in project alpha: decided to switch to PostgreSQL"
- "Write a note in the platform area about the new deployment checklist"
- "Note for project beta backend stream: API versioning strategy"
- "Team management note: performance review cycle starts next month"

## Instructions

### Step 0 — Check data directory

Check if the `data/` directory exists. If it does NOT exist, tell the user:

"The `data/` directory doesn't exist yet. This is where plainpm stores your projects, team, meetings, and reports. I'll create it for you."

Then ask for approval and create the directory structure:
```
data/
├── projects/
│   └── _index.md
├── tasks/
├── team/
├── meetings/
│   ├── transcripts/
│   ├── notes/
│   └── areas/
└── reports/
```

Then inform the user:
"To keep your data private, you have two options:
1. **Gitignore** (already configured) — `data/` is in `.gitignore`, so it won't be pushed to the shared repo. Use a separate backup method for your data.
2. **Private repo** — Clone a private repo into `data/` manually: `git clone <your-private-repo-url> data`. The URL stays local since `data/` is gitignored."

### Step 1 — Read conventions and context

1. Read `CLAUDE.md` for conventions (file locations, date format, notes rules).
2. List existing areas under `data/meetings/areas/` and existing projects under `data/projects/` to match the user's target.

### Step 2 — Parse the input

Extract from the user's description:
- **Title**: concise note title
- **Content**: the substance of the note — what the user wants recorded
- **Target context**: where this note belongs:
  - **Area**: match to an existing area under `data/meetings/areas/`. If the user names an area that doesn't exist, ask if they want to create it.
  - **Project**: match to an existing project under `data/projects/`. If unclear, ask.
  - **Stream**: match to a stream within the identified project. If unclear, ask.
  - If no context is given, ask the user where the note should go.
- **Tags**: extract if mentioned, otherwise leave empty
- **Links**: extract if URLs are mentioned

### Step 3 — Determine the note location

Notes go in the `notes/YYYY/MM/` subfolder of the target context:

- **Area note**: `data/meetings/areas/<area-slug>/notes/YYYY/MM/YYYY-MM-DD-note-title.md`
- **Project note**: `data/projects/<slug>/meetings/YYYY/MM/YYYY-MM-DD-note-title.md`
- **Stream note**: `data/projects/<slug>/streams/<stream-slug>/notes/YYYY/MM/YYYY-MM-DD-note-title.md`

Use today's date for YYYY, MM, and the date prefix. Slugify the title for the filename (lowercase, hyphens, no special chars).

Create subdirectories if they don't exist.

### Step 4 — Create the note file

Use `templates/note.md` as the base. Fill in:
- `type: note`
- `date`: today's date (YYYY-MM-DD)
- `area`: area slug if this is an area note; otherwise leave blank
- `project`: project slug if this is a project or stream note; otherwise leave blank
- `stream`: stream slug if this is a stream note; otherwise leave blank
- `tags`: any tags extracted from the input
- `links`: any links extracted from the input

For the body:
- **Title**: use the extracted title
- **Summary**: a concise summary of the note content (1-2 sentences)
- **Details**: the full content the user provided, organized clearly. Use subheadings if the content covers multiple topics.

### Step 5 — Cross-reference updates

After creating the note, check if the content warrants an update entry on the parent entity (project, stream, or area):

- If the note contains a decision, status change, or meaningful update about the parent entity, propose a dated summary for the entity's `### Updates` section.
- Follow the same approval flow as in `/process-meeting`: show the existing latest update, propose the new one, and ask the user to approve, edit, replace, or skip.
- Format: `- YYYY-MM-DD: <summary> (source: [note title](relative-path-to-note))`
- Follow **Same-Day Updates** conventions from `CLAUDE.md`.

### Step 6 — If the note creates action items

If the user's note content includes action items or tasks that need doing:
- Ask the user if they want to create task files for any of them.
- If yes, follow the same task creation flow as `/new-task` (ID generation, file placement, etc.).
- Link the created tasks back to the note via `source_meeting` (which works for notes too — the field name is a legacy convention).

### Step 7 — Show the user

- The created note (full content)
- File path where it was saved
- Any proposed cross-reference updates (pending approval)
- Any tasks created from action items

### If anything is ambiguous:
- Ask the user to clarify before creating the file
- Common ambiguities: which area/project/stream, whether to create a new area

$ARGUMENTS
