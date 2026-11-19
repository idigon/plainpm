#!/usr/bin/env python3
"""plainpm Dashboard Generator.

Usage:
    python scripts/dashboard.py today
    python scripts/dashboard.py this_week
    python scripts/dashboard.py my_team
    python scripts/dashboard.py weekly_report
    python scripts/dashboard.py owner <first_name>
    python scripts/dashboard.py timeline [project-slug]
    python scripts/dashboard.py check
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
    "timeline": "timeline",
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


def load_archived_tasks() -> list[dict]:
    """Load archived tasks from data/archive/. Used for progress roll-ups only,
    so archiving finished work doesn't change a project's or stream's progress."""
    tasks = []
    archive_dir = DATA_DIR / "archive"
    if not archive_dir.exists():
        return tasks
    for tf in sorted(archive_dir.rglob("*.md")):
        fm = parse_front_matter(tf)
        if fm.get("type") != "task":
            continue
        fm["_file"] = tf
        fm["_title"] = extract_title(tf)
        fm["_archived"] = True
        tasks.append(fm)
    return tasks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TASK_STATUSES = ("todo", "in-progress", "blocked", "done", "cancelled")
CLOSED_STATUSES = {"done", "cancelled"}
ENTITY_STATUSES = ("active", "on-hold", "completed")
PRIORITIES = ("critical", "high", "medium", "low")
HEALTH_VALUES = ("on-track", "at-risk", "off-track")
COMPLETION_MODES = ("any", "all")

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
PRIORITY_ICONS = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
STATUS_ICONS = {"todo": "⬚", "in-progress": "🔄", "blocked": "🚫", "done": "✅", "cancelled": "✖️"}
HEALTH_ICONS = {"on-track": "🟢", "at-risk": "🟡", "off-track": "🔴"}


def task_status(task: dict) -> str:
    s = task.get("status")
    return s.lower() if isinstance(s, str) else ""


def is_open(task: dict) -> bool:
    """A task is open until it is done or cancelled."""
    return task_status(task) not in CLOSED_STATUSES


def closed_date(task: dict) -> date | None:
    """The date a closed task was completed or cancelled (None for open tasks)."""
    status = task_status(task)
    if status == "done":
        return parse_date(task.get("completed_date"))
    if status == "cancelled":
        return parse_date(task.get("cancelled_date"))
    return None


def print_table_header(headers: list[str]):
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join("-" * (len(h) + 2) for h in headers) + "|")


def print_row(cells: list):
    print("| " + " | ".join(str(c) for c in cells) + " |")


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
    if not d:
        return "No due date"
    due = parse_date(d)
    if due and due < date.today() and is_open(task):
        return f"⚠️ {d}"
    return d


def fmt_start(task: dict) -> str:
    return task.get("start_date") or "—"


MAX_UPDATE_LEN = 60


def fmt_latest_update(task: dict) -> str:
    update = task.get("_latest_update") or ""
    if len(update) > MAX_UPDATE_LEN:
        update = update[:MAX_UPDATE_LEN - 3] + "..."
    return update or "—"


# --- Project / stream schedule, health, and progress ---

def entity_status(entity: dict) -> str:
    s = entity.get("status") or "active"
    return s.lower() if isinstance(s, str) else "active"


def entity_is_late(entity: dict) -> bool:
    """True when a project/stream is past its target_date and not completed."""
    target = parse_date(entity.get("target_date"))
    return bool(target and target < date.today() and entity_status(entity) != "completed")


def fmt_health(entity: dict) -> str:
    h = str(entity.get("health") or "").lower()
    if not h:
        return "—"
    return f"{HEALTH_ICONS.get(h, '⬚')} {h}"


def fmt_target(entity: dict) -> str:
    t = entity.get("target_date")
    if not t:
        return "—"
    return f"⚠️ {t}" if entity_is_late(entity) else t


def tasks_in(tasks: list[dict], project_slug: str, stream_slug: str | None = None) -> list[dict]:
    """Tasks of a project (all streams + project-level), or of one of its streams."""
    return [t for t in tasks if t.get("project") == project_slug
            and (stream_slug is None or t.get("stream") == stream_slug)]


def fmt_progress(tasks: list[dict]) -> str:
    """Share of non-cancelled tasks that are done, e.g. '60% (6/10)'."""
    counted = [t for t in tasks if task_status(t) != "cancelled"]
    if not counted:
        return "—"
    done = sum(1 for t in counted if task_status(t) == "done")
    return f"{100 * done // len(counted)}% ({done}/{len(counted)})"


def fmt_entity_meta(entity: dict, tasks: list[dict]) -> str:
    """One-line health / dates / progress summary for a project or stream header."""
    parts = []
    if entity.get("health"):
        parts.append(f"Health: {fmt_health(entity)}")
    start, target = entity.get("start_date"), entity.get("target_date")
    if start or target:
        parts.append(f"Dates: {start or '?'} → {fmt_target(entity) if target else '?'}")
    parts.append(f"Progress: {fmt_progress(tasks)}")
    return " | ".join(parts)


def print_project_status_table(heading: str, projects: list[dict], history: list[dict]):
    """Project Status table (non-completed projects) with health, target, and progress."""
    active = [p for p in projects if entity_status(p) != "completed"]
    if not active:
        return
    print(f"## {heading}")
    print()
    print_table_header(["Project", "Owner", "Status", "Health", "Target", "Progress", "Latest Update"])
    for p in active:
        print_row([p["_title"], fmt_entity_owners(p), entity_status(p), fmt_health(p), fmt_target(p),
                   fmt_progress(tasks_in(history, p["_slug"])), p.get("_latest_update") or "—"])
    print()


