# Build Spec — MHA Cohort Deadline Board (FINAL SCOPE)

**Hand this file to Claude Code (Sonnet is fine).** It is complete and execution-ready. Scope is locked and will not change — the program ends August 2026, so don't build anything to "discover" courses dynamically. Build for exactly the courses below.

---

## 1. What we're building

An **interactive, app-like** static web dashboard (hosted on GitHub Pages) that a Columbia HPM EXEC 2026 student shares with classmates as a **group resource**. It surfaces every remaining assignment, graduation milestone, and to-do — **with full details inline so nobody has to go back to Canvas** — plus group rosters for team projects and links to syllabi and reading files.

This is **not** a personal progress tracker. There is **no private/per-user view and no submission status** — it only shows what's due and what it requires. (Ben tracks his own work separately.)

Data is static (pre-generated JSON), but the page must *feel* like an app — not a flat list. See §8.

**One output:** the public board in `/docs`. No token, no grades, no personal status.

Publishing is **manual** (a double-click "Update Dashboard" file). A separate weekly Claude task keeps the underlying tracker current (see CLAUDE.md).

---

## 2. Locked scope — track exactly these

Canvas base URL: **https://courseworks2.columbia.edu**

| What | Canvas course_id | Notes |
|------|------------------|-------|
| The Pharmaceutical Industry (P8237) | **249500** | 3 graded papers |
| Health Innovation & Technology (P8536) | **246952** | group project + per-session reflection quizzes + final presentation |
| EXEC Program (grad requirements) | **47471** | APEx capstone + ILE Culminating Paper + **any late-arriving grad paperwork** (see §6) |
| Health System Simulation / Competitive Health Strategy (P8556) | 247383 | **watch only** — no assignments expected; include the course but expect an empty list |

Everything else in the user's Canvas is intentionally excluded (concluded courses, RESIP residence-unit shells, Career Services, Pre-Orientation, OpenAI electives).

---

## 3. Credentials (critical)

- Read `CANVAS_TOKEN` and `CANVAS_BASE_URL` from a local `.env` (gitignored). `CANVAS_BASE_URL=https://courseworks2.columbia.edu`.
- The token must NEVER appear in any committed file, in `/docs`, or in git history. If it ever does, it must be regenerated in Canvas.
- Auth header for REST: `Authorization: Bearer $CANVAS_TOKEN`.
- The `canvas-control` CLI is installed at `~/canvas-control` (run via `uv --directory ~/canvas-control run cvsctl ...`) but **direct REST is preferred** for the build because it returns full assignment descriptions and group data the MCP tools don't.

---

## 4. Data to pull (per refresh)

For each tracked course (§2):

