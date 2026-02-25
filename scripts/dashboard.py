#!/usr/bin/env python3
"""PM Vault Dashboard Generator.

Usage:
    python scripts/dashboard.py today
    python scripts/dashboard.py this_week
    python scripts/dashboard.py my_team
    python scripts/dashboard.py weekly_report
"""

import sys
import os
import io
import re
from datetime import date, timedelta
from pathlib import Path
from collections import defaultdict

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Resolve vault root (script lives in scripts/)
VAULT = Path(__file__).resolve().parent.parent
DATA_DIR = VAULT / "data"
REPORTS_DIR = DATA_DIR / "reports"

# Map command names to report subdirectories
REPORT_SUBDIRS = {
    "today": "daily",
    "this_week": "weekly",
    "my_team": "team",
    "weekly_report": "weekly-report",
}


# ---------------------------------------------------------------------------
# YAML front matter parser (stdlib only, handles our simple schema)
# ---------------------------------------------------------------------------

def parse_front_matter(filepath: Path) -> dict:
    """Parse YAML front matter from a markdown file. Returns dict or empty."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    m = re.match(r"^---\s*\n(.*?\n)---", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        # Handle arrays like [a, b] or []
        if val.startswith("["):
            inner = val.strip("[]").strip()
            if inner:
                fm[key] = [v.strip().strip('"').strip("'") for v in inner.split(",")]
            else:
                fm[key] = []
        # Handle empty values
        elif val == "" or val == "null":
            fm[key] = None
        # Handle quoted strings
        elif (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            fm[key] = val[1:-1]
        else:
            fm[key] = val
    return fm


def extract_title(filepath: Path) -> str:
    """Extract the first markdown heading from a file."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return filepath.stem
    for line in text.splitlines():
        m = re.match(r"^#{1,3}\s+(.+)", line)
        if m:
            title = m.group(1).strip()
            if title.startswith("[") and title.endswith("]"):
                title = title[1:-1]
            return title
    return filepath.stem


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_all_tasks() -> list[dict]:
    """Scan vault for all task files, return list of parsed dicts."""
    tasks = []
    projects_dir = DATA_DIR / "projects"
    if not projects_dir.exists():
        return tasks

    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        slug = project_dir.name

        # Project-level tasks (may be in tasks/*.md or tasks/YYYY/*.md)
        tasks_dir = project_dir / "tasks"
        if tasks_dir.exists():
            for tf in sorted(tasks_dir.rglob("*.md")):
                fm = parse_front_matter(tf)
                if fm.get("type") != "task":
                    continue
                fm["_file"] = tf
                fm["_title"] = extract_title(tf)
                fm.setdefault("project", slug)
                fm.setdefault("stream", None)
                tasks.append(fm)

        # Stream tasks (may be in tasks/*.md or tasks/YYYY/*.md)
        streams_dir = project_dir / "streams"
        if streams_dir.exists():
            for stream_dir in sorted(streams_dir.iterdir()):
                if not stream_dir.is_dir():
                    continue
                stream_tasks_dir = stream_dir / "tasks"
                if not stream_tasks_dir.exists():
                    continue
                for tf in sorted(stream_tasks_dir.rglob("*.md")):
                    fm = parse_front_matter(tf)
                    if fm.get("type") != "task":
                        continue
                    fm["_file"] = tf
                    fm["_title"] = extract_title(tf)
                    fm.setdefault("project", slug)
                    fm.setdefault("stream", stream_dir.name)
                    tasks.append(fm)

    return tasks


def load_team() -> dict[str, dict]:
    """Load team members. Returns dict keyed by first_name."""
    team = {}
    team_dir = DATA_DIR / "team"
    if not team_dir.exists():
        return team
    for tf in sorted(team_dir.glob("*.md")):
        fm = parse_front_matter(tf)
        if fm.get("type") != "team-member":
            continue
        key = fm.get("first_name") or fm.get("full_name") or tf.stem
        team[key] = fm
    return team


def load_projects() -> list[dict]:
    """Load all project.md files."""
    projects = []
    projects_dir = DATA_DIR / "projects"
    if not projects_dir.exists():
        return projects
    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        pf = project_dir / "project.md"
        if pf.exists():
            fm = parse_front_matter(pf)
            fm["_slug"] = project_dir.name
            fm["_title"] = extract_title(pf)
            projects.append(fm)
    return projects


def load_streams(project_slug: str) -> list[dict]:
    """Load all stream.md files for a project."""
    streams = []
    streams_dir = DATA_DIR / "projects" / project_slug / "streams"
    if not streams_dir.exists():
        return streams
    for stream_dir in sorted(streams_dir.iterdir()):
        if not stream_dir.is_dir():
            continue
        sf = stream_dir / "stream.md"
        if sf.exists():
            fm = parse_front_matter(sf)
            fm["_slug"] = stream_dir.name
            fm["_title"] = extract_title(sf)
            streams.append(fm)
    return streams


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
PRIORITY_ICONS = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}


