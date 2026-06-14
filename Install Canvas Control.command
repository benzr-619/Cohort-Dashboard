#!/bin/bash
###############################################################################
#  Canvas Control — One-Time Setup
#  Just double-click this file. It does everything and asks you 2 questions.
###############################################################################

set -uo pipefail

clear
echo "=================================================="
echo "        Canvas Control  —  One-Time Setup"
echo "=================================================="
echo ""
echo "This sets up the bridge between Claude and your"
echo "school's Canvas. It takes about 3-5 minutes."
echo "You'll be asked 2 questions near the end."
echo ""
echo "--------------------------------------------------"

INSTALL_DIR="$HOME/canvas-control"

# Make sure tools we install can be found in this session
export PATH="$HOME/.local/bin:$PATH"

# ---------------------------------------------------------------------------
# 1. Install "uv" (the small engine that runs Canvas Control)
# ---------------------------------------------------------------------------
if ! command -v uv >/dev/null 2>&1; then
  echo ""
  echo "[1/4] Installing the engine (uv)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh || {
    echo "!! Could not install uv. Check your internet connection and try again."
    read -r -p "Press Return to close." ; exit 1
  }
else
  echo ""
  echo "[1/4] Engine already installed. Skipping."
fi
# Load uv into this session
source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"

# ---------------------------------------------------------------------------
# 2. Download Canvas Control
# ---------------------------------------------------------------------------
echo ""
echo "[2/4] Downloading Canvas Control..."
rm -rf "$INSTALL_DIR" "$HOME/canvas-control-main"
curl -L -o /tmp/canvas-control.zip \
  https://github.com/tomtranjr/canvas-control/archive/refs/heads/main.zip || {
    echo "!! Download failed. Check your internet connection and try again."
    read -r -p "Press Return to close." ; exit 1
  }
unzip -o -q /tmp/canvas-control.zip -d "$HOME"
mv "$HOME/canvas-control-main" "$INSTALL_DIR"

# ---------------------------------------------------------------------------
# 3. Install it
# ---------------------------------------------------------------------------
echo ""
echo "[3/4] Installing (this is the slowest step, please wait)..."
cd "$INSTALL_DIR"
uv venv --python 3.12 >/dev/null 2>&1
uv pip install -e '.' >/dev/null 2>&1 || {
  echo "!! Install step failed. Take a screenshot of this window and send it to Claude."
  read -r -p "Press Return to close." ; exit 1
}

VENV_PY="$INSTALL_DIR/.venv/bin/python"
UV_PATH="$(command -v uv)"

# ---------------------------------------------------------------------------
# 4. Ask for your 2 details and connect to Claude
# ---------------------------------------------------------------------------
echo ""
echo "[4/4] Last step — two quick questions:"
echo ""
echo "  Question 1: Your school's Canvas web address."
echo "  (Open Canvas in your browser and copy the start of the address,"
echo "   e.g.  https://harvard.instructure.com  )"
echo ""
read -r -p "  Paste it here and press Return: " CANVAS_BASE_URL
echo ""
echo "  Question 2: Your Canvas access token."
echo "  (Paste the long code. It will NOT appear on screen as you type —"
echo "   that's normal and for your security. Just paste and press Return.)"
echo ""
read -r -s -p "  Paste token here and press Return: " CANVAS_TOKEN
echo ""

CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# Use the Python that uv just installed (stock macOS may not have python3)
"$VENV_PY" - "$CONFIG" "$INSTALL_DIR" "$CANVAS_BASE_URL" "$CANVAS_TOKEN" "$UV_PATH" <<'PYEOF'
import json, sys, os, shutil, datetime
cfg, install_dir, base_url, token, uv_path = sys.argv[1:6]
os.makedirs(os.path.dirname(cfg), exist_ok=True)
data = {}
if os.path.exists(cfg):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy(cfg, cfg + ".backup-" + stamp)   # safety backup
    try:
        with open(cfg) as f:
            data = json.load(f)
    except Exception:
        data = {}
data.setdefault("mcpServers", {})
data["mcpServers"]["canvas"] = {
    "command": uv_path,
    "args": ["--directory", install_dir, "run", "cvsctl", "mcp", "serve"],
    "env": {
        "CANVAS_TOKEN": token,
        "CANVAS_BASE_URL": base_url.strip().rstrip("/"),
        "CANVAS_TIMEZONE": "America/New_York"
    }
}
with open(cfg, "w") as f:
    json.dump(data, f, indent=2)
print("Connected and saved.")
PYEOF

echo ""
echo "=================================================="
echo "  DONE!  Canvas is now connected to Claude."
echo "=================================================="
echo ""
echo "  Two final clicks:"
echo "   1) Quit Claude completely:  press  Cmd + Q"
echo "   2) Open Claude again, return to this chat, and"
echo "      type:   Canvas is connected"
echo ""
echo "  (Your timezone is set to US Eastern. If that's wrong,"
echo "   just tell Claude and it'll fix it.)"
echo ""
read -r -p "Press Return to close this window."
