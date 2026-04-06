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

6. **Determine meeting context** (area or project):
   - **Check if the user indicated a meeting area** — they may say things like "this is a team sync", "area: partner-engagements", "save under team syncs", or name an area directly. If so, use that area.
   - **Check if a matching area exists**: list folders under `data/meetings/areas/`. If the user's description matches an existing area slug or name, use it. If a new area seems warranted, ask the user if they want to create one.
   - **If it's an area meeting**: the `area` field in notes front matter = area slug; `project` = blank. Notes go in `data/meetings/areas/<area-slug>/notes/YYYY/MM/`.
   - **If no area is indicated**: check if the meeting is associated with a specific project. Ask the user to confirm which project (and stream, if applicable).
   - If the meeting spans multiple projects, ask the user which project each action item belongs to.
   - If a new project or stream is needed, create it (folder + project.md/stream.md from templates, update `data/projects/_index.md`).
   - If a **new area** is needed: create the folder `data/meetings/areas/<area-slug>/`, write `area.md` from `templates/area.md` (fill in slug, summary, created date), and create the `notes/` subfolder.

7. **Create task files for team members' action items** (including yourself — in solo mode, that means only your own action items):
   For EACH action item assigned to a team member:
   a. Determine the target project and stream (from step 6). If the action item doesn't belong to any project (common for area meetings), it becomes a **standalone task**.
   b. Generate the next task ID:
      - Scan ALL year folders under the target tasks directory to find the highest NNN across all years.
      - Stream tasks: `PROJECT-STREAM-NNN` (e.g., `ALPHA-BE-002`). Stream abbreviation = uppercase first letters of each word in stream folder name, 2-4 chars.
      - Project-level tasks: `PROJECT-NNN` (e.g., `ALPHA-003`).
      - Standalone tasks: `TASK-NNN` (e.g., `TASK-001`). Scan `data/tasks/` for existing IDs.
   c. Create the task `.md` file using `templates/task.md`:
      - `id`: the generated ID
      - `project`: project slug (or empty for standalone tasks)
      - `stream`: stream slug (or empty for project-level/standalone)
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
      - Standalone task: `data/tasks/YYYY/<ID>.md`
      - Create directories if they don't exist.
   - Do NOT create task files for external attendees' action items.

8. **Cross-reference updates to existing entities** (projects, streams, and tasks):

   After extracting action items and creating new tasks, review the meeting content for discussions about existing projects, streams, or tasks. For each entity that was meaningfully discussed, propose a dated summary for its `### Updates` section — but **always ask the user for approval before writing**.

   a. **Identify discussed entities**:
      - **Projects**: check if the meeting discussed any project in `data/projects/`. Match by project name, slug, or general context.
      - **Streams**: check if specific streams within a project were discussed. Match by stream name or slug.
      - **Existing tasks**: check if any existing task IDs were mentioned (e.g., `ALPHA-BE-001`) or if discussion clearly refers to a known open task (match by title/description).

   b. **What to include vs. skip**:
      - **Include**: status updates, decisions affecting the entity, blockers discussed, scope changes, timeline changes, new context or requirements.
      - **Skip**: passing mentions with no substance (e.g., "we also have project X" with no further discussion), action items that are already captured as new tasks.
      - **For existing tasks**: do NOT duplicate information that's already in a newly created task's description.

   c. **Present proposed updates to the user for review**:
      For each identified entity, show:
      - The entity name, type (project / stream / task), and file path.
      - The **existing latest update** (the last entry currently under `### Updates`), so the user can see what's already there. If there are no existing updates, say "(no existing updates)".
      - The **proposed new update** — format: `- YYYY-MM-DD: <concise summary> (source: [meeting title](relative-path-to-meeting-notes))`
      - Keep each proposed entry to 1-2 sentences. The meeting notes have the full detail; the update is a pointer and quick summary.
      - **Same-day handling**: if the entity already has an update for today's date, follow the **Same-Day Updates** convention in `CLAUDE.md` — convert to grouped format with sub-bullets instead of adding a duplicate date.

      Display this as a clear list, for example:
      ```
      Proposed updates from this meeting:

      1. **roles** (project) — `data/projects/roles/project.md`
         Latest existing update: (none)
         Proposed: `- 2026-03-17: Phase 1 on track for C26.03, sales enablement training confirmed for April 2nd (source: [Team Sync — Mar 17](...))`

      2. **roles / phase-1** (stream) — `data/projects/roles/streams/phase-1/stream.md`
         Latest existing update: `- 2026-03-11: Sales enablement training scheduled April 2nd. Nashat building materials.`
         Proposed: `- 2026-03-17: Training materials ready, dry run scheduled for March 28 (source: [Team Sync — Mar 17](...))`

      3. **ROLES-004** (task) — `data/projects/roles/tasks/2026/ROLES-004.md`
         Latest existing update: `- 2026-03-14: Waiting on design review`
         Proposed: `- 2026-03-17: Design review completed, moving to implementation (source: [Team Sync — Mar 17](...))`
      ```

   d. **Ask the user what to do for each** (or all at once). The user may:
      - **Approve** — append the proposed update as-is.
      - **Edit** — provide a revised update text (e.g., merging the existing latest update with the new one, or rewording).
      - **Replace** — replace the existing latest update instead of appending (useful when the new info supersedes the old).
      - **Skip** — don't add any update to that entity.

      The user can respond per-entity or in bulk (e.g., "approve all", "skip 2, approve the rest", "edit 3 to say: ...").

   e. **Apply approved updates**:
      - For "approve" or "edit": append the (possibly revised) entry under `### Updates`.
      - For "replace": replace the last entry under `### Updates` with the new one.
      - If `### Updates` doesn't exist in the file, add it at the end of the document.
      - Do NOT write any update the user skipped.

9. **Determine meeting notes location**:
   - If area meeting: `data/meetings/areas/<area-slug>/notes/YYYY/MM/`
   - If project-specific: ask the user if notes should go in `data/projects/<slug>/meetings/YYYY/MM/` or `data/meetings/notes/YYYY/MM/`.
   - If general/cross-project: save in `data/meetings/notes/YYYY/MM/`.
   - Filename format: `YYYY-MM-DD-meeting-title.md`
   - Create subdirectories if they don't exist.

10. **Create the meeting notes file** using `templates/meeting-notes.md`:
    - Fill in all YAML front matter fields
    - `area`: area slug if this is an area meeting; otherwise leave blank
    - `project`: project slug if project-specific; otherwise leave blank
    - `source_transcript`: path to original .vtt file (if applicable)
    - In the "Action Items" section, list every action item with the person's name. For team members, append the created task ID as a link, e.g.:
      ```
      - **Ana**: Fix the auth endpoint → `ALPHA-BE-002`
      - **ClientName**: Send updated contract
      ```

11. **Show the user**:
    - The generated meeting notes (full content)
    - A summary table of tasks created:
      | ID | Task | Owner | Project | Stream |
      |----|------|-------|---------|--------|
    - A summary of entity updates applied (after user approval from step 8):
      | Entity | Type | Action |
      |--------|------|--------|
      (e.g., `roles` | project | approved / `roles / phase-1` | stream | edited / `ROLES-004` | task | skipped)
    - Note which action items had no task created (external attendees)
    - Any questions about ambiguous attendees

$ARGUMENTS