def priority_sort_key(task: dict):
    p = (task.get("priority") or "medium").lower()
    due = task.get("due_date") or "9999-99-99"
    return (PRIORITY_ORDER.get(p, 2), due)


def fmt_priority(task: dict) -> str:
    p = (task.get("priority") or "medium").lower()
    icon = PRIORITY_ICONS.get(p, "🟡")
    return f"{icon} {p}"


def fmt_due(task: dict) -> str:
    d = task.get("due_date")
    return d if d else "No due date"


def parse_date(s) -> date | None:
    if not s or not isinstance(s, str):
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def working_days_between(start: date, end: date) -> int:
    """Count weekdays (Mon-Fri) from start (inclusive) to end (exclusive)."""
    if start >= end:
        return 0
    count = 0
    current = start
    while current < end:
        if current.weekday() < 5:  # Mon=0 ... Fri=4
            count += 1
        current += timedelta(days=1)
    return count


def week_bounds(today: date) -> tuple[date, date]:
    """Return (monday, sunday) of the current week."""
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def project_display_name(slug: str) -> str:
    """Convert slug to display name."""
    pf = DATA_DIR / "projects" / slug / "project.md"
    if pf.exists():
        return extract_title(pf)
    return slug.replace("-", " ").title()


def stream_display_name(project_slug: str, stream_slug: str) -> str:
    sf = DATA_DIR / "projects" / project_slug / "streams" / stream_slug / "stream.md"
    if sf.exists():
        return extract_title(sf)
    return stream_slug.replace("-", " ").title()


# ---------------------------------------------------------------------------
# Dashboard: today
# ---------------------------------------------------------------------------

def cmd_today():
    today = date.today()
    tasks = load_all_tasks()

    overdue = []
    due_today = []
    in_progress = []
    blocked = []

    for t in tasks:
        status = (t.get("status") or "").lower()
        if status == "done":
            continue
        due = parse_date(t.get("due_date"))

        if due and due < today and status != "done":
            overdue.append(t)
        if due and due == today:
            due_today.append(t)
        if status == "in-progress":
            in_progress.append(t)
        if status == "blocked":
            blocked.append(t)

    print(f"# 📋 Daily Dashboard — {today}")
    print()

    def print_section(title, items):
        print(f"## {title}")
        print()
        if not items:
            print("None")
            print()
            return
        items.sort(key=priority_sort_key)
        # Group by project -> stream
        grouped = defaultdict(lambda: defaultdict(list))
        for t in items:
            proj = t.get("project") or "Unknown"
            stream = t.get("stream") or "(Project-level)"
            grouped[proj][stream].append(t)

        for proj in sorted(grouped):
            print(f"### {project_display_name(proj)}")
            for stream in sorted(grouped[proj]):
                if stream != "(Project-level)":
                    print(f"#### {stream_display_name(proj, stream)}")
                else:
                    print(f"#### {stream}")
                for t in grouped[proj][stream]:
                    tid = t.get("id") or "???"
                    title = t["_title"]
                    owner = t.get("owner") or "Unassigned"
                    print(f"- {fmt_priority(t)} **{tid}** — {title} | Owner: {owner} | Due: {fmt_due(t)}")
                print()

    print_section("🔴 Overdue", overdue)
    print_section("📅 Due Today", due_today)
    print_section("🔄 In Progress", in_progress)
    print_section("🚫 Blocked", blocked)


# ---------------------------------------------------------------------------
# Dashboard: this_week
# ---------------------------------------------------------------------------

def cmd_this_week():
    today = date.today()
    monday, _ = week_bounds(today)
    tasks = load_all_tasks()
    projects = load_projects()

    print(f"# 📊 Weekly Dashboard — Week of {monday}")
    print()

    if not projects:
        print("No projects found.")
        return

    for proj in projects:
        slug = proj["_slug"]
        pstatus = proj.get("status") or "active"
        print(f"## Project: {proj['_title']} ({pstatus})")
        print()

        proj_tasks = [t for t in tasks if t.get("project") == slug and (t.get("status") or "").lower() != "done"]
        streams = load_streams(slug)

        # Stream tasks
        for stream in streams:
            sslug = stream["_slug"]
            sstatus = stream.get("status") or "active"
            stream_tasks = [t for t in proj_tasks if t.get("stream") == sslug]
            stream_tasks.sort(key=priority_sort_key)

            print(f"### Stream: {stream['_title']} ({sstatus})")
            print()
            if stream_tasks:
                print("| ID | Task | Owner | Priority | Status | Due |")
                print("|----|------|-------|----------|--------|-----|")
                for t in stream_tasks:
                    tid = t.get("id") or "???"
                    title = t["_title"]
                    owner = t.get("owner") or "Unassigned"
                    status = t.get("status") or "todo"
                    print(f"| {tid} | {title} | {owner} | {fmt_priority(t)} | {status} | {fmt_due(t)} |")
            else:
                print("No open tasks.")
            print()

        # Project-level tasks
        plevel = [t for t in proj_tasks if not t.get("stream")]
        plevel.sort(key=priority_sort_key)
        if plevel:
            print("### (Project-level tasks)")
            print()
            print("| ID | Task | Owner | Priority | Status | Due |")
            print("|----|------|-------|----------|--------|-----|")
            for t in plevel:
                tid = t.get("id") or "???"
                title = t["_title"]
                owner = t.get("owner") or "Unassigned"
                status = t.get("status") or "todo"
                print(f"| {tid} | {title} | {owner} | {fmt_priority(t)} | {status} | {fmt_due(t)} |")
            print()

        print("---")
        print()


