#!/bin/bash
# HPM EXEC 2026 Deadline Board — Update & Publish
# Double-click this file to pull fresh data from Canvas and push to GitHub Pages.
# ─────────────────────────────────────────────────────────────────────────────

# Change to the directory this script lives in (project root)
cd "$(dirname "$0")"

echo ""
echo "═══════════════════════════════════════════════"
echo "  HPM EXEC 2026 · Deadline Board — Update"
echo "═══════════════════════════════════════════════"
echo ""

# ── Load .env ──────────────────────────────────────────────────
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "✓ Loaded .env"
else
    echo "ERROR: .env file not found."
    echo ""
    echo "Create one by copying .env.example:"
    echo "  cp .env.example .env"
    echo "Then fill in your CANVAS_TOKEN."
    echo ""
    read -rp "Press Enter to close..."
    exit 1
fi

# ── Check token ────────────────────────────────────────────────
if [ -z "$CANVAS_TOKEN" ] || [ "$CANVAS_TOKEN" = "your_canvas_token_here" ]; then
    echo "ERROR: CANVAS_TOKEN is not set in .env"
    echo ""
    echo "Open .env and paste in your Canvas access token."
    echo "You can generate one at:"
    echo "  https://courseworks2.columbia.edu/profile/settings"
    echo "  (Account → Settings → + New Access Token)"
    echo ""
    read -rp "Press Enter to close..."
    exit 1
fi

# ── Check Python 3 ─────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found."
    echo "Install Python 3 from https://python.org and try again."
    echo ""
    read -rp "Press Enter to close..."
    exit 1
fi

# ── Pull data from Canvas → docs/data.json ─────────────────────
echo ""
echo "Pulling data from Canvas..."
echo ""
python3 scripts/generate.py

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Data generation failed. See error above."
    echo ""
    read -rp "Press Enter to close..."
    exit 1
fi

# ── Check git ──────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
    echo ""
    echo "WARNING: git not found — skipping publish step."
    echo "Data was generated in docs/data.json but not pushed."
    echo ""
    read -rp "Press Enter to close..."
    exit 0
fi

# ── Init repo if needed ────────────────────────────────────────
if [ ! -d .git ]; then
    echo ""
    echo "No git repo found — initialising..."
    git init
    git add .
    git commit -m "Initial commit — HPM EXEC 2026 Deadline Board"
    echo ""
    echo "Repo initialised. To publish on GitHub Pages:"
    echo "  1. Create a repo at https://github.com/new"
    echo "  2. Run: git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
    echo "  3. Double-click this file again."
    echo ""
    read -rp "Press Enter to close..."
    exit 0
fi

# ── Stage changes ──────────────────────────────────────────────
echo ""
echo "Staging changes..."
git add docs/ data/

# Check if there's anything to commit
if git diff --staged --quiet; then
    echo "No changes to publish — data is already up to date."
    echo ""
    read -rp "Press Enter to close..."
    exit 0
fi

# ── Commit ─────────────────────────────────────────────────────
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
git commit -m "Update dashboard — ${TIMESTAMP}"

# ── Push ───────────────────────────────────────────────────────
REMOTE=$(git remote get-url origin 2>/dev/null)
if [ -z "$REMOTE" ]; then
    echo ""
    echo "WARNING: No git remote configured. Changes committed locally but not pushed."
    echo ""
    echo "To set up GitHub Pages publishing:"
    echo "  1. Create a repo at https://github.com/new"
    echo "  2. Run: git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
    echo "  3. In GitHub repo Settings → Pages → set source to main / /docs"
    echo "  4. Double-click this file again to push."
    echo ""
    read -rp "Press Enter to close..."
    exit 0
fi

echo ""
echo "Pushing to GitHub..."
git push -u origin main 2>/dev/null || git push -u origin master 2>/dev/null

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Published!"
    echo ""
    # Try to derive the GitHub Pages URL
    if [ -n "$GITHUB_REPO" ]; then
        # Extract user/repo from URL
        SLUG=$(echo "$GITHUB_REPO" | sed 's|https://github.com/||' | sed 's|\.git$||')
        USER=$(echo "$SLUG" | cut -d'/' -f1)
        REPO=$(echo "$SLUG" | cut -d'/' -f2)
        echo "  Live at: https://${USER}.github.io/${REPO}/"
    else
        SLUG=$(echo "$REMOTE" | sed 's|https://github.com/||' | sed 's|git@github.com:||' | sed 's|\.git$||')
        USER=$(echo "$SLUG" | cut -d'/' -f1)
        REPO=$(echo "$SLUG" | cut -d'/' -f2)
        echo "  Live at: https://${USER}.github.io/${REPO}/"
    fi
    echo ""
    echo "  (GitHub Pages may take ~1 minute to reflect the update.)"
else
    echo ""
    echo "Push failed — check your GitHub credentials or remote URL."
    echo "Changes are committed locally; run 'git push' manually to retry."
fi

echo ""
read -rp "Press Enter to close..."
