#!/usr/bin/env python3
"""
HPM EXEC 2026 Deadline Board — Data Generator
Pulls Canvas API + manual-todos.md → docs/data.json
No external dependencies; pure Python 3 stdlib.
"""

import json
import os
import re
import ssl
import urllib.request
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent
ENV_FILE = PROJECT_DIR / ".env"
DOCS_DIR = PROJECT_DIR / "docs"
DATA_FILE = DOCS_DIR / "data.json"
MANUAL_TODOS_FILE    = PROJECT_DIR / "data" / "manual-todos.md"
SESSION_READINGS_FILE = PROJECT_DIR / "data" / "session-readings.md"
SCHEDULE_FILE        = PROJECT_DIR / "data" / "schedule.json"

TRACKED_COURSES = {
    249500: {
        "short": "Pharma",
        "name": "The Pharmaceutical Industry (P8237)",
        "color": "#4f46e5",
        "bg": "#ede9fe",
    },
    246952: {
        "short": "Health Innovation",
        "name": "Health Innovation & Technology (P8536)",
        "color": "#059669",
        "bg": "#dcfce7",
    },
    47471: {
        "short": "EXEC/Grad",
        "name": "EXEC Program — Graduation Requirements",
        "color": "#d97706",
        "bg": "#fef3c7",
    },
    247383: {
        "short": "Simulation",
        "name": "Health System Simulation (P8556)",
        "color": "#6b7280",
        "bg": "#f3f4f6",
    },
}

# Known weight map: checked against lowercase title substrings
WEIGHT_MAP = [
    (249500, "strategic company",  "20%"),
    (249500, "policy memo",        "25%"),
    (249500, "synthesis paper",    "40%"),
    (246952, "reflection",         "~1 pt"),
    (246952, "group project",      "50%"),
    (246952, "final presentation", "30%"),
    (246952, "participation",      "20%"),
]

def get_weight(course_id, title):
    t = title.lower()
    for cid, keyword, weight in WEIGHT_MAP:
        if cid == course_id and keyword in t:
            return weight
    return None


# ──────────────────────────────────────────────────────────────
# .env loader
# ──────────────────────────────────────────────────────────────

def load_env():
    env = dict(os.environ)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip("\"'")
    return env


# ──────────────────────────────────────────────────────────────
# Canvas REST client (stdlib urllib, handles pagination)
# ──────────────────────────────────────────────────────────────

def _ssl_ctx():
    ctx = ssl.create_default_context()
    return ctx

def canvas_get(base_url, token, path, params=None):
    """Fetch one or all pages from a Canvas API endpoint.
    Returns a list (for collection endpoints) or dict (for single-resource endpoints).
    """
    url = base_url.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)

    ctx = _ssl_ctx()
    collected = []

    while url:
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                if isinstance(data, list):
                    collected.extend(data)
                else:
                    return data  # single object — return immediately

                # Follow pagination via Link header
                link_header = resp.headers.get("Link", "")
                url = None
                for part in link_header.split(","):
                    if 'rel="next"' in part:
                        m = re.search(r"<([^>]+)>", part)
                        if m:
                            url = m.group(1)
        except urllib.error.HTTPError as e:
            print(f"    HTTP {e.code} {e.reason} — {url}")
            break
        except Exception as exc:
            print(f"    ERROR fetching {url}: {exc}")
            break

    return collected


# ──────────────────────────────────────────────────────────────
# HTML sanitizer (strips script/style; keeps safe formatting tags)
# ──────────────────────────────────────────────────────────────

