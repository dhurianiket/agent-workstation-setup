# Universal AI Agent Workstation Setup

One-command autonomous AI developer workstation setup for **macOS (Apple Silicon & Intel)**, **Windows**, and **Linux**.

Brings your entire AI multi-agent stack, frontier Bedrock models (Claude 4.5 Sonnet & Opus, DeepSeek R1, Meta Llama 3.3), local discrete GPU inference (Ollama), and specialized agent harnesses (Aider, Claude Code, Codex, OpenCode) to any laptop, Mac, or PC with a single command.

---

## Quickstart: 1-Command Installation

### For macOS (Office Mac, MacBook Pro, iMac) & Linux
Run this in your terminal:
```bash
curl -sSL https://raw.githubusercontent.com/dhurianiket/agent-workstation-setup/main/install.sh | bash
```

### For Windows (PC / Laptop)
Run this in PowerShell as Administrator or standard user:
```powershell
irm https://raw.githubusercontent.com/dhurianiket/agent-workstation-setup/main/install.ps1 | iex
```

---

## What It Automatically Sets Up

1. **Development Runtime & Package Managers**:
   - `uv` (Fastest Python package manager)
   - Node.js & `pnpm`
   - Git with long file paths enabled
   - GitHub CLI (`gh`)
   - AWS CLI v2 configured for SSO / `aws login`

2. **Agent Harnesses**:
   - **Claude Code**: `@anthropic-ai/claude-code`
   - **Codex CLI**: `@openai/codex`
   - **Aider Chat**: `aider-chat`
   - **OpenCode**: Lightweight terminal agent

3. **Unified OpenAI-Compatible AI API Server (`http://127.0.0.1:8000`)**:
   - Drops in as a standard OpenAI endpoint (`/v1/chat/completions` with SSE streaming).
   - Routes to **AWS Bedrock** under your AWS Startup program credits:
     * `claude` / `sonnet` -> Claude Sonnet 4.5 (State-of-the-Art Coding)
     * `opus` -> Claude Opus 4.5 (Deep Reasoning & Systems Design)
     * `reasoner` -> DeepSeek-R1 (671B MoE with full chain-of-thought)
     * `coder` -> Meta Llama 3.3 70B (Fast high-throughput coder)
     * `fast` -> Meta Llama 4 Scout (17B sub-200ms inner loop coder)
     * `pixtral` -> Mistral Pixtral Large (Multimodal vision)
     * `local` -> Local GPU Ollama engine

4. **Zero-Touch Background Automation**:
   - **macOS**: `launchd` user daemon automatically starts the API server on login.
   - **Windows**: Silent VBScript startup launcher runs the server in hidden mode on boot.
   - **Self-Healing Guard**: If the server is ever stopped, the CLI orchestrator auto-starts it in 2 seconds.

5. **Curated Agent Skills & Tools**:
   - **`agent-orchestrator`**: Master controller skill for Antigravity, Claude Code, and Codex.
   - **`graphify`**: Codebase AST knowledge graph without vector stores.
   - **`ui-ux-pro-max`**: Professional UI/UX, typography, component guidelines, and color theory.
   - **`apple-design`**: Apple Human Interface Guidelines (HIG) and physics-based animations.
   - **`agent-reach`**: Web intelligence across Twitter, Reddit, YouTube, and GitHub with zero API keys.
   - **`agentmemory`**: Persistent cross-session agent memory.
   - **`strix`**: AI-powered security auditing and penetration testing.

---

## Usage Cheat Sheet

### 1. Dispatching Tasks via Orchestrator
```bash
# SOTA Coding with Claude Sonnet 4.5
python orchestrate.py --task "Implement OAuth2 PKCE login" --agent aider --model claude

# Complex Systems Architecture with Claude Opus 4.5
python orchestrate.py --task "Design resilient event bus architecture" --agent aider --model opus

# Mathematical Logic with DeepSeek R1
python orchestrate.py --task "Refactor search algorithm with zero allocations" --agent aider --model reasoner
```

### 2. Direct Aider Invocations
```bash
aider --openai-api-base http://127.0.0.1:8000/v1 --openai-api-key dummy --model openai/claude
```

### 3. System & Agent Status Check
```bash
# Windows
powershell -ExecutionPolicy Bypass -File .\ai_agent_status.ps1

# macOS / Linux
python check_status.py
```