# ---------------------------------------------------------------------------
# Dashboard: my_team
# ---------------------------------------------------------------------------

def cmd_my_team():
    today = date.today()
    tasks = load_all_tasks()
    team = load_team()

    open_tasks = [t for t in tasks if (t.get("status") or "").lower() not in ("done",)]

    # Group by owner
    by_owner = defaultdict(list)
    for t in open_tasks:
        owner = t.get("owner") or "Unassigned"
        by_owner[owner].append(t)

    print(f"# 👥 Team Workload — {today}")
    print()

    # Sort owners: team members first (alphabetical), then Unassigned
    owners = sorted(by_owner.keys(), key=lambda o: (o == "Unassigned", o.lower()))

    for owner in owners:
        member = team.get(owner, {})
        role = member.get("role") or ""
        owner_tasks = by_owner[owner]
        owner_tasks.sort(key=priority_sort_key)

        role_str = f" — {role}" if role else ""
        print(f"## {owner}{role_str}")
        print(f"**Open tasks**: {len(owner_tasks)}")
        print()
        print("| ID | Task | Project | Stream | Priority | Status | Due | Days Open |")
        print("|----|------|---------|--------|----------|--------|-----|-----------|")

        for t in owner_tasks:
            tid = t.get("id") or "???"
            title = t["_title"]
            proj = project_display_name(t.get("project") or "")
            stream = t.get("stream") or "—"
            if stream != "—":
                stream = stream_display_name(t.get("project") or "", stream)
            status = t.get("status") or "todo"
            created = parse_date(t.get("created"))
            days = working_days_between(created, today) if created else "?"
            warn = "⚠️ " if isinstance(days, int) and days > 14 else ""
            print(f"| {warn}{tid} | {title} | {proj} | {stream} | {fmt_priority(t)} | {status} | {fmt_due(t)} | {days} |")

        print()
        print("---")
        print()

    # Summary table
    print("## Summary")
    print()
    print("| Member | Open | In Progress | Blocked | Oldest Task (days) |")
    print("|--------|------|-------------|---------|---------------------|")
    for owner in owners:
        owner_tasks = by_owner[owner]
        open_count = len(owner_tasks)
        ip = sum(1 for t in owner_tasks if (t.get("status") or "").lower() == "in-progress")
        bl = sum(1 for t in owner_tasks if (t.get("status") or "").lower() == "blocked")
        ages = []
        for t in owner_tasks:
            created = parse_date(t.get("created"))
            if created:
                ages.append(working_days_between(created, today))
        oldest = max(ages) if ages else "?"
        print(f"| {owner} | {open_count} | {ip} | {bl} | {oldest} |")
    print()


# ---------------------------------------------------------------------------
# Dashboard: weekly_report
# ---------------------------------------------------------------------------

