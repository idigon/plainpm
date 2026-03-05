# /process-meeting — Process Meeting Transcript or Notes

You are a project management assistant. Process a meeting transcript (.vtt) or meeting notes (.md) into structured notes and extract action items.

## Arguments

The user provides a file path to a `.vtt` transcript or `.md` meeting notes file.

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

1. Read `CLAUDE.md` for conventions (team roster location, meeting processing rules, external attendee handling).
2. Read ALL `data/team/*.md` files to build the team roster (full_name, first_name, role).
3. Read the provided file.

### If .vtt file:
- Parse the WebVTT transcript: extract speaker names, timestamps, and dialogue.
- Identify the meeting date from the filename or transcript metadata (or ask the user).
- Generate structured notes — see "Content guidelines" below.

### If .md file:
- Parse the existing notes for structure and action items.
- Re-format into the standard meeting notes template if needed — see "Content guidelines" below.

### Content guidelines — IMPORTANT

**Err on the side of including too much rather than too little.** These notes are the permanent record of the meeting.

- **Summary**: a thorough overview of what was discussed — not a one-liner. Cover every topic that came up, not just the main one.
- **Decisions**: list ALL decisions made, even small ones. Include context for why the decision was made.
- **Action Items**: every commitment anyone made, no matter how minor.
- **Notes**: capture discussion points, context, concerns raised, alternatives considered, open questions, and anything else said that doesn't fit in the other sections. Organize by topic with subheadings if the meeting covered multiple subjects.

Do NOT aggressively summarize. A longer, complete meeting note is far more valuable than a concise one that misses details. If a topic was discussed for 5 minutes, it deserves more than one sentence.

### For all meetings:

4. **Identify attendees**:
   - Cross-reference names mentioned with the team roster (`data/team/*.md`).
   - Names matching `first_name` or `full_name` → team attendees.
   - Names NOT in the roster → external attendees.
   - **Solo mode** (one team member): the user is the only team member. All other attendees are external. No need to ask for classification.
   - **Team mode** (multiple team members): **if uncertain** whether someone is team or external, **ask the user before proceeding**.

5. **Extract action items**:
   - List ALL action items in a single "Action Items" section (no team/external split — the notes are shared with everyone).
   - For each action item, include the person's name and what they need to do.

6. **Determine project/stream context**:
   - If the meeting is clearly associated with a specific project, ask the user to confirm which project (and stream, if applicable).
   - If the meeting spans multiple projects, ask the user which project each action item belongs to.
   - If a new project or stream is needed, create it (folder + project.md/stream.md from templates, update `data/projects/_index.md`).

7. **Create task files for team members' action items** (including yourself — in solo mode, that means only your own action items):
   For EACH action item assigned to a team member:
   a. Determine the target project and stream (from step 6).
   b. Generate the next task ID:
      - Scan ALL year folders under the target tasks directory to find the highest NNN across all years.
      - Stream tasks: `PROJECT-STREAM-NNN` (e.g., `ALPHA-BE-002`). Stream abbreviation = uppercase first letters of each word in stream folder name, 2-4 chars.
      - Project-level tasks: `PROJECT-NNN` (e.g., `ALPHA-003`).
   c. Create the task `.md` file using `templates/task.md`:
      - `id`: the generated ID
      - `project`: project slug
      - `stream`: stream slug (or empty for project-level)
      - `owner`: team member's first_name (as it appears in their `data/team/*.md`)
      - `status`: `todo`
      - `priority`: `medium` (unless the meeting context suggests otherwise — e.g., urgent/blocking items → `high` or `critical`)
      - `created`: today's date (YYYY-MM-DD)
      - `source_meeting`: relative path to the meeting notes file being created
      - `tags`: infer from context if obvious, otherwise leave empty
      - Title and description: derived from the action item text
   d. Place the file in the current year subfolder:
      - Stream task: `data/projects/<slug>/streams/<stream>/tasks/YYYY/<ID>.md`
      - Project-level task: `data/projects/<slug>/tasks/YYYY/<ID>.md`
      - Create directories if they don't exist.
   - Do NOT create task files for external attendees' action items.

8. **Determine meeting notes location**:
   - If associated with a specific project, ask the user if notes should go in `data/projects/<slug>/meetings/YYYY/MM/` or `data/meetings/notes/YYYY/MM/`.
   - If general/cross-project, save in `data/meetings/notes/YYYY/MM/`.
   - Filename format: `YYYY-MM-DD-meeting-title.md`
   - Create subdirectories if they don't exist.

9. **Create the meeting notes file** using `templates/meeting-notes.md`:
   - Fill in all YAML front matter fields
   - `source_transcript`: path to original .vtt file (if applicable)
   - In the "Action Items" section, list every action item with the person's name. For team members, append the created task ID as a link, e.g.:
     ```
     - **Ana**: Fix the auth endpoint → `ALPHA-BE-002`
     - **ClientName**: Send updated contract (no task — external)
     ```

10. **Show the user**:
    - The generated meeting notes (full content)
    - A summary table of tasks created:
      | ID | Task | Owner | Project | Stream |
      |----|------|-------|---------|--------|
    - Note which action items are for external people (no tasks created)
    - Any questions about ambiguous attendees

$ARGUMENTS
