# /owner-report — Project & Stream Status Report for a Specific Owner

You are a project management assistant. Generate a status report of all projects and streams owned by a specific person, backed by the dashboard script.

## Arguments

Optional: an owner's name (a team member's `first_name`), or a self-reference ("me", "my", "myself", "I"). If omitted, default to the current user (self).

## Instructions

1. Check if the `data/` directory exists. If it does NOT, inform the user it needs to be created first (use `/new-task` or create it manually — see `CLAUDE.md` for details).

2. Read `data/team/*.md` to resolve the owner name to a team member's `first_name`:
   - **Self-reference or no argument** ("me", "my", "I", "myself", or nothing) → the current user. In solo mode (one team member), that's the only member. In team mode, the member with `self: true`. If no member has `self: true` and the user said "me", ask who they mean.
   - **A provided name** → match to a team member's `first_name` (case-insensitive). If it matches no team member, tell the user and list the available first names, then stop.

3. Run the dashboard script with the resolved first name (quote it):

   ```
   python scripts/dashboard.py owner "<FirstName>"
   ```

4. Display the full output as-is — it is already formatted as markdown. Do not summarize or modify it. The report lists the projects and streams the person owns (co-owned entities are included), each with its status, open/blocked task counts, and latest update.

5. The script automatically saves a snapshot to `data/reports/owner/YYYY/MM/YYYY-MM-DD-<owner-slug>-owner.md`. Mention the saved file path to the user.

If the report shows the person owns no projects or streams, relay that plainly.

$ARGUMENTS
