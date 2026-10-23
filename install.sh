#!/usr/bin/env bash
# Universal AI Agent Workstation Installer for macOS & Linux (v3.6)
# Zero-friction 1-step setup — works via remote 1-liner OR inside a cloned repository:
#   Remote: curl -fsSL https://raw.githubusercontent.com/dhurianiket/agent-workstation-setup/main/install.sh | bash
#   Local : ./install.sh

set -e

echo "================================================================================"
echo "   ANTIGRAVITY AUTONOMOUS AI WORKSTATION — UNIVERSAL MAC / LINUX INSTALLER      "
echo "================================================================================"

OS="$(uname -s)"
ARCH="$(uname -m)"
echo "[1/5] Detected System: $OS ($ARCH)"

export PATH="$HOME/.local/bin:$HOME/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

# 1. Lightweight Dependency Check (never block on interactive sudo if git/uv exist)
if ! command -v uv &>/dev/null; then
    echo "[*] Installing uv (fast Python & tool manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh || true
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if [ "$OS" = "Darwin" ]; then
    if command -v brew &>/dev/null; then
        echo "[+] Ensuring Git, uv, and Ollama via Homebrew..."
        brew install git uv ollama 2>/dev/null || true
    fi
elif [ "$OS" = "Linux" ]; then
    if ! command -v git &>/dev/null && command -v apt-get &>/dev/null; then
        sudo apt-get update && sudo apt-get install -y git curl python3-venv || true
    fi
    if ! command -v ollama &>/dev/null; then
        curl -fsSL https://ollama.com/install.sh | sh || true
    fi
fi

# 2. Resolve Repository Directory (always mirror to ~/.agent-workstation/repo for clean APFS daemon support)
INSTALL_DIR="$HOME/.agent-workstation"
mkdir -p "$INSTALL_DIR"
CANONICAL_REPO="$INSTALL_DIR/repo"

if [ -f "./tools/setup_wizard.py" ]; then
    SRC_DIR="$(pwd)"
    echo "[2/5] Found cloned repository at: $SRC_DIR"
    if [ "$SRC_DIR" != "$CANONICAL_REPO" ]; then
        echo "      Syncing runtime engine to $CANONICAL_REPO ..."
        mkdir -p "$CANONICAL_REPO"
        rsync -a --exclude '.venv' --exclude 'tools/*/*' --exclude '._*' "$SRC_DIR/" "$CANONICAL_REPO/" 2>/dev/null || cp -R "$SRC_DIR/." "$CANONICAL_REPO/" 2>/dev/null || true
    fi
else
    if [ ! -d "$CANONICAL_REPO/.git" ]; then
        echo "[2/5] Cloning agent-workstation-setup repository..."
        git clone https://github.com/dhurianiket/agent-workstation-setup.git "$CANONICAL_REPO"
    else
        echo "[2/5] Updating existing workstation repository at $CANONICAL_REPO..."
        git -C "$CANONICAL_REPO" pull --ff-only || true
    fi
fi
cd "$CANONICAL_REPO"

# 3. Install Agent Harnesses & GitGuardian Security Shield
echo "[3/5] Installing AI Agent Harnesses (Aider, GitGuardian ggshield)..."
if command -v uv &>/dev/null; then
    uv tool install aider-chat 2>/dev/null || true
    uv tool install ggshield 2>/dev/null || true
fi
if command -v npm &>/dev/null; then
    npm install -g @anthropic-ai/claude-code @openai/codex 2>/dev/null || true
fi

# 4. Create Python Virtual Environment & Install Gateway + MCP + Graphify Packages
echo "[4/5] Creating Python virtual environment (.venv) and installing Gateway + Graphify + MCP..."
if command -v uv &>/dev/null; then
    if [ ! -x "$CANONICAL_REPO/.venv/bin/python" ]; then
        uv venv "$CANONICAL_REPO/.venv" --python 3.13 2>/dev/null || uv venv "$CANONICAL_REPO/.venv"
    fi
    VENV_PY="$CANONICAL_REPO/.venv/bin/python"
    uv pip install --python "$VENV_PY" fastapi uvicorn boto3 pydantic requests "mcp<2" graphifyy ggshield
else
    python3 -m venv "$CANONICAL_REPO/.venv"
    VENV_PY="$CANONICAL_REPO/.venv/bin/python"
    "$VENV_PY" -m pip install --upgrade pip
    "$VENV_PY" -m pip install fastapi uvicorn boto3 pydantic requests "mcp<2" graphifyy ggshield
fi

# 5. Launch All-In-One Setup Wizard (prompts for API keys/AWS via /dev/tty, clones 32 repos, registers hooks/MCP, starts port 8000 daemon)
echo "[5/5] Running All-In-One Setup Wizard (Hardware Detection + Personal API Keys + 32 Repos + Daemon)..."
"$VENV_PY" "$CANONICAL_REPO/tools/setup_wizard.py" "$@"

mkdir -p "$HOME/.local/bin"
ln -sf "$CANONICAL_REPO/orchestrate.py" "$HOME/.local/bin/orchestrate"
chmod +x "$CANONICAL_REPO/orchestrate.py"

echo ""
echo "================================================================================"
echo " [OK] ANTIGRAVITY AUTONOMOUS WORKSTATION IS READY!"
echo "  • Live Web Dashboard & API Keys : http://127.0.0.1:8000/dashboard"
echo "  • Interactive Graphify AST      : http://127.0.0.1:8000/graphify"
echo "  • Re-run Key Setup Anytime      : python3 ~/.agent-workstation/repo/tools/setup_wizard.py"
echo "================================================================================"
