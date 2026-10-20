#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "    UNIVERSAL AI AGENT WORKSTATION INSTALLER (UNIX/MAC)   "
echo "=========================================================="

OS="$(uname -s)"
ARCH="$(uname -m)"

echo "[+] Detected OS: $OS ($ARCH)"

INSTALL_DIR="$HOME/.agent-workstation"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# 1. Package Manager & System Dependencies
if [ "$OS" = "Darwin" ]; then
    echo "[+] Running on macOS (Apple Silicon / Intel)..."
    if ! command -v brew &>/dev/null; then
        echo "[*] Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv 2>/dev/null)"
    fi
    echo "[+] Updating packages via brew..."
    brew install git uv node pnpm gh awscli ollama || true
elif [ "$OS" = "Linux" ]; then
    echo "[+] Running on Linux..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update
        sudo apt-get install -y git curl build-essential
    fi
    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    # Install Ollama
    if ! command -v ollama &>/dev/null; then
        curl -fsSL https://ollama.com/install.sh | sh
    fi
fi

# Ensure uv, node, pnpm are in PATH
export PATH="$HOME/.local/bin:$HOME/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

# 2. Install Agent Harnesses
echo "[+] Installing AI Agent Harnesses..."
# Aider
uv tool install aider-chat || true
# Claude Code & Codex
npm install -g @anthropic-ai/claude-code @openai/codex || true

# 3. Pull Baseline Fast GPU Model for Ollama
if command -v ollama &>/dev/null; then
    echo "[+] Pulling Llama 3.2 1B baseline model into Ollama..."
    ollama serve &>/dev/null &
    sleep 2
    ollama pull llama3.2:1b || true
fi

# 4. Clone Workstation Repo & Setup Virtual Environment
REPO_DIR="$INSTALL_DIR/repo"
if [ ! -d "$REPO_DIR" ]; then
    echo "[+] Cloning agent workstation core files..."
    git clone https://github.com/dhurianiket/agent-workstation-setup.git "$REPO_DIR"
fi
cd "$REPO_DIR"

echo "[+] Setting up Python environment via uv..."
uv venv .venv
source .venv/bin/activate
uv pip install fastapi uvicorn boto3 requests

# 5. Install Global Agent Skills (~/.agents/skills)
SKILLS_DIR="$HOME/.agents/skills"
mkdir -p "$SKILLS_DIR"
if [ -d "$REPO_DIR/skills" ]; then
    echo "[+] Installing global skills into $SKILLS_DIR..."
    cp -r "$REPO_DIR/skills/"* "$SKILLS_DIR/"
fi

# 6. Create Launchd (macOS) or Systemd (Linux) background daemon for API Server
if [ "$OS" = "Darwin" ]; then
    PLIST_PATH="$HOME/Library/LaunchAgents/com.user.agent-ai-server.plist"
    echo "[+] Registering macOS background daemon in $PLIST_PATH..."
    cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.agent-ai-server</string>
    <key>ProgramArguments</key>
    <array>
        <string>$REPO_DIR/.venv/bin/python</string>
        <string>$REPO_DIR/laptop_api_server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$REPO_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/.agent-workstation/server.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.agent-workstation/server.err</string>
</dict>
</plist>
EOF
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    launchctl load "$PLIST_PATH"
fi

# 7. Symlink orchestrator CLI
mkdir -p "$HOME/.local/bin"
ln -sf "$REPO_DIR/orchestrate.py" "$HOME/.local/bin/orchestrate"
chmod +x "$REPO_DIR/orchestrate.py"

echo ""
echo "=========================================================="
echo " [OK] UNIVERSAL AGENT WORKSTATION INSTALLED SUCCESSFULLY! "
echo "=========================================================="
echo " - Local AI API Server : http://127.0.0.1:8000"
echo " - Orchestrator CLI    : orchestrate --task \"...\""
echo " - Next step: Run 'aws login --profile msi-lappy' to link credits."
echo "=========================================================="