def print_stream_status_table(heading: str, streams: list[dict], history: list[dict]):
    """Stream Status table (non-completed streams) with health, target, and progress."""
    active = [s for s in streams if entity_status(s) != "completed"]
    if not active:
        return
    print(f"## {heading}")
    print()
    print_table_header(["Project", "Stream", "Owner", "Status", "Health", "Target", "Progress", "Latest Update"])
    for s in active:
        stream_tasks = tasks_in(history, s["_project_slug"], s["_slug"])
        print_row([project_display_name(s["_project_slug"]), s["_title"], fmt_entity_owners(s),
                   entity_status(s), fmt_health(s), fmt_target(s), fmt_progress(stream_tasks),
                   s.get("_latest_update") or "—"])
    print()


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
    cancelled = []
    scheduled_later = 0  # todo tasks whose start_date is still in the future

    for t in tasks:
        status = task_status(t)
        due = parse_date(t.get("due_date"))
        start = parse_date(t.get("start_date"))

        if status == "done":
            if closed_date(t) == today:
                completed.append(t)
            continue
        if status == "cancelled":
            if closed_date(t) == today:
                cancelled.append(t)
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
            if start and start > today:
                scheduled_later += 1
            else:
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
                rows = grouped[proj][stream]
                has_start = any(t.get("start_date") for t in rows)
                has_deps = any(t.get("blocked_by") for t in rows)
                headers = ["ID", "Task", "Owner", "Priority"]
                if has_start:
                    headers.append("Start")
                headers.append("Due")
                if has_deps:
                    headers.append("Blocked By")
                headers.append("Latest Update")
                print_table_header(headers)
                for t in rows:
                    cells = [t.get("id") or "???", t["_title"], fmt_owners(t), fmt_priority(t)]
                    if has_start:
                        cells.append(fmt_start(t))
                    cells.append(fmt_due(t))
                    if has_deps:
                        cells.append(", ".join(t.get("blocked_by") or []) or "—")
                    cells.append(fmt_latest_update(t))
                    print_row(cells)
                print()

    print_section("🔴 Overdue", overdue)
    print_section("📅 Due Today", due_today)
    print_section("🔄 In Progress", in_progress)
    print_section("🚫 Blocked", blocked)
    print_section("📋 Not Started", not_started)
    if scheduled_later:
        print(f"_{scheduled_later} todo task(s) with a future `start_date` are not shown — "
              f"see `this_week` or `timeline`._")
        print()
    print_section("✅ Completed", completed)
    if cancelled:
        print_section("✖️ Cancelled", cancelled)


# ---------------------------------------------------------------------------
# Dashboard: this_week
# ---------------------------------------------------------------------------

def cmd_this_week():
    today = date.today()
    monday, sunday = week_bounds(today)
    all_tasks = load_all_tasks()
    history = all_tasks + load_archived_tasks()  # for progress roll-ups

    def in_week(d: date | None) -> bool:
        return d is not None and monday <= d <= sunday

    # Open tasks, plus tasks done or cancelled this week
    tasks = [t for t in all_tasks if is_open(t) or in_week(closed_date(t))]
    projects = load_projects()

    def print_week_table(rows: list[dict]):
        has_start = any(t.get("start_date") for t in rows)
        headers = ["ID", "Task", "Owner", "Priority", "Status"]
        if has_start:
            headers.append("Start")
        headers += ["Due", "Latest Update"]
        print_table_header(headers)
        for t in rows:
            cells = [t.get("id") or "???", t["_title"], fmt_owners(t), fmt_priority(t), fmt_status(t)]
            if has_start:
                cells.append(fmt_start(t))
            cells += [fmt_due(t), fmt_latest_update(t)]
            print_row(cells)

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
        print(f"> {fmt_entity_meta(proj, tasks_in(history, slug))}")
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
            print(f"> {fmt_entity_meta(stream, tasks_in(history, slug, sslug))}")
            latest = stream.get("_latest_update")
            if latest:
                print(f"> Latest: {latest}")
            print()
            if stream_tasks:
                print_week_table(stream_tasks)
            else:
                print("No open tasks.")
            print()

        # Project-level tasks
        plevel = [t for t in proj_tasks if not t.get("stream")]
        plevel.sort(key=priority_sort_key)
        if plevel:
            print("### (Project-level tasks)")
            print()
            print_week_table(plevel)
            print()

        print("---")
        print()

    # Standalone tasks (not tied to any project)
    standalone = [t for t in tasks if not t.get("project")]
    if standalone:
        standalone.sort(key=priority_sort_key)
        print("## Standalone Tasks")
        print()
        print_week_table(standalone)
        print()
        print("---")
        print()


# ---------------------------------------------------------------------------
# Dashboard: my_team
# ---------------------------------------------------------------------------

def cmd_my_team():
    today = date.today()
    all_tasks = load_all_tasks()
    history = all_tasks + load_archived_tasks()  # for progress roll-ups
    # Open tasks, plus tasks completed today (cancelled tasks are left out)
    tasks = [t for t in all_tasks if is_open(t)
             or (task_status(t) == "done" and closed_date(t) == today)]
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
        open_count = sum(1 for t in owner_tasks if is_open(t))
        done_count = sum(1 for t in owner_tasks if task_status(t) == "done")
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
            print(f"| {tid} | {title} | {proj} | {stream} | {fmt_priority(t)} | {fmt_status(t)} | {fmt_due(t)} | {days} | {fmt_latest_update(t)} |")

        print()
        print("---")
        print()

    print_project_status_table("Project Status", load_projects(), history)
    print_stream_status_table("Stream Status", load_all_streams(), history)

    # Summary table
    print("## Summary")
    print()
    print("| Member | Open | In Progress | Blocked | Completed Today | Oldest Task (days) |")
    print("|--------|------|-------------|---------|-----------------|---------------------|")
    for owner in owners:
        owner_tasks = by_owner[owner]
        open_count = sum(1 for t in owner_tasks if is_open(t))
        done_count = sum(1 for t in owner_tasks if task_status(t) == "done")
        ip = sum(1 for t in owner_tasks if task_status(t) == "in-progress")
        bl = sum(1 for t in owner_tasks if task_status(t) == "blocked")
        ages = []
        for t in owner_tasks:
            if not is_open(t):
                continue
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
    history = tasks + load_archived_tasks()  # for progress roll-ups

    completed = []
    cancelled = []
    in_progress = []
    blocked = []
    new_this_week = []

    for t in tasks:
        status = task_status(t)
        closed = closed_date(t)
        created_date = parse_date(t.get("created"))

        if status == "done" and closed and monday <= closed <= sunday:
            completed.append(t)
        if status == "cancelled" and closed and monday <= closed <= sunday:
            cancelled.append(t)
        if status == "in-progress":
            in_progress.append(t)
        if status == "blocked":
            blocked.append(t)
        if created_date and monday <= created_date <= sunday and is_open(t):
            new_this_week.append(t)

    total_open = sum(1 for t in tasks if is_open(t))

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

    # Cancelled
    print("## ✖️ Cancelled This Week")
    print()
    if cancelled:
        cancelled.sort(key=lambda t: t.get("cancelled_date") or "")
        print_table_header(["ID", "Task", "Project", "Owner", "Cancelled", "Latest Update"])
        for t in cancelled:
            print_row([t.get("id") or "???", t["_title"], project_display_name(t.get("project") or ""),
                       fmt_owners(t), t.get("cancelled_date") or "?", fmt_latest_update(t)])
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

    print_project_status_table("📁 Project Status", load_projects(), history)
    print_stream_status_table("🌊 Stream Status", load_all_streams(), history)

    # Summary
    print("## 📊 Summary")
    print()
    print(f"- Tasks completed: {len(completed)}")
    print(f"- Tasks cancelled: {len(cancelled)}")
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
    history = tasks + load_archived_tasks()  # for progress roll-ups

    def owns(entity: dict) -> bool:
        names = [o.lower() for o in entity_owners(entity)]
        return owner.lower() in names

    def counts(items: list[dict]) -> tuple[int, int]:
        open_n = sum(1 for t in items if is_open(t))
        blocked_n = sum(1 for t in items if task_status(t) == "blocked")
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
        print_table_header(["Project", "Status", "Health", "Target", "Progress", "Open", "Blocked",
                            "Latest Update"])
        for p in owned_projects:
            # Roll up all tasks under the project (project-level + all streams)
            open_n, blocked_n = counts(tasks_in(tasks, p["_slug"]))
            print_row([p["_title"], entity_status(p), fmt_health(p), fmt_target(p),
                       fmt_progress(tasks_in(history, p["_slug"])), open_n, blocked_n,
                       p.get("_latest_update") or "—"])
    else:
        print("None")
    print()

    print("## 🌊 Streams Owned")
    print()
    if owned_streams:
        print_table_header(["Project", "Stream", "Status", "Health", "Target", "Progress", "Open",
                            "Blocked", "Latest Update"])
        for s in owned_streams:
            open_n, blocked_n = counts(tasks_in(tasks, s["_project_slug"], s["_slug"]))
            print_row([project_display_name(s["_project_slug"]), s["_title"], entity_status(s),
                       fmt_health(s), fmt_target(s),
                       fmt_progress(tasks_in(history, s["_project_slug"], s["_slug"])),
                       open_n, blocked_n, s.get("_latest_update") or "—"])
    else:
        print("None")
    print()