1. **Assignments WITH full detail** — `GET /api/v1/courses/:id/assignments?per_page=100`. Keep: `id`, `name`, `due_at`, `lock_at`, `unlock_at`, `points_possible`, `submission_types`, `html_url`, and **`description`** (HTML body — the "what's needed" detail that must render inline so users don't return to Canvas). Sanitize `description` HTML for the page (strip scripts/styles, keep text/links/lists). **Do NOT pull or store `has_submitted` / submission data — this is a group resource, not personal tracking.**
2. **Groups (for team projects)** — `GET /api/v1/courses/:id/groups?per_page=100`, then `GET /api/v1/groups/:gid/users` for members. Mainly relevant to Health Innovation (246952), where teams form in Session 2. **Degrade gracefully**: if no groups exist yet, omit the section rather than erroring. Member display names only — no emails.
3. **Files (syllabi + readings)** — `GET /api/v1/courses/:id/files?per_page=100` and `GET /api/v1/courses/:id/modules?include[]=items`. Capture syllabus file links and any reading/case files so the dashboard can link directly. For readings that are external citations (journal articles, HBS/Kellogg cases), link to the course Modules/Files page where they live; don't fabricate URLs.
4. **Syllabus** — `GET /api/v1/courses/:id?include[]=syllabus_body`.
5. **Announcements (catch late grad paperwork)** — `GET /api/v1/announcements?context_codes[]=course_47471` (and the other tracked courses). New graduation tasks, forms, or paperwork are often posted as announcements rather than assignments. The generator should surface recent announcements from the EXEC shell as candidate to-dos (see §6) so nothing slips through.

Merge in the **manual to-dos** (§6). De-duplicate by `(course_id, title, due_date)`.

---

## 5. Known content as of build time (seed / sanity-check)

The pipeline should reproduce at least these. Cross-check against `Assignment Tracker — Summer 2026.md` in this folder (authoritative human-readable snapshot).

**Pharma (249500):** Strategic Company Evaluation (due 2026-06-23, 20%, 2–3pp) · Policy Memo (due 2026-07-19, 25%, 2–3pp) · Final Synthesis Paper (due 2026-07-31, 40%, 5–7pp). Remaining sessions Jul 11–12 with assigned readings (see tracker).

**Health Innovation (246952):** per-session reflection quizzes ~1pt (Session 1 due 2026-06-15; more post as sessions occur) · Group Project written (50%) · Final Presentation & Demo (30%, Session 6 = Thu Aug 13). Pre-work: Google Skills GenAI path + 2 LinkedIn Learning modules.

**EXEC grad (47471):** APEx Executive Summary + Peer Review (7/1) · Slide Deck (7/8) · Presentations in person (Fri 7/10) · Work Deliverables (7/12) · **ILE Culminating Paper (due 2026-08-09**, lock 10/31).

---

## 6. Manual to-dos & late-arriving requirements (IMPORTANT — leave room for these)

The cohort's remaining requirements are NOT fully known in advance. New things will appear two ways, and the build must accommodate both:

**(a) New items inside Canvas** — e.g., graduation paperwork, a form, or a task posted later in the EXEC shell (47471), as an assignment OR as an announcement. These are caught automatically by the refresh (§4 steps 1 and 5). The weekly Claude task (CLAUDE.md) also flags them. No special handling needed beyond surfacing EXEC-shell announcements as candidate items.

**(b) Things that never hit Canvas** — e.g., the program emails the cohort a to-do ("submit X by Friday"). Ben needs an easy way to add these himself. Implement a **human-friendly manual file** the generator reads on every build:

- File: `data/manual-todos.md` — a simple Markdown table Ben can hand-edit (no JSON). Columns: `Title | Due (YYYY-MM-DD or blank) | Category | Details | Link`.
- `Category` is free text, e.g. `Grad requirement`, `Paperwork`, `Pharma`, `Health Innovation`, `General`.
- Blank `Due` is allowed (show under an "Undated to-dos" group, don't crash).
- The generator parses this table and merges its rows into the feed exactly like Canvas items, tagged `source: manual`.
- Also document (in a top comment of the file) that Ben can simply **ask Claude in any session to "add a to-do"** and Claude will append a row — then he double-clicks Update Dashboard to publish. This is the expected everyday path; hand-editing is the fallback.

The dashboard must render these clearly — see §8 (a dedicated **"To-dos & Grad Requirements"** grouping/badge so non-assignment items aren't lost among coursework).

---

## 7. Output

- `docs/data.json` — feed: `title`, `course_short`, `due_at`, `link`, `points`, `weight`, `details_html` (sanitized), `type`, `category`, `source` (`canvas`|`manual`), `urgency`, `readings[]`, `files[]`, `groups[]` (names + members, display names only). **No grades, no submission status, no emails.**
- `docs/index.html` — the interactive board (§8), self-contained, reads `data.json`. No token, no live Canvas calls at view time.
- Footer on every page: "Last updated {{generated_at}} · unofficial group resource, verify in CourseWorks."

---

## 8. Interactive dashboard requirements (the app-like feel)

This is a priority. Even though data is static, build a real little app:

- **Layout:** card/board view, not a flat table. Group by urgency (Overdue / This week / Next 2 weeks / Later) with a toggle to group by course instead. Include a distinct **"To-dos & Grad Requirements"** lane/badge so manual items and graduation paperwork stand out from coursework.
- **Expandable detail:** each item is a card showing title, course/category, due date with a **live countdown** ("4 days") and weight/points. Clicking expands to show the **full description inline** (`details_html`) plus readings and file links — users never need to open Canvas to know what's required.
- **Filters & controls:** filter chips by course/category; a text search box. Persist filter/sort choices in `localStorage`. (No "mark complete" — this isn't a personal tracker.)
- **Group surfacing:** for team-tied assignments (Health Innovation group project), show the **group name and members** on the card so people know who they're working with.
- **Readings as links:** list readings as clickable links (to the course file or Modules page). A per-course header chip links the **Syllabus**.
- **Urgency cues:** color/badge for items due < 48h; visually de-emphasize past items.
- **Mobile-first:** classmates will check on phones. Responsive, touch-friendly cards.
- **Polish allowed:** Chart.js / Grid.js / Mermaid from CDN are permitted (e.g., a small timeline or progress ring); keep everything else inline. No backend.

---

## 9. Hosting & publishing

1. Public GitHub repo (e.g. `hpm-exec-2026-deadlines`); Settings → Pages → `main` / `/docs`.
2. **`Update Dashboard.command`** (double-clickable, `chmod +x`): load `.env` → run pull+generate → `git add docs/ && git commit && git push` → print the live URL.
3. No cron in the repo. (Weekly content refresh is handled by the Claude scheduled task; Ben publishes when ready.)

---

## 10. Security checklist (must pass before first push)

- [ ] `.env` and any token-bearing file in `.gitignore`.
- [ ] `docs/` contains no token, no submission status, no grades, no emails.
- [ ] Group rosters use display names only.
- [ ] Git history never contained the token.
- [ ] Footer marks it an unofficial group resource.

---

## 11. Build order

1. Scaffold + `.env.example` + `.gitignore` + `data/manual-todos.md` (with header comment + example row).
2. Canvas REST client (assignments+descriptions, groups+members, files, modules, syllabus, announcements) for the 4 course IDs in §2.
3. Parse `manual-todos.md`; merge; filter; compute urgency/countdown → `data.json`.
4. Interactive HTML generator per §8.
5. `Update Dashboard.command` + repo/Pages setup.
6. Verify against §10 and confirm the seed items in §5 appear with descriptions, readings, and (if present) groups; confirm a manual-todo row and an EXEC announcement both show up in the "To-dos & Grad Requirements" lane.

---

## Appendix — reference files in this folder
- `Assignment Tracker — Summer 2026.md` — authoritative human snapshot (content cross-check).
- `EXEC Class of 2026 Course Schedule Sept 2024-Aug 2026.pdf` — schedule of record.
- `syllabi/` — downloaded course syllabi (.docx) for Pharma and Health Innovation.
