#!/usr/bin/env python3
"""plainpm Dashboard Generator.

Usage:
    python scripts/dashboard.py today
    python scripts/dashboard.py this_week
    python scripts/dashboard.py my_team
    python scripts/dashboard.py weekly_report
    python scripts/dashboard.py owner <first_name>
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

# Resolve project root (script lives in scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = DATA_DIR / "reports"

# Map command names to report subdirectories
REPORT_SUBDIRS = {
    "today": "daily",
    "this_week": "weekly",
    "my_team": "team",
    "weekly_report": "weekly-report",
    "owner": "owner",
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
        # Handle inline maps like {Alice: 2026-04-08, Bob: null}
        elif val.startswith("{"):
            inner = val.strip("{}").strip()
            if inner:
                mapping = {}
                for pair in inner.split(","):
                    pair = pair.strip()
                    if ":" in pair:
                        k, _, v = pair.partition(":")
                        k = k.strip().strip('"').strip("'")
                        v = v.strip().strip('"').strip("'")
                        mapping[k] = None if v == "null" or v == "" else v
                fm[key] = mapping
            else:
                fm[key] = {}
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


def extract_latest_update(filepath: Path) -> str | None:
    """Return the most recent dated update from the Updates section.

    Handles both single-line and grouped (sub-bullet) formats:
        - 2026-04-06: Single update text
        - 2026-04-06:
          - First sub-bullet
          - Second sub-bullet

    For grouped entries, returns the last sub-bullet with "(+N more)" appended
    when there are additional entries for that date.
    """
    try:
        text = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    in_updates = False
    latest_date = None
    latest_subitems: list[str] = []
    current_date = None
    current_subitems: list[str] = []

    for line in text.splitlines():
        if re.match(r"^#{2,4}\s+Updates", line):
            in_updates = True
            continue
        if in_updates and re.match(r"^#{1,4}\s+", line):
            break
        if in_updates:
            # Top-level date bullet with inline text: - 2026-04-06: some text
            m = re.match(r"^-\s+(\d{4}-\d{2}-\d{2}):\s+(.+)", line)
            if m:
                # Save previous date group if it's the latest
                if current_date and (latest_date is None or current_date > latest_date):
                    latest_date = current_date
                    latest_subitems = current_subitems[:]
                current_date = m.group(1)
                current_subitems = [m.group(2).strip()]
                continue
            # Top-level date bullet without inline text: - 2026-04-06:
            m = re.match(r"^-\s+(\d{4}-\d{2}-\d{2}):\s*$", line)
            if m:
                if current_date and (latest_date is None or current_date > latest_date):
                    latest_date = current_date
                    latest_subitems = current_subitems[:]
                current_date = m.group(1)
                current_subitems = []
                continue
            # Sub-bullet under a date: "  - sub item text"
            m = re.match(r"^\s+-\s+(.+)", line)
            if m and current_date:
                current_subitems.append(m.group(1).strip())
                continue

    # Don't forget the last date group
    if current_date and (latest_date is None or current_date > latest_date):
        latest_date = current_date
        latest_subitems = current_subitems[:]

    if not latest_date or not latest_subitems:
        return None

    last_item = latest_subitems[-1]
    count = len(latest_subitems)
    if count > 1:
        return f"{latest_date}: {last_item} (+{count - 1} more)"
    return f"{latest_date}: {last_item}"


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_all_tasks() -> list[dict]:
    """Scan all projects and standalone tasks, return list of parsed dicts."""
    tasks = []

    # Standalone tasks (not tied to any project)
    standalone_dir = DATA_DIR / "tasks"
    if standalone_dir.exists():
        for tf in sorted(standalone_dir.rglob("*.md")):
            fm = parse_front_matter(tf)
            if fm.get("type") != "task":
                continue
            fm["_file"] = tf
            fm["_title"] = extract_title(tf)
            fm["_latest_update"] = extract_latest_update(tf)
            fm.setdefault("project", None)
            fm.setdefault("stream", None)
            tasks.append(fm)

    # Project and stream tasks
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
                fm["_latest_update"] = extract_latest_update(tf)
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
                    fm["_latest_update"] = extract_latest_update(tf)
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
            fm["_latest_update"] = extract_latest_update(pf)
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
            fm["_latest_update"] = extract_latest_update(sf)
            streams.append(fm)
    return streams


def load_all_streams() -> list[dict]:
    """Load all stream.md files across all projects."""
    streams = []
    projects_dir = DATA_DIR / "projects"
    if not projects_dir.exists():
        return streams
    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        for stream in load_streams(project_dir.name):
            stream["_project_slug"] = project_dir.name
            streams.append(stream)
    return streams


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
PRIORITY_ICONS = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
STATUS_ICONS = {"todo": "⬚", "in-progress": "🔄", "blocked": "🚫", "done": "✅"}


def task_owners(task: dict) -> list[str]:
    """Return the list of owner first_names for a task.

    Supports both the new 'owners' array field and the legacy 'owner' string field.
    Returns ['Unassigned'] when no owner is set.
    """
    owners = task.get("owners")
    if isinstance(owners, list) and owners:
        return owners
    # Legacy single-owner field
    legacy = task.get("owner")
    if legacy and isinstance(legacy, str):
        return [legacy]
    return ["Unassigned"]


def entity_owners(entity: dict) -> list[str]:
    """Return the list of owner first_names for a project or stream.

    Supports the 'owners' array field and a legacy 'owner' string field.
    Returns ['Unassigned'] when no owner is set.
    """
    owners = entity.get("owners")
    if isinstance(owners, list) and owners:
        return owners
    legacy = entity.get("owner")
    if legacy and isinstance(legacy, str):
        return [legacy]
    return ["Unassigned"]


def fmt_entity_owners(entity: dict) -> str:
    """Format project/stream owners for display (co-owners joined with ' / ')."""
    return " / ".join(entity_owners(entity))


def fmt_owners(task: dict) -> str:
    """Format the owners for display in dashboard tables.

    For completion_mode: all tasks, appends ✅ / ⬚ per member if completions exist.
    """
    owners = task_owners(task)
    mode = (task.get("completion_mode") or "any").lower()
    completions = task.get("completions")

    if mode == "all" and isinstance(completions, dict):
        parts = []
        for o in owners:
            done = completions.get(o)
            icon = "✅" if done and done != "null" else "⬚"
            parts.append(f"{o} {icon}")
        return " / ".join(parts)

    return " / ".join(owners)



def priority_sort_key(task: dict):
    p = (task.get("priority") or "medium").lower()
    due = task.get("due_date") or "9999-99-99"
    return (PRIORITY_ORDER.get(p, 2), due)


def fmt_priority(task: dict) -> str:
    p = (task.get("priority") or "medium").lower()
    icon = PRIORITY_ICONS.get(p, "🟡")
    return f"{icon} {p}"


def fmt_status(task: dict) -> str:
    s = (task.get("status") or "todo").lower()
    icon = STATUS_ICONS.get(s, "⬚")
    return f"{icon} {s}"


def fmt_due(task: dict) -> str:
    d = task.get("due_date")
    return d if d else "No due date"


MAX_UPDATE_LEN = 60


def fmt_latest_update(task: dict) -> str:
    update = task.get("_latest_update") or ""
    if len(update) > MAX_UPDATE_LEN:
        update = update[:MAX_UPDATE_LEN - 3] + "..."
    return update or "—"


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
    if not slug:
        return "(Standalone)"
    pf = DATA_DIR / "projects" / slug / "project.md"
    if pf.exists():
        return extract_title(pf)
    return slug.replace("-", " ").title()


def stream_display_name(project_slug: str, stream_slug: str) -> str:
    if not project_slug:
        return stream_slug.replace("-", " ").title() if stream_slug else ""
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
    not_started = []
    completed = []

    for t in tasks:
        status = (t.get("status") or "").lower()
        due = parse_date(t.get("due_date"))

        if status == "done":
            completed_date = parse_date(t.get("completed_date"))
            if completed_date and completed_date == today:
                completed.append(t)
            continue
        if due and due < today:
            overdue.append(t)
        if due and due == today:
            due_today.append(t)
        if status == "in-progress":
            in_progress.append(t)
        if status == "blocked":
            blocked.append(t)
        if status == "todo" and not (due and due < today):
            not_started.append(t)

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
            proj = t.get("project") or ""
            stream = t.get("stream") or "(Project-level)"
            grouped[proj][stream].append(t)

        for proj in sorted(grouped):
            print(f"### {project_display_name(proj)}")
            if proj:
                pf = DATA_DIR / "projects" / proj / "project.md"
                pfm = parse_front_matter(pf) if pf.exists() else {}
                proj_owner = fmt_entity_owners(pfm) if pfm else "Unassigned"
                proj_latest = extract_latest_update(pf) if pf.exists() else None
                meta = []
                if proj_owner != "Unassigned":
                    meta.append(f"> Owner: {proj_owner}")
                if proj_latest:
                    meta.append(f"> Latest: {proj_latest}")
                if meta:
                    for m in meta:
                        print(m)
                    print()
            for stream in sorted(grouped[proj]):
                if stream != "(Project-level)" and proj:
                    sf = DATA_DIR / "projects" / proj / "streams" / stream / "stream.md"
                    sfm = parse_front_matter(sf) if sf.exists() else {}
                    sstatus = sfm.get("status") or "active"
                    latest = extract_latest_update(sf) if sf.exists() else None
                    print(f"#### {stream_display_name(proj, stream)} ({sstatus})")
                    s_owner = fmt_entity_owners(sfm)
                    if s_owner != "Unassigned":
                        print(f"> Owner: {s_owner}")
                    if latest:
                        print(f"> Latest: {latest}")
                        print()
                else:
                    print(f"#### {stream}")
                print()
                has_deps = any(t.get("blocked_by") for t in grouped[proj][stream])
                if has_deps:
                    print("| ID | Task | Owner | Priority | Due | Blocked By | Latest Update |")
                    print("|----|------|-------|----------|-----|------------|---------------|")
                else:
                    print("| ID | Task | Owner | Priority | Due | Latest Update |")
                    print("|----|------|-------|----------|-----|---------------|")
                for t in grouped[proj][stream]:
                    tid = t.get("id") or "???"
                    title = t["_title"]
                    owner = fmt_owners(t)
                    update = fmt_latest_update(t)
                    blocked_by = t.get("blocked_by") or []
                    if has_deps:
                        dep_str = ", ".join(blocked_by) if blocked_by else "—"
                        print(f"| {tid} | {title} | {owner} | {fmt_priority(t)} | {fmt_due(t)} | {dep_str} | {update} |")
                    else:
                        print(f"| {tid} | {title} | {owner} | {fmt_priority(t)} | {fmt_due(t)} | {update} |")
                print()

    print_section("🔴 Overdue", overdue)
    print_section("📅 Due Today", due_today)
    print_section("🔄 In Progress", in_progress)
    print_section("🚫 Blocked", blocked)
    print_section("📋 Not Started", not_started)
    print_section("✅ Completed", completed)


# ---------------------------------------------------------------------------
# Dashboard: this_week
# ---------------------------------------------------------------------------

def cmd_this_week():
    today = date.today()
    monday, sunday = week_bounds(today)
    tasks = load_all_tasks()
    # Exclude done tasks unless completed this week
    tasks = [t for t in tasks if (t.get("status") or "").lower() != "done"
             or (parse_date(t.get("completed_date")) and monday <= parse_date(t.get("completed_date")) <= sunday)]
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
        powner = fmt_entity_owners(proj)
        if powner != "Unassigned":
            print(f"> Owner: {powner}")
        latest = proj.get("_latest_update")
        if latest:
            print(f"> Latest: {latest}")
        print()

        proj_tasks = [t for t in tasks if t.get("project") == slug]
        streams = load_streams(slug)

        # Stream tasks
        for stream in streams:
            sslug = stream["_slug"]
            sstatus = stream.get("status") or "active"
            stream_tasks = [t for t in proj_tasks if t.get("stream") == sslug]
            stream_tasks.sort(key=priority_sort_key)

            print(f"### Stream: {stream['_title']} ({sstatus})")
            sowner = fmt_entity_owners(stream)
            if sowner != "Unassigned":
                print(f"> Owner: {sowner}")
            latest = stream.get("_latest_update")
            if latest:
                print(f"> Latest: {latest}")
            print()
            if stream_tasks:
                print("| ID | Task | Owner | Priority | Status | Due | Latest Update |")
                print("|----|------|-------|----------|--------|-----|---------------|")
                for t in stream_tasks:
                    tid = t.get("id") or "???"
                    title = t["_title"]
                    owner = fmt_owners(t)
                    print(f"| {tid} | {title} | {owner} | {fmt_priority(t)} | {fmt_status(t)} | {fmt_due(t)} | {fmt_latest_update(t)} |")
            else:
                print("No open tasks.")
            print()

        # Project-level tasks
        plevel = [t for t in proj_tasks if not t.get("stream")]
        plevel.sort(key=priority_sort_key)
        if plevel:
            print("### (Project-level tasks)")
            print()
            print("| ID | Task | Owner | Priority | Status | Due | Latest Update |")
            print("|----|------|-------|----------|--------|-----|---------------|")
            for t in plevel:
                tid = t.get("id") or "???"
                title = t["_title"]
                owner = fmt_owners(t)
                print(f"| {tid} | {title} | {owner} | {fmt_priority(t)} | {fmt_status(t)} | {fmt_due(t)} | {fmt_latest_update(t)} |")
            print()

        print("---")
        print()

    # Standalone tasks (not tied to any project)
    standalone = [t for t in tasks if not t.get("project")]
    if standalone:
        standalone.sort(key=priority_sort_key)
        print("## Standalone Tasks")
        print()
        print("| ID | Task | Owner | Priority | Status | Due | Latest Update |")
        print("|----|------|-------|----------|--------|-----|---------------|")
        for t in standalone:
            tid = t.get("id") or "???"
            title = t["_title"]
            owner = fmt_owners(t)
            print(f"| {tid} | {title} | {owner} | {fmt_priority(t)} | {fmt_status(t)} | {fmt_due(t)} | {fmt_latest_update(t)} |")
        print()
        print("---")
        print()


# ---------------------------------------------------------------------------
# Dashboard: my_team
# ---------------------------------------------------------------------------

def cmd_my_team():
    today = date.today()
    tasks = load_all_tasks()
    # Exclude done tasks unless completed today
    tasks = [t for t in tasks if (t.get("status") or "").lower() != "done"
             or (parse_date(t.get("completed_date")) and parse_date(t.get("completed_date")) == today)]
    team = load_team()

    # Group by owner — multi-owner tasks appear under each assigned member
    by_owner = defaultdict(list)
    for t in tasks:
        for owner in task_owners(t):
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
        open_count = sum(1 for t in owner_tasks if (t.get("status") or "").lower() != "done")
        done_count = sum(1 for t in owner_tasks if (t.get("status") or "").lower() == "done")
        print(f"## {owner}{role_str}")
        print(f"**Open tasks**: {open_count} | **Completed today**: {done_count}")
        print()
        print("| ID | Task | Project | Stream | Priority | Status | Due | Days Open | Latest Update |")
        print("|----|------|---------|--------|----------|--------|-----|-----------|---------------|")

        for t in owner_tasks:
            tid = t.get("id") or "???"
            title = t["_title"]
            proj = project_display_name(t.get("project") or "")
            stream = t.get("stream") or "—"
            if stream != "—":
                stream = stream_display_name(t.get("project") or "", stream)
            created = parse_date(t.get("created"))
            days = working_days_between(created, today) if created else "?"
            warn = "⚠️ " if isinstance(days, int) and days > 14 else ""
            print(f"| {warn}{tid} | {title} | {proj} | {stream} | {fmt_priority(t)} | {fmt_status(t)} | {fmt_due(t)} | {days} | {fmt_latest_update(t)} |")

        print()
        print("---")
        print()

    # Project status
    projects = load_projects()
    active_projects = [p for p in projects if (p.get("status") or "active") != "completed"]
    if active_projects:
        print("## Project Status")
        print()
        print("| Project | Owner | Status | Latest Update |")
        print("|---------|-------|--------|---------------|")
        for p in active_projects:
            pstatus = p.get("status") or "active"
            latest = p.get("_latest_update") or "—"
            print(f"| {p['_title']} | {fmt_entity_owners(p)} | {pstatus} | {latest} |")
        print()

    # Stream status
    all_streams = load_all_streams()
    active_streams = [s for s in all_streams if (s.get("status") or "active") != "completed"]
    if active_streams:
        print("## Stream Status")
        print()
        print("| Project | Stream | Owner | Status | Latest Update |")
        print("|---------|--------|-------|--------|---------------|")
        for s in active_streams:
            proj_name = project_display_name(s["_project_slug"])
            sstatus = s.get("status") or "active"
            latest = s.get("_latest_update") or "—"
            print(f"| {proj_name} | {s['_title']} | {fmt_entity_owners(s)} | {sstatus} | {latest} |")
        print()

    # Summary table
    print("## Summary")
    print()
    print("| Member | Open | In Progress | Blocked | Completed Today | Oldest Task (days) |")
    print("|--------|------|-------------|---------|-----------------|---------------------|")
    for owner in owners:
        owner_tasks = by_owner[owner]
        open_count = sum(1 for t in owner_tasks if (t.get("status") or "").lower() != "done")
        done_count = sum(1 for t in owner_tasks if (t.get("status") or "").lower() == "done")
        ip = sum(1 for t in owner_tasks if (t.get("status") or "").lower() == "in-progress")
        bl = sum(1 for t in owner_tasks if (t.get("status") or "").lower() == "blocked")
        ages = []
        for t in owner_tasks:
            created = parse_date(t.get("created"))
            if created:
                ages.append(working_days_between(created, today))
        oldest = max(ages) if ages else "?"
        print(f"| {owner} | {open_count} | {ip} | {bl} | {done_count} | {oldest} |")
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
        print("| ID | Task | Project | Owner | Completed | Latest Update |")
        print("|----|------|---------|-------|-----------|---------------|")
        for t in completed:
            tid = t.get("id") or "???"
            title = t["_title"]
            proj = project_display_name(t.get("project") or "")
            owner = fmt_owners(t)
            cd = t.get("completed_date") or "?"
            print(f"| {tid} | {title} | {proj} | {owner} | {cd} | {fmt_latest_update(t)} |")
    else:
        print("None")
    print()

    # In Progress
    print("## 🔄 In Progress")
    print()
    if in_progress:
        in_progress.sort(key=priority_sort_key)
        print("| ID | Task | Project | Owner | Priority | Due | Latest Update |")
        print("|----|------|---------|-------|----------|-----|---------------|")
        for t in in_progress:
            tid = t.get("id") or "???"
            title = t["_title"]
            proj = project_display_name(t.get("project") or "")
            owner = fmt_owners(t)
            print(f"| {tid} | {title} | {proj} | {owner} | {fmt_priority(t)} | {fmt_due(t)} | {fmt_latest_update(t)} |")
    else:
        print("None")
    print()

    # Blocked
    print("## 🚫 Blocked")
    print()
    if blocked:
        blocked.sort(key=priority_sort_key)
        print("| ID | Task | Project | Owner | Priority | Created | Latest Update |")
        print("|----|------|---------|-------|----------|---------|---------------|")
        for t in blocked:
            tid = t.get("id") or "???"
            title = t["_title"]
            proj = project_display_name(t.get("project") or "")
            owner = fmt_owners(t)
            created = t.get("created") or "?"
            print(f"| {tid} | {title} | {proj} | {owner} | {fmt_priority(t)} | {created} | {fmt_latest_update(t)} |")
    else:
        print("None")
    print()

    # New this week
    print("## 🆕 New This Week")
    print()
    if new_this_week:
        new_this_week.sort(key=priority_sort_key)
        print("| ID | Task | Project | Owner | Priority | Due | Latest Update |")
        print("|----|------|---------|-------|----------|-----|---------------|")
        for t in new_this_week:
            tid = t.get("id") or "???"
            title = t["_title"]
            proj = project_display_name(t.get("project") or "")
            owner = fmt_owners(t)
            print(f"| {tid} | {title} | {proj} | {owner} | {fmt_priority(t)} | {fmt_due(t)} | {fmt_latest_update(t)} |")
    else:
        print("None")
    print()

    # Project status
    projects = load_projects()
    active_projects = [p for p in projects if (p.get("status") or "active") != "completed"]
    if active_projects:
        print("## 📁 Project Status")
        print()
        print("| Project | Owner | Status | Latest Update |")
        print("|---------|-------|--------|---------------|")
        for p in active_projects:
            pstatus = p.get("status") or "active"
            latest = p.get("_latest_update") or "—"
            print(f"| {p['_title']} | {fmt_entity_owners(p)} | {pstatus} | {latest} |")
        print()

    # Stream status
    all_streams = load_all_streams()
    active_streams = [s for s in all_streams if (s.get("status") or "active") != "completed"]
    if active_streams:
        print("## 🌊 Stream Status")
        print()
        print("| Project | Stream | Owner | Status | Latest Update |")
        print("|---------|--------|-------|--------|---------------|")
        for s in active_streams:
            proj_name = project_display_name(s["_project_slug"])
            sstatus = s.get("status") or "active"
            latest = s.get("_latest_update") or "—"
            print(f"| {proj_name} | {s['_title']} | {fmt_entity_owners(s)} | {sstatus} | {latest} |")
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
# Dashboard: owner (projects & streams owned by a specific person)
# ---------------------------------------------------------------------------

def cmd_owner(owner: str):
    today = date.today()
    projects = load_projects()
    all_streams = load_all_streams()
    tasks = load_all_tasks()

    def owns(entity: dict) -> bool:
        names = [o.lower() for o in entity_owners(entity)]
        return owner.lower() in names

    def counts(items: list[dict]) -> tuple[int, int]:
        open_n = sum(1 for t in items if (t.get("status") or "").lower() != "done")
        blocked_n = sum(1 for t in items if (t.get("status") or "").lower() == "blocked")
        return open_n, blocked_n

    owned_projects = [p for p in projects if owns(p)]
    owned_streams = [s for s in all_streams if owns(s)]

    print(f"# 👤 Owner Report: {owner} — {today}")
    print()
    print(f"**Projects owned**: {len(owned_projects)} | **Streams owned**: {len(owned_streams)}")
    print()

    if not owned_projects and not owned_streams:
        print(f"{owner} does not own any projects or streams.")
        return

    print("## 📁 Projects Owned")
    print()
    if owned_projects:
        print("| Project | Status | Open | Blocked | Latest Update |")
        print("|---------|--------|------|---------|---------------|")
        for p in owned_projects:
            # Roll up all tasks under the project (project-level + all streams)
            ptasks = [t for t in tasks if t.get("project") == p["_slug"]]
            open_n, blocked_n = counts(ptasks)
            pstatus = p.get("status") or "active"
            latest = p.get("_latest_update") or "—"
            print(f"| {p['_title']} | {pstatus} | {open_n} | {blocked_n} | {latest} |")
    else:
        print("None")
    print()

    print("## 🌊 Streams Owned")
    print()
    if owned_streams:
        print("| Project | Stream | Status | Open | Blocked | Latest Update |")
        print("|---------|--------|--------|------|---------|---------------|")
        for s in owned_streams:
            stasks = [t for t in tasks
                      if t.get("project") == s["_project_slug"] and t.get("stream") == s["_slug"]]
            open_n, blocked_n = counts(stasks)
            proj_name = project_display_name(s["_project_slug"])
            sstatus = s.get("status") or "active"
            latest = s.get("_latest_update") or "—"
            print(f"| {proj_name} | {s['_title']} | {sstatus} | {open_n} | {blocked_n} | {latest} |")
    else:
        print("None")
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


def run_and_save(command_name: str, owner: str | None = None):
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
    month = f"{file_date.month:02d}"
    report_dir = REPORTS_DIR / subdir / year / month
    report_dir.mkdir(parents=True, exist_ok=True)
    if command_name == "owner":
        owner_slug = re.sub(r"[^a-z0-9]+", "-", (owner or "").lower()).strip("-") or "owner"
        report_path = report_dir / f"{file_date}-{owner_slug}-owner.md"
    else:
        report_path = report_dir / f"{file_date}-{subdir}.md"

    # Capture stdout into a buffer
    real_stdout = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf

    if command_name == "owner":
        cmd_owner(owner)
    else:
        COMMANDS[command_name]()

    sys.stdout = real_stdout
    output = buf.getvalue()

    # Save to file
    report_path.write_text(output, encoding="utf-8")

    # Print to stdout
    print(output, end="")

    # Print save confirmation to stderr (so it doesn't mix with dashboard output)
    print(f"\n> Saved to {report_path.relative_to(PROJECT_ROOT)}", file=sys.stderr)


def main():
    valid = list(COMMANDS) + ["owner"]
    if len(sys.argv) < 2 or sys.argv[1] not in valid:
        print(f"Usage: python {sys.argv[0]} <{'|'.join(COMMANDS)}|owner <first_name>>")
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
        print("  ├── tasks/", file=sys.stderr)
        print("  ├── team/", file=sys.stderr)
        print("  ├── meetings/", file=sys.stderr)
        print("  │   ├── transcripts/", file=sys.stderr)
        print("  │   ├── notes/", file=sys.stderr)
        print("  │   └── areas/", file=sys.stderr)
        print("  └── reports/", file=sys.stderr)
        print("", file=sys.stderr)
        print("Or use a slash command like /new-task to create it automatically.", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "owner":
        if len(sys.argv) < 3 or not " ".join(sys.argv[2:]).strip():
            print("Usage: python scripts/dashboard.py owner <first_name>", file=sys.stderr)
            sys.exit(1)
        run_and_save("owner", " ".join(sys.argv[2:]).strip())
    else:
        run_and_save(sys.argv[1])


if __name__ == "__main__":
    main()