_ALLOWED_TAGS = {
    "p", "br", "b", "strong", "i", "em", "u", "s",
    "ul", "ol", "li",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "a", "blockquote", "pre", "code", "hr",
    "table", "thead", "tbody", "tr", "th", "td",
    "div", "span", "sup", "sub",
}
_SKIP_TAGS = {
    "script", "style", "iframe", "object", "embed",
    "form", "input", "button", "select", "textarea",
    "meta", "link", "head",
}


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__()
        self._buf = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in _ALLOWED_TAGS:
            extra = ""
            for name, val in (attrs or []):
                name = name.lower()
                if name == "href" and tag == "a" and val:
                    val = val.strip()
                    if val.startswith(("http://", "https://", "mailto:", "/")):
                        safe = val.replace('"', "%22")
                        extra = f' href="{safe}" target="_blank" rel="noopener noreferrer"'
            self._buf.append(f"<{tag}{extra}>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag in _ALLOWED_TAGS:
            self._buf.append(f"</{tag}>")

    def handle_data(self, data):
        if not self._skip_depth:
            self._buf.append(data)

    def output(self):
        return "".join(self._buf).strip()


def sanitize_html(raw):
    if not raw:
        return ""
    p = _Sanitizer()
    try:
        p.feed(str(raw))
    except Exception:
        pass
    return p.output()


# ──────────────────────────────────────────────────────────────
# Urgency computation
# ──────────────────────────────────────────────────────────────

def compute_urgency(due_at_str):
    """Returns one of: overdue | due_soon | this_week | next_two_weeks | later | undated"""
    if not due_at_str:
        return "undated"
    try:
        due = datetime.fromisoformat(due_at_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        hours = (due - now).total_seconds() / 3600
        if hours < 0:
            return "overdue"
        if hours < 48:
            return "due_soon"
        if hours < 7 * 24:
            return "this_week"
        if hours < 14 * 24:
            return "next_two_weeks"
        return "later"
    except Exception:
        return "undated"


# ──────────────────────────────────────────────────────────────
# Parse data/manual-todos.md
# ──────────────────────────────────────────────────────────────

def parse_manual_todos():
    if not MANUAL_TODOS_FILE.exists():
        print("  (manual-todos.md not found — skipping)")
        return []

    items = []
    lines = MANUAL_TODOS_FILE.read_text(encoding="utf-8").splitlines()
    in_table = False
    past_separator = False

    for line in lines:
        s = line.strip()

        if not s.startswith("|"):
            in_table = False
            past_separator = False
            continue

        if not in_table:
            # First pipe line = header row
            in_table = True
            past_separator = False
            continue

        if re.match(r"^\|[\s\-|]+\|$", s):
            past_separator = True
            continue

        if not past_separator:
            continue

        cells = [c.strip() for c in s.strip("|").split("|")]
        while len(cells) < 5:
            cells.append("")

        title, due_raw, category, details, link = cells[:5]

        if not title or title.lower() == "title":
            continue

        due_at = None
        if re.match(r"\d{4}-\d{2}-\d{2}", due_raw.strip()):
            due_at = due_raw.strip() + "T23:59:00-04:00"

        safe_link = link.strip() if link.strip().startswith("http") else None

        items.append({
            "id": "manual-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-"),
            "title": title,
            "course_short": category or "General",
            "course_id": None,
            "course_name": category or "General",
            "course_color": "#7c3aed",
            "course_bg": "#ede9fe",
            "due_at": due_at,
            "lock_at": None,
            "link": safe_link,
            "points": None,
            "weight": None,
            "details_html": f"<p>{details}</p>" if details else "",
            "type": "todo",
            "category": category or "General",
            "source": "manual",
            "urgency": compute_urgency(due_at),
            "syllabus_url": None,
            "readings": [],
            "files": [],
            "groups": [],
        })

    return items


# ──────────────────────────────────────────────────────────────
# Parse data/session-readings.md
# ──────────────────────────────────────────────────────────────

# Course info for readings (by course short name)
_READING_COURSE_INFO = {
    "Pharma":            {"color": "#4f46e5", "bg": "#ede9fe", "id": 249500},
    "Health Innovation": {"color": "#059669", "bg": "#dcfce7", "id": 246952},
    "EXEC/Grad":         {"color": "#d97706", "bg": "#fef3c7", "id": 47471},
}

def parse_session_readings():
    if not SESSION_READINGS_FILE.exists():
        print("  (session-readings.md not found — skipping)")
        return []

    items = []
    lines = SESSION_READINGS_FILE.read_text(encoding="utf-8").splitlines()
    in_table = False
    past_separator = False

    for line in lines:
        s = line.strip()

        if not s.startswith("|"):
            in_table = False
            past_separator = False
            continue

        if not in_table:
            in_table = True
            past_separator = False
            continue

        if re.match(r"^\|[\s\-|]+\|$", s):
            past_separator = True
            continue

        if not past_separator:
            continue

        cells = [c.strip() for c in s.strip("|").split("|")]
        while len(cells) < 8:
            cells.append("")

        title, course, session_key, due_raw, reading_type, file_status, link, details = cells[:8]

        if not title or title.lower() == "title":
            continue

        # Due = session date, read before class (set to 8am session morning)
        due_at = None
        if re.match(r"\d{4}-\d{2}-\d{2}", due_raw.strip()):
            due_at = due_raw.strip() + "T08:00:00-04:00"

        safe_link = link.strip() if link.strip().startswith("http") else None
        fs = file_status.strip().lower()  # "available", "pending", or blank

        cinfo = _READING_COURSE_INFO.get(course.strip(), {"color": "#6b7280", "bg": "#f3f4f6", "id": None})

        item_id = "reading-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]

        # Build details_html: description + pending callout if needed
        desc_html = f"<p>{details}</p>" if details.strip() else ""
        if fs == "pending":
            pending_html = (
                '<div class="pending-callout">'
                '⏳ <strong>File not yet uploaded to Canvas.</strong> '
                f'Check course Modules closer to the {due_raw.strip()} class date.'
                '</div>'
            )
        else:
            pending_html = ""

        items.append({
            "id":          item_id,
            "title":       title,
            "course_short": course.strip(),
            "course_id":   cinfo["id"],
            "course_name": course.strip(),
            "course_color": cinfo["color"],
            "course_bg":   cinfo["bg"],
            "due_at":      due_at,
            "lock_at":     None,
            "link":        safe_link,
            "points":      None,
            "weight":      None,
            "details_html": desc_html + pending_html,
            "type":        "reading",
            "reading_type": reading_type.strip() or "Required",
            "session_key": session_key.strip(),
            "file_status": fs or "n/a",
            "category":    course.strip(),
            "source":      "syllabus",
            "urgency":     compute_urgency(due_at),
            "syllabus_url": None,
            "readings":    [],
            "files":       [],
            "groups":      [],
        })

    return items


# ──────────────────────────────────────────────────────────────
# Group individual readings into one bundle card per session_key
# ──────────────────────────────────────────────────────────────

def group_readings_by_session(readings):
    """Collapse individual reading items into one reading_bundle per session_key."""

    buckets = defaultdict(list)
    for r in readings:
        sk = r.get("session_key") or "no-session"
        buckets[sk].append(r)

    bundles = []
    for sk, items in buckets.items():
        first = items[0]
        session_label = sk.replace("-", " ")   # "Pharma-S5" → "Pharma S5"

        due_dates = [i["due_at"] for i in items if i.get("due_at")]
        due_at = min(due_dates) if due_dates else None

        required    = [i for i in items if i.get("reading_type", "Required").lower() != "recommended"]
        recommended = [i for i in items if i.get("reading_type", "").lower() == "recommended"]

        def reading_html(r):
            title   = r["title"]
            link    = r.get("link")
            details = re.sub(
                r'<div class="pending-callout">.*?</div>', "",
                r.get("details_html", ""), flags=re.DOTALL,
            ).replace("<p>", "").replace("</p>", "").strip()

            title_html = (
                f'<a href="{link}" target="_blank" rel="noopener">{title}</a>'
                if link else title
            )
            html = f"<li>{title_html}"
            if details:
                html += f' <span class="reading-detail">— {details}</span>'
            if r.get("file_status") == "pending":
                due_str = (r.get("due_at") or "")[:10]
                html += (
                    '<div class="pending-callout">'
                    "⏳ <strong>File not yet uploaded to Canvas.</strong> "
                    f"Check course Modules closer to the {due_str} class date."
                    "</div>"
                )
            html += "</li>"
            return html

        html_parts = []
        if required:
            html_parts.append("<p><strong>Required Readings</strong></p><ul>")
            html_parts.extend(reading_html(r) for r in required)
            html_parts.append("</ul>")
        if recommended:
            html_parts.append("<p><strong>Recommended Readings</strong></p><ul>")
            html_parts.extend(reading_html(r) for r in recommended)
            html_parts.append("</ul>")

        readings_list = [
            {
                "title":        r["title"],
                "reading_type": r.get("reading_type", "Required"),
                "link":         r.get("link"),
                "file_status":  r.get("file_status", "n/a"),
            }
            for r in items
        ]

        all_pending = all(i.get("file_status") == "pending" for i in items)

        bundles.append({
            "id":           "bundle-" + re.sub(r"[^a-z0-9]+", "-", sk.lower()).strip("-"),
            "title":        f"{session_label} — Readings",
            "course_short": first["course_short"],
            "course_id":    first["course_id"],
            "course_name":  first["course_name"],
            "course_color": first["course_color"],
            "course_bg":    first["course_bg"],
            "due_at":       due_at,
            "lock_at":      None,
            "link":         None,
            "points":       None,
            "weight":       None,
            "details_html": "".join(html_parts),
            "type":         "reading_bundle",
            "session_key":  sk,
            "file_status":  "pending" if all_pending else "partial",
            "category":     first["course_short"],
            "source":       "syllabus",
            "urgency":      compute_urgency(due_at),
            "syllabus_url": None,
            "readings_list": readings_list,
            "readings":     [],
            "files":        [],
            "groups":       [],
        })

    bundles.sort(key=lambda b: (0 if b["due_at"] else 1, b["due_at"] or "", b["title"]))
    return bundles


# ──────────────────────────────────────────────────────────────
# Load data/schedule.json
# ──────────────────────────────────────────────────────────────

def load_schedule():
    if not SCHEDULE_FILE.exists():
        print("  (schedule.json not found — skipping)")
        return {}
    try:
        return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  WARNING: could not parse schedule.json: {e}")
        return {}


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    env = load_env()
    token = env.get("CANVAS_TOKEN", "").strip()
    base_url = env.get("CANVAS_BASE_URL", "https://courseworks2.columbia.edu").strip()

    if not token:
        print("ERROR: CANVAS_TOKEN not set. Create a .env file from .env.example.")
        raise SystemExit(1)

    DOCS_DIR.mkdir(exist_ok=True)

    all_items = []

    for course_id, info in TRACKED_COURSES.items():
        print(f"\n▸ {info['short']} (course {course_id})")

        # 1 — Assignments (with descriptions)
        print("  assignments … ", end="", flush=True)
        assignments = canvas_get(
            base_url, token,
            f"/api/v1/courses/{course_id}/assignments",
            {"per_page": "100"},
        )
        print(f"{len(assignments)} found")

        # 2 — Groups + members (for Health Innovation team assignments)
        print("  groups … ", end="", flush=True)
        groups_raw = canvas_get(
            base_url, token,
            f"/api/v1/courses/{course_id}/groups",
            {"per_page": "100"},
        )
        group_list = []
        for g in (groups_raw or []):
            members_raw = canvas_get(
                base_url, token,
                f"/api/v1/groups/{g['id']}/users",
                {"per_page": "100"},
            )
            names = [
                m.get("name") or m.get("display_name", "Unknown")
                for m in (members_raw or [])
            ]
            group_list.append({"name": g.get("name", ""), "members": names})
        print(f"{len(group_list)} group(s)")

        # 3 — Files (course-level, for the Files page link)
        print("  files … ", end="", flush=True)
        files_raw = canvas_get(
            base_url, token,
            f"/api/v1/courses/{course_id}/files",
            {"per_page": "100"},
        )
        print(f"{len(files_raw)} file(s)")

        # 4 — Syllabus link (constructed, no extra API call needed)
        syllabus_url = f"{base_url}/courses/{course_id}/assignments/syllabus"
        modules_url  = f"{base_url}/courses/{course_id}/modules"
        files_url    = f"{base_url}/courses/{course_id}/files"

        # 5 — Announcements (catch late grad paperwork in EXEC shell)
        print("  announcements … ", end="", flush=True)
        ann_raw = canvas_get(
            base_url, token,
            "/api/v1/announcements",
            {"context_codes[]": f"course_{course_id}", "per_page": "50"},
        )
        print(f"{len(ann_raw)} found")

        # ── Process assignments ──────────────────────────────────
        now_utc = datetime.now(timezone.utc)
        for a in (assignments or []):
            # Skip Pharma class participation (no deliverable)
            if course_id == 249500 and "participation" in (a.get("name") or "").lower():
                continue
            # Skip assignments already past due by more than 24 hours
            due_str = a.get("due_at") or ""
            if due_str:
                try:
                    due_dt = datetime.fromisoformat(due_str.replace("Z", "+00:00"))
                    if (now_utc - due_dt).total_seconds() > 24 * 3600:
                        continue
                except Exception:
                    pass

            item_groups = group_list if course_id == 246952 else []
            item_files  = [
                {"name": "Course Modules", "url": modules_url},
                {"name": "Course Files",   "url": files_url},
                {"name": "Syllabus",        "url": syllabus_url},
            ]

            all_items.append({
                "id":          f"canvas-{course_id}-{a['id']}",
                "title":       a.get("name", "Untitled"),
                "course_short": info["short"],
                "course_id":   course_id,
                "course_name": info["name"],
                "course_color": info["color"],
                "course_bg":   info["bg"],
                "due_at":      a.get("due_at"),
                "lock_at":     a.get("lock_at"),
                "link":        a.get("html_url") or f"{base_url}/courses/{course_id}/assignments/{a['id']}",
                "points":      a.get("points_possible"),
                "weight":      get_weight(course_id, a.get("name", "")),
                "details_html": sanitize_html(a.get("description", "")),
                "type":        "assignment",
                "category":    info["short"],
                "source":      "canvas",
                "urgency":     compute_urgency(a.get("due_at")),
                "syllabus_url": syllabus_url,
                "readings":    [],
                "files":       item_files,
                "groups":      item_groups,
            })

        # ── Surface EXEC announcements as undated to-do candidates ──
        if course_id == 47471 and ann_raw:
            cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            for ann in ann_raw:
                posted_str = ann.get("posted_at") or ann.get("created_at", "")
                try:
                    posted_dt = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))
                    if posted_dt < cutoff:
                        continue
                except Exception:
                    pass

                all_items.append({
                    "id":          f"ann-{course_id}-{ann['id']}",
                    "title":       ann.get("title", "Untitled announcement"),
                    "course_short": info["short"],
                    "course_id":   course_id,
                    "course_name": info["name"],
                    "course_color": info["color"],
                    "course_bg":   info["bg"],
                    "due_at":      None,
                    "lock_at":     None,
                    "link":        ann.get("url") or f"{base_url}/courses/{course_id}/discussion_topics",
                    "points":      None,
                    "weight":      None,
                    "details_html": sanitize_html(ann.get("message", "")),
                    "type":        "announcement",
                    "category":    "EXEC/Grad",
                    "source":      "canvas",
                    "urgency":     "undated",
                    "syllabus_url": syllabus_url,
                    "readings":    [],
                    "files":       [],
                    "groups":      [],
                })

    # ── Manual to-dos ────────────────────────────────────────────
    print("\n▸ Manual to-dos (data/manual-todos.md)")
    manual = parse_manual_todos()
    all_items.extend(manual)
    print(f"  {len(manual)} item(s)")

    # ── Session readings (grouped into bundles) ──────────────────
    print("\n▸ Session readings (data/session-readings.md)")
    readings = parse_session_readings()
    bundles  = group_readings_by_session(readings)
    all_items.extend(bundles)
    print(f"  {len(readings)} reading(s) → {len(bundles)} bundle(s)")

    # ── Schedule ─────────────────────────────────────────────────
    print("\n▸ Class schedule (data/schedule.json)")
    schedule = load_schedule()
    print(f"  {len(schedule.get('weekends', []))} weekend block(s)")

    # ── Split combined APEx "Exec Summary + Peer Review" if Canvas
    #    returns it as a single item rather than two separate ones ──
    expanded = []
    apex_peer_seen = False
    for item in all_items:
        title_lc = item["title"].lower()
        if (
            item.get("course_id") == 47471
            and "executive summary" in title_lc
            and "peer review" in title_lc
            and not apex_peer_seen
        ):
            apex_peer_seen = True
            # Executive Summary card
            summary_item = dict(item)
            summary_item["id"]    = item["id"] + "-summary"
            summary_item["title"] = "APEx: Executive Summary (Final)"
            expanded.append(summary_item)
            # Peer Review card — due June 28 (rubric must be returned to peer by email)
            peer_item = dict(item)
            peer_item["id"]     = item["id"] + "-peer-review"
            peer_item["title"]  = "APEx: Peer Review"
            peer_item["due_at"] = "2026-06-28T23:59:00-04:00"
            peer_item["urgency"] = compute_urgency("2026-06-28T23:59:00-04:00")
            peer_item["details_html"] = (
                "<p>Review your assigned peer's Executive Summary Draft and return a completed "
                "rubric to them by email no later than <strong>11:59pm Sunday, June 28</strong>. "
                "The department expects peer reviewers to meet with their peer to discuss comments.</p>"
                "<p>Your peer reviewer pairing is listed "
                '<a href="https://courseworks2.columbia.edu/courses/47471/files/26988702'
                '?verifier=1xKno9X03eErRfHqefwHDsHYINDsvyLPpsZb4Dpi&amp;wrap=1" '
                'target="_blank" rel="noopener noreferrer">here</a>.</p>'
                "<p>Peer Review Rubric: "
                '<a href="https://courseworks2.columbia.edu/courses/47471/files/19742606'
                '?verifier=J8fRJCYZGJlMa3rmbyuQrPrEUtc4IDR0ONEL9EZK&amp;wrap=1" '
                'target="_blank" rel="noopener noreferrer">Rubric for Executive Summary Peer Review</a></p>'
            )
            expanded.append(peer_item)
        else:
            expanded.append(item)
    all_items = expanded

    # ── De-duplicate by (course_id, normalised-title, due-date) ──
    seen = set()
    deduped = []
    for item in all_items:
        key = (
            item.get("course_id"),
            re.sub(r"\s+", " ", item["title"].lower().strip())[:80],
            (item.get("due_at") or "")[:10],
        )
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    # ── Sort: dated items by due_at, undated last ────────────────
    def sort_key(item):
        d = item.get("due_at") or ""
        return (0 if d else 1, d, item["title"])

    deduped.sort(key=sort_key)

    # ── Write docs/data.json ────────────────────────────────────
    generated_at = datetime.now().astimezone().isoformat()
    payload = {
        "generated_at": generated_at,
        "items": deduped,
        "courses": {str(k): v for k, v in TRACKED_COURSES.items()},
        "schedule": schedule,
    }
    DATA_FILE.write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )

    print(f"\n✓ Wrote {len(deduped)} items → docs/data.json")
    print(f"  Generated at: {generated_at}")


if __name__ == "__main__":
    main()