def cmd_weekly_report():
    today = date.today()
    monday, sunday = week_bounds(today)
    tasks = load_all_tasks()

    completed = []
    in_progress = []
    blocked = []
    new_this_week = []

    for t in tasks:
        status = (t.get("status") or "").lower()
        completed_date = parse_date(t.get("completed_date"))
        created_date = parse_date(t.get("created"))

        if status == "done" and completed_date and monday <= completed_date <= sunday:
            completed.append(t)
        if status == "in-progress":
            in_progress.append(t)
        if status == "blocked":
            blocked.append(t)
        if created_date and monday <= created_date <= sunday and status != "done":
            new_this_week.append(t)

    total_open = sum(1 for t in tasks if (t.get("status") or "").lower() not in ("done",))

    print(f"# 📝 Weekly Report — Week of {monday}")
    print()

    # Completed
    print("## ✅ Completed This Week")
    print()
    if completed:
        completed.sort(key=lambda t: t.get("completed_date") or "")
        print("| ID | Task | Project | Owner | Completed |")
        print("|----|------|---------|-------|-----------|")
        for t in completed:
            tid = t.get("id") or "???"
            title = t["_title"]
            proj = project_display_name(t.get("project") or "")
            owner = t.get("owner") or "Unassigned"
            cd = t.get("completed_date") or "?"
            print(f"| {tid} | {title} | {proj} | {owner} | {cd} |")
    else:
        print("None")
    print()

    # In Progress
    print("## 🔄 In Progress")
    print()
    if in_progress:
        in_progress.sort(key=priority_sort_key)
        print("| ID | Task | Project | Owner | Priority | Due |")
        print("|----|------|---------|-------|----------|-----|")
        for t in in_progress:
            tid = t.get("id") or "???"
            title = t["_title"]
            proj = project_display_name(t.get("project") or "")
            owner = t.get("owner") or "Unassigned"
            print(f"| {tid} | {title} | {proj} | {owner} | {fmt_priority(t)} | {fmt_due(t)} |")
    else:
        print("None")
    print()

    # Blocked
    print("## 🚫 Blocked")
    print()
    if blocked:
        blocked.sort(key=priority_sort_key)
        print("| ID | Task | Project | Owner | Priority | Created |")
        print("|----|------|---------|-------|----------|---------|")
        for t in blocked:
            tid = t.get("id") or "???"
            title = t["_title"]
            proj = project_display_name(t.get("project") or "")
            owner = t.get("owner") or "Unassigned"
            created = t.get("created") or "?"
            print(f"| {tid} | {title} | {proj} | {owner} | {fmt_priority(t)} | {created} |")
    else:
        print("None")
    print()

    # New this week
    print("## 🆕 New This Week")
    print()
    if new_this_week:
        new_this_week.sort(key=priority_sort_key)
        print("| ID | Task | Project | Owner | Priority | Due |")
        print("|----|------|---------|-------|----------|-----|")
        for t in new_this_week:
            tid = t.get("id") or "???"
            title = t["_title"]
            proj = project_display_name(t.get("project") or "")
            owner = t.get("owner") or "Unassigned"
            print(f"| {tid} | {title} | {proj} | {owner} | {fmt_priority(t)} | {fmt_due(t)} |")
    else:
        print("None")
    print()

    # Summary
    print("## 📊 Summary")
    print()
    print(f"- Tasks completed: {len(completed)}")
    print(f"- Tasks in progress: {len(in_progress)}")
    print(f"- Tasks blocked: {len(blocked)}")
    print(f"- New tasks created: {len(new_this_week)}")
    print(f"- Total open tasks: {total_open}")
    print()


# ---------------------------------------------------------------------------
# Main — capture output, save to reports/, print to stdout
# ---------------------------------------------------------------------------

COMMANDS = {
    "today": cmd_today,
    "this_week": cmd_this_week,
    "my_team": cmd_my_team,
    "weekly_report": cmd_weekly_report,
}


def run_and_save(command_name: str):
    """Run a dashboard command, capture its output, save to reports/, print to stdout."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    # Determine filename: weekly dashboards use Monday date, others use today
    if command_name in ("this_week", "weekly_report"):
        file_date = monday
    else:
        file_date = today

    subdir = REPORT_SUBDIRS[command_name]
    year = str(file_date.year)
    report_dir = REPORTS_DIR / subdir / year
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{file_date}.md"

    # Capture stdout into a buffer
    real_stdout = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf

    COMMANDS[command_name]()

    sys.stdout = real_stdout
    output = buf.getvalue()

    # Save to file
    report_path.write_text(output, encoding="utf-8")

    # Print to stdout
    print(output, end="")

    # Print save confirmation to stderr (so it doesn't mix with dashboard output)
    print(f"\n> Saved to {report_path.relative_to(VAULT)}", file=sys.stderr)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python {sys.argv[0]} <{'|'.join(COMMANDS)}>")
        sys.exit(1)

    if not DATA_DIR.exists():
        print("Error: data/ directory not found.", file=sys.stderr)
        print("", file=sys.stderr)
        print("plainpm stores user data (projects, team, meetings, reports) in the data/ directory.", file=sys.stderr)
        print("Create it with the required structure:", file=sys.stderr)
        print("", file=sys.stderr)
        print("  data/", file=sys.stderr)
        print("  ├── projects/", file=sys.stderr)
        print("  │   └── _index.md", file=sys.stderr)
        print("  ├── team/", file=sys.stderr)
        print("  ├── meetings/", file=sys.stderr)
        print("  │   ├── transcripts/", file=sys.stderr)
        print("  │   └── notes/", file=sys.stderr)
        print("  └── reports/", file=sys.stderr)
        print("", file=sys.stderr)
        print("Or use a slash command like /new-task to create it automatically.", file=sys.stderr)
        sys.exit(1)

    run_and_save(sys.argv[1])


if __name__ == "__main__":
    main()
