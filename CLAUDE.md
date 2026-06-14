# CLAUDE.md — Canvas Control / MHA Deadline Tracker

Context for any new session working in this folder. Read this first.

## Who & what
Ben is an executive MHA student at **Columbia Mailman, Health Policy & Management, EXEC Class of 2026**, finishing in **August 2026**. This project keeps track of his remaining assignments and graduation requirements, and builds a shareable deadline dashboard for his cohort. He is **not a software engineer** — prefer double-click files over terminal instructions, and explain plainly.

## How Canvas is connected
A local MCP server named **`canvas`** (the `canvas-control` tool, installed at `~/canvas-control`) is wired into Claude Desktop. It talks to Columbia's Canvas at **https://courseworks2.columbia.edu**. Useful tools: `list_courses`, `get_upcoming_assignments` (takes `course_id`, `days_ahead`), `get_syllabus`, `search_course_files`, `download_selected_files`, `get_announcements`, `get_calendar_events`, `get_grades_summary`. The token lives in Claude Desktop's config (not in this repo) — never print or commit it.

## Locked scope (won't change — program ends Aug 2026)
Track ONLY:
- **Pharma — The Pharmaceutical Industry (P8237)** → course_id **249500**
- **Health Innovation & Technology (P8536)** → course_id **246952**
- **EXEC Program** (graduation items: APEx + ILE) → course_id **47471**
- **Health System Simulation (P8556)** → course_id **247383** — watch only, no assignments expected.

Everything else is intentionally muted (concluded courses, RESIP residence units, Career Services, Pre-Orientation, OpenAI electives). Do not re-litigate the whitelist.

## Key deadlines (see the tracker for full detail)
Pharma: Strategic Company Evaluation 6/23 (20%), Policy Memo 7/19 (25%), Final Synthesis Paper 7/31 (40%).
Health Innovation: per-session reflection quizzes (Session 1 due 6/15), Group Project (50%) + Final Presentation 8/13 (30%).
Graduation (EXEC shell): APEx Exec Summary 7/1, Slide Deck 7/8, in-person Presentations 7/10, Work Deliverables 7/12, **ILE Culminating Paper 8/9** (the capstone).

## Files in this folder
- `Assignment Tracker — Summer 2026.md` — **authoritative human-readable snapshot.** Update this when refreshing.
- `BUILD SPEC — Cohort Deadline Board.md` — spec for building the interactive GitHub Pages dashboard (intended for Claude Code + Sonnet).
- `EXEC Class of 2026 Course Schedule Sept 2024-Aug 2026.pdf` — schedule of record (file_id 27265017 in EXEC shell 47471).
- `syllabi/` — downloaded course syllabi (.docx).
- `Install Canvas Control.command`, `START HERE — Canvas Tracker Setup.md` — one-time setup (already done).

## How to "refresh the tracker"
1. Call `get_upcoming_assignments` for 249500, 246952, and 47471 (use a wide `days_ahead`, e.g. 120). Also check `get_announcements` for 47471 — late graduation paperwork/forms often arrive as announcements, not assignments.
2. Compare results to `Assignment Tracker — Summer 2026.md`.
3. Update the tracker file with any new/changed assignments; note what changed at the top.
4. A weekly scheduled task ("weekly-canvas-refresh") does this automatically every Monday and reports what's new.

## New requirements & manual to-dos
The cohort's remaining requirements are not fully known in advance. New graduation paperwork may appear later in the EXEC shell (47471) as an assignment OR an announcement — the refresh catches both. Things that never hit Canvas (e.g. a to-do emailed to the cohort) go in `data/manual-todos.md` (simple Markdown table; built by Claude Code per the build spec). When Ben says "add a to-do," append a row there; it then shows on the dashboard after he runs Update Dashboard.

## Dashboard = group resource only
The shared dashboard surfaces deadlines + assignment details + group rosters for Ben's classmates. There is **no private/per-user view and no submission status** — Ben tracks his own work separately.

## Conventions
- Save deliverables to this folder; share with the user via the file-card tool.
- Times are US Eastern (America/New_York).
- Never commit or display the Canvas token. Public dashboard = deadlines + assignment details + group names only; no grades, no submission status.
- Keep responses concise; Ben prefers minimal fluff.