# ---------------------------------------------------------------------------
# Timeline (Mermaid Gantt chart) — one project, or the whole portfolio
# ---------------------------------------------------------------------------

TIMELINE_DONE_WINDOW_DAYS = 30  # completed tasks older than this are left off the chart
MAX_BAR_TITLE = 45
TIMELINE_LEGEND = ("_Legend: grey = done · highlighted = in progress · red = blocked, overdue, "
                   "past target, or off-track. Task bars run from `start_date` (or `created`) to "
                   "`due_date`; project and stream bars run to `target_date`._")


def mermaid_text(s: str) -> str:
    """Make text safe for a Mermaid gantt title, section, or bar name."""
    s = (s or "").replace(":", " -").replace(";", ",").replace("#", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s or "Untitled"


def gantt_bar(name: str, tags: list[str], start: date, end: date) -> str:
    """A Mermaid gantt bar covering start..end, both inclusive."""
    start = min(start, end)
    tag_str = "".join(f"{tag}, " for tag in tags)
    # Mermaid end dates are exclusive, so add a day to include the end date itself
    return f"    {mermaid_text(name)} :{tag_str}{start}, {end + timedelta(days=1)}"


def gantt_milestone(name: str, when: date) -> str:
    return f"    {mermaid_text(name)} :milestone, {when}, 0d"


def task_span(task: dict) -> tuple[date, date] | None:
    """(start, end) of a task's bar, or None when it has no date to place it on."""
    if task_status(task) == "done":
        end = closed_date(task) or parse_date(task.get("due_date"))
    else:
        end = parse_date(task.get("due_date"))
    if not end:
        return None
    start = parse_date(task.get("start_date")) or parse_date(task.get("created")) or end
    return min(start, end), end


def task_bar_tags(task: dict, today: date) -> list[str]:
    status = task_status(task)
    if status == "done":
        return ["done"]
    tags = []
    due = parse_date(task.get("due_date"))
    if status == "blocked" or (due and due < today):
        tags.append("crit")
    if status == "in-progress":
        tags.append("active")
    return tags


def entity_span(entity: dict) -> tuple[date, date] | None:
    """(start, end) of a project/stream bar, or None without a target_date."""
    end = parse_date(entity.get("target_date"))
    if not end:
        return None
    start = parse_date(entity.get("start_date")) or parse_date(entity.get("created")) or end
    return min(start, end), end


def entity_bar_tags(entity: dict) -> list[str]:
    if entity_status(entity) == "completed":
        return ["done"]
    if entity_is_late(entity) or str(entity.get("health") or "").lower() == "off-track":
        return ["crit"]
    return []


def task_bar_name(task: dict) -> str:
    title = task["_title"]
    if len(title) > MAX_BAR_TITLE:
        title = title[:MAX_BAR_TITLE - 1] + "…"
    return f"{task.get('id') or '???'} {title}"


def print_gantt(title: str, sections: list[tuple[str, list[str]]], dates: list[date]):
    """Print a ```mermaid gantt block. sections = [(section name, [bar lines]), ...]."""
    sections = [(name, bars) for name, bars in sections if bars]
    if not sections:
        print("_Nothing to chart yet — add `target_date` to projects/streams, or `due_date` to tasks._")
        print()
        return
    wide = bool(dates) and (max(dates) - min(dates)).days > 180
    print("```mermaid")
    print("gantt")
    print(f"    title {mermaid_text(title)}")
    print("    dateFormat YYYY-MM-DD")
    print(f"    axisFormat {'%b %Y' if wide else '%b %d'}")
    for name, bars in sections:
        print(f"    section {mermaid_text(name)}")
        for bar in bars:
            print(bar)
    print("```")
    print()
    print(TIMELINE_LEGEND)
    print()


def timeline_project(slug: str):
    today = date.today()
    project = next(p for p in load_projects() if p["_slug"] == slug)
    history = load_all_tasks() + load_archived_tasks()
    project_tasks = tasks_in(history, slug)
    charted = [t for t in project_tasks if task_status(t) != "cancelled"]
    cutoff = today - timedelta(days=TIMELINE_DONE_WINDOW_DAYS)

    sections: list[tuple[str, list[str]]] = []
    dates: list[date] = []
    unscheduled: list[dict] = []
    hidden_done = 0

    def task_bars(tasks: list[dict]) -> list[str]:
        nonlocal hidden_done
        bars = []
        placed = [(task_span(t), t) for t in tasks]
        for span, t in sorted(placed, key=lambda x: x[0] or (date.max, date.max)):
            if span is None:
                if is_open(t):
                    unscheduled.append(t)
                continue
            if task_status(t) == "done" and span[1] < cutoff:
                hidden_done += 1
                continue
            dates.extend(span)
            bars.append(gantt_bar(task_bar_name(t), task_bar_tags(t, today), *span))
        return bars

    print(f"# 🗓️ Timeline: {project['_title']} — {today}")
    print()
    print(f"> {fmt_entity_meta(project, project_tasks)}")
    print()

    # Project window + target milestone, then project-level tasks
    project_bars = []
    span = entity_span(project)
    if span:
        dates.extend(span)
        project_bars.append(gantt_bar(project["_title"], entity_bar_tags(project), *span))
        project_bars.append(gantt_milestone("Target", span[1]))
    sections.append((project["_title"], project_bars + task_bars([t for t in charted if not t.get("stream")])))

    # One section per stream: stream window, then its tasks
    no_target = []
    for stream in load_streams(slug):
        stream_bars = []
        sspan = entity_span(stream)
        if sspan:
            dates.extend(sspan)
            stream_bars.append(gantt_bar(f"{stream['_title']} (stream)", entity_bar_tags(stream), *sspan))
        elif entity_status(stream) != "completed":
            no_target.append(stream["_title"])
        stream_bars += task_bars([t for t in charted if t.get("stream") == stream["_slug"]])
        sections.append((stream["_title"], stream_bars))

    print_gantt(project["_title"], sections, dates)

    if not span:
        print("_The project has no `target_date`, so it has no bar or target milestone._")
        print()
    if no_target:
        print(f"_Streams without a `target_date`: {', '.join(no_target)}._")
        print()
    if unscheduled:
        print(f"**Not on the timeline** — {len(unscheduled)} open task(s) without a `due_date`:")
        print()
        for t in sorted(unscheduled, key=priority_sort_key):
            print(f"- {t.get('id') or '???'} — {t['_title']} ({fmt_status(t)}, {fmt_owners(t)})")
        print()
    if hidden_done:
        print(f"_{hidden_done} task(s) completed more than {TIMELINE_DONE_WINDOW_DAYS} days ago are not shown._")
        print()


def timeline_portfolio():
    today = date.today()
    projects = [p for p in load_projects() if entity_status(p) != "completed"]

    print(f"# 🗓️ Portfolio Timeline — {today}")
    print()

    sections: list[tuple[str, list[str]]] = []
    dates: list[date] = []
    unscheduled: list[str] = []
    for p in projects:
        bars = []
        span = entity_span(p)
        if span:
            dates.extend(span)
            bars.append(gantt_bar(p["_title"], entity_bar_tags(p), *span))
        else:
            unscheduled.append(p["_title"])
        for s in load_streams(p["_slug"]):
            sspan = entity_span(s)
            if sspan:
                dates.extend(sspan)
                bars.append(gantt_bar(s["_title"], entity_bar_tags(s), *sspan))
            elif entity_status(s) != "completed":
                unscheduled.append(f"{p['_title']} / {s['_title']}")
        sections.append((p["_title"], bars))

    print_gantt("Portfolio", sections, dates)

    if unscheduled:
        print(f"**Not on the timeline** — no `target_date`: {', '.join(unscheduled)}")
        print()


def cmd_timeline(project_slug: str | None):
    if project_slug:
        timeline_project(project_slug)
    else:
        timeline_portfolio()


# ---------------------------------------------------------------------------
# Data check — validates every file under data/ (read-only, never saved)
# ---------------------------------------------------------------------------

KNOWN_FIELDS = {
    "task": {"id", "type", "project", "stream", "owners", "owner", "completion_mode", "completions",
             "status", "priority", "start_date", "due_date", "created", "completed_date",
             "cancelled_date", "tags", "blocked_by", "links", "source_meeting"},
    "project": {"type", "status", "health", "owners", "owner", "summary", "start_date",
                "target_date", "created", "links"},
    "stream": {"type", "project", "status", "health", "owners", "owner", "summary", "start_date",
               "target_date", "created", "links"},
    "team-member": {"type", "full_name", "first_name", "role", "self"},
    "meeting": {"type", "date", "area", "project", "stream", "attendees", "tags", "links",
                "source_transcript"},
    "note": {"type", "date", "area", "project", "stream", "tags", "links"},
    "area": {"type", "slug", "summary", "created"},
    "index": {"type"},
}
TASK_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)?-\d{3,}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class CheckReport:
    def __init__(self):
        self.errors: set[tuple[str, str]] = set()
        self.warnings: set[tuple[str, str]] = set()

    def error(self, path, msg: str):
        self.errors.add((rel_path(path), msg))

    def warn(self, path, msg: str):
        self.warnings.add((rel_path(path), msg))


