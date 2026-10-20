#!/usr/bin/env bash
# Universal AI Agent Workstation Installer for macOS & Linux (v3.4)
# Supports both 1-line remote install AND running inside a cloned repository:
#   Remote: curl -fsSL https://raw.githubusercontent.com/dhurianiket/agent-workstation-setup/main/install.sh | bash
#   Local : ./install.sh

set -e

echo "================================================================================"
echo "   ANTIGRAVITY AUTONOMOUS AI WORKSTATION — UNIVERSAL MAC / LINUX INSTALLER      "
echo "================================================================================"

OS="$(uname -s)"
ARCH="$(uname -m)"
echo "[1/6] Detected System: $OS ($ARCH)"

# 1. Package Manager & System Dependencies
if [ "$OS" = "Darwin" ]; then
    if ! command -v brew &>/dev/null; then
        echo "[*] Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv 2>/dev/null)"
    fi
    echo "[+] Installing Git, uv, Node, pnpm, and Ollama via Homebrew..."
    brew install git uv node pnpm gh ollama || true
elif [ "$OS" = "Linux" ]; then
    if command -v apt-get &>/dev/null; then
        sudo apt-get update && sudo apt-get install -y git curl build-essential python3-venv || true
    fi
    if ! command -v uv &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    if ! command -v ollama &>/dev/null; then
        curl -fsSL https://ollama.com/install.sh | sh
    fi
fi

export PATH="$HOME/.local/bin:$HOME/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

# 2. Resolve Repository Directory (use current folder if already cloned, else clone to ~/.agent-workstation/repo)
if [ -f "./tools/setup_wizard.py" ]; then
    REPO_DIR="$(pwd)"
    echo "[2/6] Using existing cloned repository at: $REPO_DIR"
else
    INSTALL_DIR="$HOME/.agent-workstation"
    mkdir -p "$INSTALL_DIR"
    REPO_DIR="$INSTALL_DIR/repo"
    if [ ! -d "$REPO_DIR/.git" ]; then
        echo "[2/6] Cloning agent-workstation-setup repository..."
        git clone https://github.com/dhurianiket/agent-workstation-setup.git "$REPO_DIR"
    else
        echo "[2/6] Updating existing workstation repository at $REPO_DIR..."
        git -C "$REPO_DIR" pull --ff-only || true
    fi
fi
cd "$REPO_DIR"

# 3. Install Agent Harnesses & GitGuardian Security Shield
echo "[3/6] Installing AI Agent Harnesses (Aider, GitGuardian ggshield, Claude Code, Codex)..."
uv tool install aider-chat || true
uv tool install ggshield || true
if command -v npm &>/dev/null; then
    npm install -g @anthropic-ai/claude-code @openai/codex || true
fi

# 4. Create Python Virtual Environment & Install Gateway + MCP + Graphify Packages
echo "[4/6] Creating Python virtual environment (.venv) and installing Gateway + Graphify + MCP..."
uv venv .venv
VENV_PY="$REPO_DIR/.venv/bin/python"
uv pip install --python "$VENV_PY" fastapi uvicorn boto3 pydantic requests mcp graphifyy ggshield

# 5. Run Cross-Platform Hardware Detector, Ollama Auto-Model Selector, API Key Wizard & 32-Repo Cloner
echo "[5/6] Launching Hardware-Adaptive Setup Wizard (Ollama Model + API Keys + 32 GitHub Repos)..."
"$VENV_PY" "$REPO_DIR/tools/setup_wizard.py"

# 6. Create Launchd (macOS) or Background Daemon for API Server on Port 8000
echo "[6/6] Starting Unified 5-Tier AI Gateway on http://127.0.0.1:8000 ..."
if [ "$OS" = "Darwin" ]; then
    mkdir -p "$HOME/Library/LaunchAgents"
    PLIST_PATH="$HOME/Library/LaunchAgents/com.antigravity.agent-workstation.plist"
    cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.antigravity.agent-workstation</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_PY</string>
        <string>$REPO_DIR/laptop_api_server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$REPO_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/.agent_workstation/server.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.agent_workstation/server.err</string>
</dict>
</plist>
EOF
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    launchctl load "$PLIST_PATH" 2>/dev/null || true
else
    nohup "$VENV_PY" "$REPO_DIR/laptop_api_server.py" > "$HOME/.agent_workstation/server.log" 2>&1 &
fi

mkdir -p "$HOME/.local/bin"
ln -sf "$REPO_DIR/orchestrate.py" "$HOME/.local/bin/orchestrate"
chmod +x "$REPO_DIR/orchestrate.py"

echo ""
echo "================================================================================"
echo " [OK] ANTIGRAVITY AUTONOMOUS WORKSTATION IS READY!"
echo "  • Live Web Dashboard        : http://127.0.0.1:8000/dashboard"
echo "  • Interactive Graphify File : http://127.0.0.1:8000/graphify"
echo "  • How It Works Guide        : python orchestrate.py --guide"
echo "================================================================================"