def rel_path(path) -> str:
    p = Path(path)
    try:
        rel = p.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        rel = p.as_posix()
    return rel + "/" if p.is_dir() else rel


def load_checked(path: Path, report: CheckReport, kind: str | None, required: bool = True):
    """Read a file's front matter, lint its syntax, and check its `type`.

    Returns (fm, raw) where raw maps each field to its unparsed value, or (None, None)
    when the front matter can't be read at all.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        report.error(path, "not valid UTF-8 — plainpm can't read this file")
        return None, None
    except OSError as e:
        report.error(path, f"can't read file ({e.strerror})")
        return None, None
    if text.startswith("﻿"):
        report.error(path, "file starts with a byte-order mark (BOM), so its front matter isn't read — "
                           "re-save it as UTF-8 without BOM")
        return None, None
    m = re.match(r"^---\s*\n(.*?\n)---", text, re.DOTALL)
    if not m:
        msg = "no YAML front matter (`---` block at the top)"
        if required:
            report.error(path, msg + " — dashboards ignore this file")
        else:
            report.warn(path, msg)
        return None, None

    raw: dict[str, str] = {}
    multiline_reported: set[str] = set()
    last_key = None
    for line in m.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[0] in " \t" or stripped.startswith("- "):
            key = last_key or "(unknown)"
            if key not in multiline_reported:
                multiline_reported.add(key)
                report.error(path, f"`{key}` uses multi-line YAML, which plainpm can't read — "
                                   f"write it inline, e.g. `{key}: [a, b]`")
            continue
        if ":" not in stripped:
            report.error(path, f"can't parse front matter line `{stripped}`")
            continue
        key, _, val = stripped.partition(":")
        key = key.strip()
        if key in raw:
            report.error(path, f"duplicate field `{key}` — only the last value is used")
        raw[key] = val.strip()
        last_key = key

    fm = parse_front_matter(path)
    ftype = fm.get("type")
    if kind and ftype != kind:
        if ftype:
            report.error(path, f"`type: {ftype}` but files here must be `type: {kind}` — dashboards ignore it")
        else:
            report.error(path, f"missing `type: {kind}` — dashboards ignore this file")
    known = KNOWN_FIELDS.get(kind or ftype or "")
    if known:
        for key in raw:
            if key not in known:
                report.warn(path, f"unknown field `{key}` (typo?)")
    return fm, raw


def check_date(path: Path, fm: dict, key: str, report: CheckReport) -> date | None:
    v = fm.get(key)
    if v in (None, ""):
        return None
    if not isinstance(v, str) or not DATE_RE.match(v) or parse_date(v) is None:
        report.error(path, f"`{key}` is not a valid YYYY-MM-DD date: `{v}`")
        return None
    return parse_date(v)


def check_list(path: Path, fm: dict, key: str, report: CheckReport) -> list[str]:
    v = fm.get(key)
    if v is None:
        return []
    if not isinstance(v, list):
        report.error(path, f"`{key}` should be an inline list like `[a, b]`, got `{v}`")
        return []
    return [x for x in v if x]


def check_links(path: Path, raw: dict, report: CheckReport):
    v = raw.get("links")
    if v in (None, "", "[]"):
        return
    example = '`links: [{label: "Design doc", url: "https://…"}]`'
    if not (v.startswith("[") and v.endswith("]")):
        report.warn(path, f"`links` should be an inline list like {example}")
        return
    inner = v[1:-1].strip()
    items = re.findall(r"\{[^{}]*\}", inner)
    leftover = re.sub(r"\{[^{}]*\}", "", inner).replace(",", "").strip()
    if leftover or not items:
        report.warn(path, f"`links` should be an inline list like {example}")
        return
    for item in items:
        if not re.search(r"\blabel\s*:", item) or not re.search(r"\burl\s*:", item):
            report.warn(path, f"link `{item}` needs both a `label` and a `url`")


def resolve_data_path(value: str) -> bool:
    """True if a path stored in front matter (e.g. source_meeting) points to an existing file."""
    v = value.strip().lstrip("./")
    return any((base / v).exists() for base in (PROJECT_ROOT, DATA_DIR))


def check_owners(path: Path, fm: dict, raw: dict, roster: set[str], report: CheckReport) -> list[str]:
    """Validate `owners` (and the legacy `owner` field). Returns the owner names."""
    owners = check_list(path, fm, "owners", report)
    if "owner" in raw:
        legacy = fm.get("owner")
        if "owners" in raw:
            report.warn(path, "has both legacy `owner` and `owners` — remove `owner`")
        else:
            report.warn(path, f"uses the legacy `owner` field — change it to `owners: [{legacy or ''}]`")
        if not owners and isinstance(legacy, str) and legacy:
            owners = [legacy]
    by_lower = {name.lower(): name for name in roster}
    for name in owners:
        if name in roster:
            continue
        hint = f" (did you mean `{by_lower[name.lower()]}`?)" if name.lower() in by_lower else ""
        report.error(path, f"owner `{name}` doesn't match any team member's `first_name` in data/team/{hint}")
    return owners


def check_team(files: list[Path], report: CheckReport) -> dict[str, dict]:
    team: dict[str, dict] = {}
    self_files = []
    for path in files:
        fm, raw = load_checked(path, report, "team-member")
        if fm is None:
            continue
        first = fm.get("first_name")
        if not first:
            report.error(path, "missing `first_name` — owners are matched by first name")
            continue
        if first in team:
            report.error(path, f"duplicate `first_name: {first}` (also in {rel_path(team[first]['_file'])}) "
                               "— owner matching is ambiguous")
            continue
        fm["_file"] = path
        team[first] = fm
        self_val = str(fm.get("self") or "false").lower()
        if self_val not in ("true", "false"):
            report.warn(path, f"`self` should be `true` or `false`, got `{fm.get('self')}`")
        if self_val == "true":
            self_files.append(path)
    if len(self_files) > 1:
        for path in self_files:
            report.error(path, "more than one team member has `self: true` — \"me\" is ambiguous")
    if not team:
        report.warn(DATA_DIR / "team", "no team members found — add yourself (see templates/team-member.md)")
    elif len(team) > 1 and not self_files:
        report.warn(DATA_DIR / "team", "no team member has `self: true`, so \"me\"/\"my\" can't be resolved")
    return team


def check_entity(path: Path, fm: dict, raw: dict, roster: set[str], report: CheckReport):
    """Checks shared by project.md and stream.md."""
    status = fm.get("status")
    if not status:
        report.warn(path, "missing `status` — dashboards treat it as `active`")
    elif str(status).lower() not in ENTITY_STATUSES:
        report.error(path, f"`status: {status}` is not one of: {', '.join(ENTITY_STATUSES)}")
    health = fm.get("health")
    if health and str(health).lower() not in HEALTH_VALUES:
        report.error(path, f"`health: {health}` is not one of: {', '.join(HEALTH_VALUES)}")
    check_date(path, fm, "created", report)
    start = check_date(path, fm, "start_date", report)
    target = check_date(path, fm, "target_date", report)
    if start and target and start > target:
        report.error(path, f"`start_date` {start} is after `target_date` {target}")
    check_owners(path, fm, raw, roster, report)
    check_links(path, raw, report)
    if entity_is_late(fm):
        msg = f"past its `target_date` ({target}) but not completed"
        if str(health or "").lower() == "on-track":
            msg += ", and `health` still says on-track"
        report.warn(path, msg + " — update the target date, health, or status")


def check_task(path: Path, fm: dict, raw: dict, loc: dict, roster: set[str], report: CheckReport,
               today: date):
    tid = fm.get("id")
    if not tid:
        report.error(path, "missing `id`")
    elif not TASK_ID_RE.match(str(tid)):
        report.error(path, f"`id: {tid}` doesn't follow the ID format (ALPHA-001, ALPHA-BE-001, TASK-001)")
    elif tid != path.stem:
        report.warn(path, f"file name doesn't match `id: {tid}` (expected {tid}.md)")

    if not loc["archived"]:
        # Front matter must agree with the folder the file lives in — dashboards trust the front matter
        exp_p, exp_s = loc["project"], loc["stream"]
        got_p, got_s = fm.get("project") or None, fm.get("stream") or None
        if "project" not in raw:
            if exp_p:
                report.warn(path, f"missing `project: {exp_p}` (dashboards infer it from the folder)")
        elif got_p != exp_p:
            where = f"project folder `{exp_p}`" if exp_p else "the standalone data/tasks/ folder"
            report.error(path, f"`project: {got_p or '(empty)'}` doesn't match its location ({where}) "
                               "— dashboards will group it under the wrong project")
        if "stream" not in raw:
            if exp_s:
                report.warn(path, f"missing `stream: {exp_s}` (dashboards infer it from the folder)")
        elif got_s != exp_s:
            where = f"stream folder `{exp_s}`" if exp_s else "a folder outside any stream"
            report.error(path, f"`stream: {got_s or '(empty)'}` doesn't match its location ({where}) "
                               "— dashboards will group it under the wrong stream")
        if tid and TASK_ID_RE.match(str(tid)):
            parts = str(tid).split("-")
            if exp_p is None and parts[0] != "TASK":
                report.error(path, f"standalone task IDs use `TASK-NNN`, got `{tid}`")
            elif exp_p and parts[0] == "TASK":
                report.error(path, f"`{tid}` uses the standalone `TASK-` prefix inside a project")
            elif exp_p and not exp_s and len(parts) != 2:
                report.error(path, f"project-level task IDs look like `PROJECT-NNN`, got `{tid}`")
            elif exp_s and len(parts) != 3:
                report.error(path, f"stream task IDs look like `PROJECT-STREAM-NNN`, got `{tid}`")

    status = task_status(fm)
    if not status:
        report.error(path, "missing `status` — the task won't appear in most dashboard sections")
    elif status not in TASK_STATUSES:
        report.error(path, f"`status: {fm.get('status')}` is not one of: {', '.join(TASK_STATUSES)}")
    priority = str(fm.get("priority") or "").lower()
    if not priority:
        report.warn(path, "missing `priority` — dashboards treat it as medium")
    elif priority not in PRIORITIES:
        report.error(path, f"`priority: {fm.get('priority')}` is not one of: {', '.join(PRIORITIES)}")
    mode = str(fm.get("completion_mode") or "any").lower()
    if mode not in COMPLETION_MODES:
        report.error(path, f"`completion_mode: {fm.get('completion_mode')}` is not one of: any, all")

    created = check_date(path, fm, "created", report)
    if not fm.get("created"):
        report.warn(path, "missing `created` date — days open can't be calculated")
    start = check_date(path, fm, "start_date", report)
    due = check_date(path, fm, "due_date", report)
    completed = check_date(path, fm, "completed_date", report)
    cancelled = check_date(path, fm, "cancelled_date", report)
    if start and due and start > due:
        report.error(path, f"`start_date` {start} is after `due_date` {due}")
    if completed and created and completed < created:
        report.warn(path, f"`completed_date` {completed} is before `created` {created}")
    for key, d in (("completed_date", completed), ("cancelled_date", cancelled)):
        if d and d > today:
            report.warn(path, f"`{key}` {d} is in the future")

    if status == "done" and not fm.get("completed_date"):
        report.error(path, "`status: done` but no `completed_date` — reports will miss when it was finished")
    if fm.get("completed_date") and status and status != "done":
        report.warn(path, f"has a `completed_date` but `status` is `{status}` — only done tasks keep a completed_date")
    if status == "cancelled" and not fm.get("cancelled_date"):
        report.error(path, "`status: cancelled` but no `cancelled_date`")
    if fm.get("cancelled_date") and status and status != "cancelled":
        report.warn(path, f"has a `cancelled_date` but `status` is `{status}` — only cancelled tasks keep a cancelled_date")

    owners = check_owners(path, fm, raw, roster, report)
    if mode == "all" and len(owners) > 1:
        comps = fm.get("completions")
        if not isinstance(comps, dict):
            report.error(path, "`completion_mode: all` needs a `completions` map, e.g. "
                               f"`completions: {{{', '.join(f'{o}: null' for o in owners)}}}`")
        else:
            missing = [o for o in owners if o not in comps]
            extra = [k for k in comps if k not in owners]
            if missing:
                report.error(path, f"`completions` is missing {', '.join(missing)}")
            if extra:
                report.error(path, f"`completions` has names that aren't in `owners`: {', '.join(extra)}")
            for name, v in comps.items():
                if v and (not DATE_RE.match(v) or parse_date(v) is None):
                    report.error(path, f"`completions` date for {name} is not YYYY-MM-DD: `{v}`")
            values = [comps.get(o) for o in owners]
            if all(values) and status not in CLOSED_STATUSES:
                report.warn(path, f"every owner has completed their part but `status` is `{status}` — mark it done?")
            if status == "done" and not all(values):
                report.error(path, "`status: done` but not every owner's part is recorded in `completions`")

    blocked_by = check_list(path, fm, "blocked_by", report)
    if tid and tid in blocked_by:
        report.error(path, "`blocked_by` lists the task itself")
    check_list(path, fm, "tags", report)
    check_links(path, raw, report)
    source = fm.get("source_meeting")
    if isinstance(source, str) and source and not resolve_data_path(source):
        report.warn(path, f"`source_meeting` points to a file that doesn't exist: `{source}`")
    if loc["archived"] and status not in CLOSED_STATUSES:
        report.warn(path, f"archived task has `status: {status or '(missing)'}` — only done or cancelled tasks belong in the archive")


def check_task_graph(tasks: list[dict], projects: dict, streams: dict, report: CheckReport):
    """Cross-file checks: duplicate IDs, dependencies, ID prefixes, and schedule containment."""
    by_id: dict[str, list[dict]] = defaultdict(list)
    for t in tasks:
        if isinstance(t.get("id"), str) and t["id"]:
            by_id[t["id"]].append(t)
    for tid, group in by_id.items():
        if len(group) > 1:
            for t in group:
                others = [rel_path(o["_file"]) for o in group if o is not t]
                report.error(t["_file"], f"duplicate task ID `{tid}` — also used by {', '.join(others)}")
    # For duplicated IDs, prefer the active (non-archived) copy
    index = {tid: next((t for t in group if not t.get("_archived")), group[0]) for tid, group in by_id.items()}

    # Dependencies
    for t in tasks:
        deps = t.get("blocked_by") if isinstance(t.get("blocked_by"), list) else []
        deps = [d for d in deps if d and d != t.get("id")]
        missing = [d for d in deps if d not in index]
        if missing:
            report.error(t["_file"], f"`blocked_by` references unknown task(s): {', '.join(missing)}")
        if t.get("_archived") or not is_open(t):
            continue
        known = [d for d in deps if d in index]
        cancelled_deps = [d for d in known if task_status(index[d]) == "cancelled"]
        if cancelled_deps:
            report.warn(t["_file"], f"depends on cancelled task(s) {', '.join(cancelled_deps)} "
                                    "— remove the dependency or rethink this task")
        if task_status(t) == "blocked" and known and not missing and not any(is_open(index[d]) for d in known):
            report.warn(t["_file"], "every `blocked_by` task is closed but `status` is still `blocked` — unblock it?")

    # Dependency cycles
    graph = {tid: [d for d in (t.get("blocked_by") if isinstance(t.get("blocked_by"), list) else [])
                   if d in index and d != tid]
             for tid, t in index.items()}
    state: dict[str, int] = {}  # 1 = visiting, 2 = done
    seen_cycles: set[frozenset] = set()

    def visit(node: str, stack: list[str]):
        state[node] = 1
        stack.append(node)
        for nxt in graph[node]:
            if state.get(nxt) == 1:
                cycle = stack[stack.index(nxt):] + [nxt]
                key = frozenset(cycle)
                if key not in seen_cycles:
                    seen_cycles.add(key)
                    report.error(index[nxt]["_file"], f"dependency cycle: {' → '.join(cycle)}")
            elif nxt not in state:
                visit(nxt, stack)
        stack.pop()
        state[node] = 2

    for node in graph:
        if node not in state:
            visit(node, [])

    # ID prefixes: one per project, one per stream, no prefix shared between projects
    prefix_projects: dict[str, set[str]] = defaultdict(set)
    for slug, project in projects.items():
        ids = [str(t["id"]) for t in tasks if t.get("project") == slug and TASK_ID_RE.match(str(t.get("id") or ""))]
        prefixes = sorted({i.split("-")[0] for i in ids})
        for p in prefixes:
            prefix_projects[p].add(slug)
        if len(prefixes) > 1:
            report.warn(project["_file"], f"tasks use mixed ID prefixes ({', '.join(prefixes)}) — keep one per project")
    for prefix, slugs in prefix_projects.items():
        if len(slugs) > 1:
            for slug in slugs:
                report.warn(projects[slug]["_file"], f"ID prefix `{prefix}` is also used by "
                                                     f"{', '.join(s for s in sorted(slugs) if s != slug)}")
    for (pslug, sslug), stream in streams.items():
        ids = [str(t["id"]) for t in tasks if t.get("project") == pslug and t.get("stream") == sslug
               and TASK_ID_RE.match(str(t.get("id") or "")) and len(str(t["id"]).split("-")) == 3]
        abbrevs = sorted({i.split("-")[1] for i in ids})
        if len(abbrevs) > 1:
            report.warn(stream["_file"], f"tasks use mixed stream abbreviations ({', '.join(abbrevs)})")

    # Open tasks vs. their project/stream
    for t in tasks:
        if t.get("_archived") or not is_open(t) or not t.get("project"):
            continue
        project = projects.get(t.get("project"))
        stream = streams.get((t.get("project"), t.get("stream"))) if t.get("stream") else None
        if project and entity_status(project) == "completed":
            report.warn(t["_file"], "open task in a completed project")
        if stream and entity_status(stream) == "completed":
            report.warn(t["_file"], "open task in a completed stream")
        due = parse_date(t.get("due_date"))
        for kind, entity in (("stream", stream), ("project", project)):
            target = parse_date(entity.get("target_date")) if entity else None
            if target:
                if due and due > target:
                    report.warn(t["_file"], f"`due_date` {due} is after the {kind}'s `target_date` {target}")
                break


def check_note(path: Path, loc: dict, projects: dict, streams: dict, areas: set[str], report: CheckReport):
    fm, raw = load_checked(path, report, None, required=False)
    if fm is None:
        return
    ntype = fm.get("type")
    if ntype == "task":
        report.error(path, "task file inside a notes folder — dashboards won't see it; move it to a tasks/YYYY/ folder")
        return
    if ntype not in ("meeting", "note"):
        report.warn(path, f"`type` should be `meeting` or `note`, got `{ntype or '(missing)'}`")
        return
    if not fm.get("date"):
        report.warn(path, "missing `date`")
    check_date(path, fm, "date", report)
    area, project, stream = fm.get("area"), fm.get("project"), fm.get("stream")
    if area and area not in areas:
        report.warn(path, f"`area: {area}` doesn't match any folder in data/meetings/areas/")
    if project and project not in projects:
        report.warn(path, f"`project: {project}` doesn't match any project")
    if stream and project and (project, stream) not in streams:
        report.warn(path, f"`stream: {stream}` doesn't match any stream in `{project}`")
    if loc.get("project") and project != loc["project"]:
        report.warn(path, f"`project: {project or '(empty)'}` doesn't match its folder (`{loc['project']}`)")
    if loc.get("area") and area != loc["area"]:
        report.warn(path, f"`area: {area or '(empty)'}` doesn't match its folder (`{loc['area']}`)")
    check_list(path, fm, "attendees", report)
    check_list(path, fm, "tags", report)
    check_links(path, raw, report)
    source = fm.get("source_transcript")
    if isinstance(source, str) and source and not resolve_data_path(source):
        report.warn(path, f"`source_transcript` points to a file that doesn't exist: `{source}`")


def check_index(projects: dict, project_dirs: list[Path], report: CheckReport):
    index_path = DATA_DIR / "projects" / "_index.md"
    if not index_path.exists():
        if project_dirs:
            report.warn(index_path, "missing — /status and /new-task use it to find projects")
        return
    text = index_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    for slug, project in projects.items():
        row = next((line for line in lines if f"projects/{slug}/" in line), None)
        if row is None:
            report.warn(index_path, f"project `{slug}` is not listed")
            continue
        cells = [c.strip().strip("`").lower() for c in row.strip().strip("|").split("|")]
        listed = next((c for c in cells if c in ENTITY_STATUSES), None)
        if listed and listed != entity_status(project):
            report.warn(index_path, f"lists `{slug}` as `{listed}` but its project.md says `{entity_status(project)}`")
    existing = {d.name for d in project_dirs}
    for slug in sorted(set(re.findall(r"projects/([A-Za-z0-9][A-Za-z0-9_-]*)/", text))):
        if slug not in existing:
            report.warn(index_path, f"lists `{slug}`, but there's no data/projects/{slug}/ folder")


def classify_data_file(path: Path) -> tuple[str, dict]:
    """Decide what a markdown file under data/ should be, based on where it lives."""
    parts = path.relative_to(DATA_DIR).parts
    n = len(parts)
    top = parts[0]
    if top == "team" and n == 2:
        return "team", {}
    if top == "tasks":
        return "task", {"project": None, "stream": None, "archived": False}
    if top == "archive":
        return "task", {"project": None, "stream": None, "archived": True}
    if top == "projects":
        if n == 2 and parts[1] == "_index.md":
            return "index", {}
        if n >= 3:
            p = parts[1]
            if n == 3 and parts[2] == "project.md":
                return "project", {"project": p}
            if parts[2] == "tasks":
                return "task", {"project": p, "stream": None, "archived": False}
            if parts[2] == "meetings":
                return "note", {"project": p}
            if parts[2] == "streams" and n >= 5:
                s = parts[3]
                if n == 5 and parts[4] == "stream.md":
                    return "stream", {"project": p, "stream": s}
                if parts[4] == "tasks":
                    return "task", {"project": p, "stream": s, "archived": False}
                if parts[4] == "notes":
                    return "note", {"project": p}
    if top == "meetings" and n >= 3:
        if parts[1] == "notes":
            return "note", {}
        if parts[1] == "areas" and n >= 4:
            if n == 4 and parts[3] == "area.md":
                return "area", {"area": parts[2]}
            if parts[3] == "notes":
                return "note", {"area": parts[2]}
    return "other", {}


def subdirs(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return [d for d in sorted(path.iterdir()) if d.is_dir() and not d.name.startswith(".")]


def print_check_report(report: CheckReport, counts: list[tuple[str, int]]):
    print(f"# 🩺 Data Check — {date.today()}")
    print()
    print("Scanned " + ", ".join(f"{n} {label if n != 1 else label.removesuffix('s')}"
                                 for label, n in counts) + ".")
    print()
    for title, items in (("❌ Errors", report.errors), ("⚠️ Warnings", report.warnings)):
        if not items:
            continue
        print(f"## {title} ({len(items)})")
        print()
        print("| File | Problem |")
        print("|------|---------|")
        for file, msg in sorted(items):
            safe = msg.replace("|", "\\|")
            print(f"| `{file}` | {safe} |")
        print()
    if not report.errors and not report.warnings:
        print("✅ All clear — no issues found.")
    else:
        print(f"**Result**: {len(report.errors)} error(s), {len(report.warnings)} warning(s). "
              "Errors break dashboards or commands; warnings are inconsistencies worth a look.")
    print()


def cmd_check() -> int:
    """Validate every file under data/. Prints a report; returns 1 if there are errors."""
    report = CheckReport()
    today = date.today()

    buckets: dict[str, list[tuple[Path, dict]]] = defaultdict(list)
    for path in sorted(DATA_DIR.rglob("*.md")):
        parts = path.relative_to(DATA_DIR).parts
        if any(part.startswith(".") for part in parts):
            continue
        if parts[0] == "reports" or parts[:2] == ("meetings", "transcripts"):
            continue
        kind, loc = classify_data_file(path)
        buckets[kind].append((path, loc))

    def guarded(path: Path, fn, *args):
        try:
            fn(*args)
        except Exception as e:  # never let one odd file stop the whole check
            report.error(path, f"couldn't be fully checked ({type(e).__name__}: {e})")

    team = check_team([p for p, _ in buckets["team"]], report)
    roster = set(team)

    # Folder structure: every project/stream/area folder needs its definition file
    project_dirs = subdirs(DATA_DIR / "projects")
    for pdir in project_dirs:
        if not (pdir / "project.md").exists():
            report.error(pdir, "project folder has no project.md — its tasks won't appear in this_week or status")
        for sdir in subdirs(pdir / "streams"):
            if not (sdir / "stream.md").exists():
                report.error(sdir, "stream folder has no stream.md — its tasks won't appear in this_week")
    area_dirs = subdirs(DATA_DIR / "meetings" / "areas")
    for adir in area_dirs:
        if not (adir / "area.md").exists():
            report.warn(adir, "area folder has no area.md")

    projects: dict[str, dict] = {}
    for path, loc in buckets["project"]:
        fm, raw = load_checked(path, report, "project")
        if fm is None:
            continue
        fm["_file"] = path
        projects[loc["project"]] = fm
        guarded(path, check_entity, path, fm, raw, roster, report)

    streams: dict[tuple[str, str], dict] = {}
    for path, loc in buckets["stream"]:
        fm, raw = load_checked(path, report, "stream")
        if fm is None:
            continue
        fm["_file"] = path
        streams[(loc["project"], loc["stream"])] = fm
        guarded(path, check_entity, path, fm, raw, roster, report)
        if not fm.get("project"):
            report.warn(path, f"missing `project: {loc['project']}`")
        elif fm.get("project") != loc["project"]:
            report.error(path, f"`project: {fm.get('project')}` doesn't match its folder (`{loc['project']}`)")
        parent = projects.get(loc["project"])
        stream_target = parse_date(fm.get("target_date"))
        project_target = parse_date(parent.get("target_date")) if parent else None
        if stream_target and project_target and stream_target > project_target:
            report.warn(path, f"`target_date` {stream_target} is after the project's `target_date` {project_target}")

    tasks: list[dict] = []
    for path, loc in buckets["task"]:
        fm, raw = load_checked(path, report, "task")
        if fm is None:
            continue
        fm["_file"] = path
        fm["_archived"] = loc["archived"]
        tasks.append(fm)
        guarded(path, check_task, path, fm, raw, loc, roster, report, today)
    try:
        check_task_graph(tasks, projects, streams, report)
    except Exception as e:
        report.error(DATA_DIR, f"cross-task checks failed ({type(e).__name__}: {e})")

    area_names = {d.name for d in area_dirs}
    for path, loc in buckets["area"]:
        fm, raw = load_checked(path, report, "area")
        if fm and fm.get("slug") and fm["slug"] != loc["area"]:
            report.warn(path, f"`slug: {fm['slug']}` doesn't match its folder name `{loc['area']}`")
    for path, loc in buckets["note"]:
        guarded(path, check_note, path, loc, projects, streams, area_names, report)
    for path, _ in buckets["other"]:
        if parse_front_matter(path).get("type") == "task":
            report.error(path, "task file outside a tasks/ folder — dashboards won't see it")
    check_index(projects, project_dirs, report)

    archived = sum(1 for t in tasks if t["_archived"])
    print_check_report(report, [
        ("projects", len(projects)), ("streams", len(streams)), ("tasks", len(tasks) - archived),
        ("archived tasks", archived), ("team members", len(team)), ("notes", len(buckets["note"])),
    ])
    return 1 if report.errors else 0


# ---------------------------------------------------------------------------
# Main — capture output, save to reports/, print to stdout
# ---------------------------------------------------------------------------

COMMANDS = {
    "today": cmd_today,
    "this_week": cmd_this_week,
    "my_team": cmd_my_team,
    "weekly_report": cmd_weekly_report,
}


def run_and_save(command_name: str, arg: str | None = None):
    """Run a dashboard command, capture its output, save to reports/, print to stdout.

    `arg` is the owner name for `owner`, or the optional project slug for `timeline`.
    """
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
        owner_slug = re.sub(r"[^a-z0-9]+", "-", (arg or "").lower()).strip("-") or "owner"
        report_path = report_dir / f"{file_date}-{owner_slug}-owner.md"
    elif command_name == "timeline":
        report_path = report_dir / f"{file_date}-{arg or 'portfolio'}-timeline.md"
    else:
        report_path = report_dir / f"{file_date}-{subdir}.md"

    # Capture stdout into a buffer
    real_stdout = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf

    if command_name == "owner":
        cmd_owner(arg)
    elif command_name == "timeline":
        cmd_timeline(arg)
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
    valid = list(COMMANDS) + ["owner", "timeline", "check"]
    if len(sys.argv) < 2 or sys.argv[1] not in valid:
        print(f"Usage: python {sys.argv[0]} "
              f"<{'|'.join(COMMANDS)}|owner <first_name>|timeline [project-slug]|check>")
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

    if sys.argv[1] == "check":
        # Read-only validation: printed, never saved to reports/
        sys.exit(cmd_check())
    elif sys.argv[1] == "owner":
        if len(sys.argv) < 3 or not " ".join(sys.argv[2:]).strip():
            print("Usage: python scripts/dashboard.py owner <first_name>", file=sys.stderr)
            sys.exit(1)
        run_and_save("owner", " ".join(sys.argv[2:]).strip())
    elif sys.argv[1] == "timeline":
        slug = " ".join(sys.argv[2:]).strip() or None
        if slug and not (DATA_DIR / "projects" / slug / "project.md").exists():
            available = ", ".join(p["_slug"] for p in load_projects()) or "(none)"
            print(f"Error: no project with slug '{slug}'. Available: {available}", file=sys.stderr)
            sys.exit(1)
        run_and_save("timeline", slug)
    else:
        run_and_save(sys.argv[1])


if __name__ == "__main__":
    main()
