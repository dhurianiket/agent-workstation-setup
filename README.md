# Agent Workstation OS (v2.0)

> Turn any Mac, Windows, or Linux machine into an autonomous, cost-protected AI development powerhouse with one command.

Brings together frontier cloud models (**Claude 4.5 Sonnet/Opus, DeepSeek R1, Llama 3.3 70B, Llama 4 Scout** via AWS Startup credits or custom credentials), local discrete GPU inference (**Ollama on Apple Metal / AMD / NVIDIA**), and battle-tested agent harnesses (**Aider, Claude Code, Codex, OpenCode**) behind a zero-maintenance OpenAI-compatible gateway with **automatic credit protection and fallback**.

---

## ⚡ 1-Command Setup

### macOS (Apple Silicon M1-M4 / Intel) & Linux
```bash
curl -sSL https://raw.githubusercontent.com/dhurianiket/agent-workstation-setup/main/install.sh | bash
```

### Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/dhurianiket/agent-workstation-setup/main/install.ps1 | iex
```

---

## 💻 Multi-Device Setup Guide (Mac, iMac, Mac Studio, Windows PC & Linux)

This setup is 100% portable. You can spin it up on your **Office Mac, iMac, Mac Studio (M1/M2/M3/M4), Windows workstation, or Linux cloud instance** with your own AWS subscription, provider credentials, or offline local GPUs.

### 1. Zero-Secret-Leakage Configuration
We strictly enforce a **Zero-Leakage Security Policy**. Credentials, API keys, and session tokens must never be committed to git or printed in logs.

1. Clone or navigate to the workstation directory:
   ```bash
   git clone https://github.com/dhurianiket/agent-workstation-setup.git
   cd agent-workstation-setup
   ```
2. Copy the safe configuration template to `.env` (`.gitignore` protects `.env` from ever being tracked):
   ```bash
   cp .env.example .env
   ```

---

### 2. Configure Your AI Backends & Subscriptions

#### Option A: AWS Bedrock (Claude 4.5, DeepSeek R1, Llama 3.3)
If you have AWS Startup credits or an existing AWS account:
1. Configure your AWS profile using the AWS CLI:
   ```bash
   aws configure --profile my-profile
   # Or using AWS IAM Identity Center (SSO):
   aws sso login --profile my-profile
   ```
2. In your `.env` file, specify your profile and region:
   ```env
   AWS_PROFILE=my-profile
   AWS_DEFAULT_REGION=us-east-1
   ```

#### Option B: Bring Your Own Keys (BYOK) - OpenRouter, NVIDIA, DeepSeek, Groq, OpenAI
No AWS account? You can use direct provider keys with zero code changes:
1. Open `.env` and set any key(s) you possess:
   ```env
   # Access Claude 3.5, DeepSeek R1, and Llama 3.3 with 1 key:
   OPENROUTER_API_KEY=sk-or-v1-...

   # Or free/cloud inference via NVIDIA NIM:
   NVIDIA_API_KEY=nvapi-...

   # Or direct API keys:
   DEEPSEEK_API_KEY=sk-...
   GROQ_API_KEY=gsk_...
   OPENAI_API_KEY=sk-proj-...
   ```
2. The gateway auto-detects configured keys and routes models automatically.

#### Option C: Apple Silicon Unified GPU (Mac, iMac, Mac Studio)
Macs with M-series chips (M1/M2/M3/M4 Pro/Max/Ultra) use unified memory and Metal acceleration, making local inference exceptionally fast and **100% free ($0.00)**:
1. Start Ollama:
   ```bash
   brew install ollama
   ollama serve
   ```
2. Pull your preferred local models:
   ```bash
   # Lightweight & ultra-fast (8GB+ RAM):
   ollama pull llama3.2:1b

   # Heavyweight local coder (16GB - 64GB+ RAM on Mac Studio / MacBook Pro):
   ollama pull qwen2.5-coder:7b
   ollama pull qwen2.5-coder:14b
   ```

#### Option D: Windows / Linux PC with Discrete GPU
- **NVIDIA GPU**: Ollama auto-detects CUDA acceleration.
- **AMD Radeon GPU**: Offloaded automatically via Vulkan / ROCm.
- Set Windows power plan to **Ultimate Performance** for peak throughput.

---

## 🚀 Native Antigravity Pro Integration: Zero-Prompt Auto-Orchestration

You **never** have to manually prompt `"orchestrate task X using aider"` or re-explain your environment across sessions or projects. When paired with your **Antigravity Pro subscription**, the orchestration stack is **always active by default**:

```
           [Your Natural Request in Antigravity]
           "Build a WebSocket reconnect handler for our OTT player"
                             │
                             ▼
 ┌──────────────────────────────────────────────────────────────┐
 │     Antigravity Pro Autonomous Orchestration Engine          │
 │                                                              │
 │  1. AST & Dependency Analysis (graphify AST scan)            │
 │  2. Smart 5-Tier Model Selection (preserves AWS credits)     │
 │  3. Principal Engineer Standard (100% complete code,         │
 │     zero lazy placeholders, strict TypeScript/Python types)  │
 │  4. Closed-Loop Auto-Verification (syntax, tests, git diff)  │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
               [Verified, Production-Ready Code]
```

### What This Gives You:
1. **Always-On Autonomous Orchestration**: Antigravity automatically manages triage, planning, multi-file edits, and testing without requiring manual invocation phrases.
2. **Principal Engineer Code Quality**: Eliminates lazy completions (`// rest unchanged` or `/* existing code */`). Every code modification is 100% complete, defensively typed, and wrapped with error boundaries.
3. **Closed-Loop Auto-Verification**: Never leaves broken builds. Automatically validates syntax (`python -m py_compile`, `tsc --noEmit`), runs test suites, and audits `git status -s` before declaring done.

---

## 🔒 GitGuardian (`ggshield`) Secret Shield & AST Sensors

The workstation features a dual-layer automated verification gate built directly into `orchestrate.py`:

```
                 [Agent Modifies Files]
                           │
                           ▼
     ┌───────────────────────────────────────────┐
     │      Deterministic Post-Action Sensors    │
     │                                           │
     │  1. AST & Bytecode Check:                 │
     │     • Python (py_compile) syntax check    │
     │     • JSON valid parse audit              │
     │     • Node.js (--check) syntax validation │
     │                                           │
     │  2. GitGuardian (ggshield) Secret Gate:   │
     │     • Scans all modified files for keys   │
     │     • BLOCKS commits if secrets detected  │
     │     • 100% Zero-Leakage Guarantee         │
     └─────────────────────┬─────────────────────┘
                           │
                           ▼
          [Verified & Secure Git Commit / Push]
```

* **GitGuardian Secret Scan**: Every task automatically passes through `ggshield` to verify that no AWS tokens, private keys, API secrets, or passwords are exposed before committing or pushing.
* **Code Constitution AST Sensor**: Scans Python AST for anti-patterns (blocks bare `except:`, detects mutable default parameters, ensures complete implementations).
* **Frontier Critic Consensus (`--judge`)**: Dispatches the diff to a reasoning model (DeepSeek R1 / Claude Sonnet 4.5) to critique logic, catch regressions, and verify that the diff strictly satisfies requirements before merging.
* **Continuous Error Memory**: Failures are logged to `~/.agent_workstation/postmortems.json`, and historical lessons are automatically injected into future prompts to eliminate repetitive regression loops.

---

## 🌐 Interactive Web & Telemetry Dashboard

The workstation includes a self-contained, real-time developer control plane running natively at:
**`http://127.0.0.1:8000/dashboard`** (or `http://127.0.0.1:8000/status`)

* **Live Health & Latency**: Real-time ping to all configured providers (AWS Bedrock, Ollama AMD/Apple/NVIDIA GPU, OpenRouter, NVIDIA, OpenAI).
* **Credit Spend & Savings Meter**: Displays exact USD expenditure and calculates smart-tier dollars saved vs frontier model baselines.
* **Token Breakdown**: Granular input/output tokens tracked per model.
* **In-Browser Playground**: Test prompts across tiers with sub-second feedback and token usage inspection.

---

## 🔌 Model Context Protocol (MCP) Server (Cursor, Claude Code, Windsurf, Antigravity)

Connect the entire workstation engine directly into **Cursor, Claude Code, Windsurf, or Antigravity** via the native FastMCP server (`agent_workstation_mcp.py`):

Add to your `claude_desktop_config.json`, `mcpServers`, or Cursor MCP settings:
```json
{
  "mcpServers": {
    "workstation": {
      "command": "python",
      "args": [
        "c:/path/to/agent-workstation-setup/agent_workstation_mcp.py"
      ]
    }
  }
}
```

### Exposed MCP Tools:
* `workstation_health`: Live gateway health, latencies, and provider availability.
* `workstation_spend`: Real-time token consumption and smart-tier savings metrics.
* `workstation_orchestrate`: Dispatches tasks with AST sensor validation, Code Constitution rules, and 5-tier routing.
* `workstation_judge`: Runs Frontier Critic consensus review on git diffs via DeepSeek R1 reasoning.
* `workstation_scan_secrets`: Runs GitGuardian `ggshield` secret audits across staged/modified files to guarantee zero key leakage.
* `workstation_list_tools`: Returns status and capabilities of all 32 curated tools.

---

## 🐳 Dockerized Sandbox Execution (Linux, Mac & Windows)

For developers who prefer running the workstation in an isolated, sandboxed environment without touching host packages:

```bash
# 1. Configure credentials in .env
cp .env.example .env

# 2. Build and launch containerized gateway
docker compose up -d

# 3. Verify health & dashboard
curl http://localhost:8000/health
# Open http://localhost:8000/dashboard in your browser
```

---

## 🧰 Curated Tools & Frameworks Manager

Manage, audit, and synchronize all 32 curated AI developer tools, harnesses, and skills:
```bash
# Audit installed tools
python tools/manage_tools.py audit

# Synchronize and clone missing repositories
python tools/manage_tools.py sync
```

See [tools_manifest.md](tools_manifest.md) for the full catalog of all 32 curated tools.

---

## 🛡️ Credit Guard & Anti-Depletion Architecture

1. **Smart Auto-Tiered Routing (`--model auto` by default)**:
   - Evaluates task complexity automatically.
   - Routes routine tasks (formatting, linting, docs, boilerplate, unit tests) to **Local GPU ($0.00)** or **Llama 4 Scout ($0.08/M tokens)**.
   - Routes general full-stack coding to **Llama 3.3 70B ($0.72/M tokens)**.
   - Reserves **DeepSeek R1** and **Claude Sonnet 4.5** exclusively for deep reasoning, architectural design, and complex debugging.
   - **Result**: Reduces credit burn by up to 90% while providing sub-300ms iteration speed.

2. **Zero-Downtime Auto-Fallback**:
   - If a high-tier model hits rate limits, quotas, or credit exhaustion, the gateway immediately cascades:
     $$\text{Opus} \longrightarrow \text{Sonnet} \longrightarrow \text{DeepSeek R1} \longrightarrow \text{Llama 3.3 70B} \longrightarrow \text{Llama 4 Scout} \longrightarrow \text{Local Ollama}$$
   - Workflows never crash with 500 errors.

3. **Live Usage & Credit Analytics**:
   ```bash
   python orchestrate.py --usage
   ```
   Inspect total token consumption, per-model request counts, and estimated USD spend tracked in `~/.agent_workstation/usage_stats.json`.

---

## 🎛️ Tiered Model Routing Matrix

| Tier | Alias | Real Model ID | Latency | Est. Cost / 1M Toks | Best Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Local (Free)** | `local` | `llama3.2:1b` (Ollama GPU) | ~17ms | **$0.00** | Formatting, linting, comments, offline work |
| **Scout** | `fast` | `us.meta.llama4-scout-17b-instruct-v1:0` | ~190ms | **~$0.08 in / $0.30 out** | Unit tests, boilerplate, HTML/CSS, configs |
| **Workhorse** | `coder` | `us.meta.llama3-3-70b-instruct-v1:0` | ~300ms | **~$0.72 in / $0.72 out** | Full-stack features, API endpoints, refactoring |
| **Reasoning** | `reasoner` | `us.deepseek.r1-v1:0` | ~1.1s | **~$1.35 in / $2.19 out** | Algorithms, complex bug triage, math |
| **Frontier** | `claude` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | ~2.0s | **~$3.00 in / $15.00 out** | High-level system architecture & security review |

---

## 🚀 CLI Usage (Optional Manual Control)

```bash
# Auto-tiering (Default: intelligent routing based on task)
python orchestrate.py -t "Refactor the authentication flow with JWT refresh tokens"

# Target specific agent harnesses
python orchestrate.py -a aider -t "Fix null pointer in user profile component"
python orchestrate.py -a claude -t "Audit API security and rate limiting"

# Force specific model tier
python orchestrate.py -m fast -t "Generate unit tests for auth middleware"
python orchestrate.py -m reasoner -t "Debug memory leak in WebSocket stream"

# Check token consumption and credit spend
python orchestrate.py --usage
```

---

## 🧰 Bundled Superpowers & Skills

* **`graphify`**: Codebase AST knowledge graph without vector databases.
* **`ui-ux-pro-max`**: Design intelligence, typography, spacing, and component guidelines.
* **`apple-design`**: Apple Human Interface Guidelines (HIG) and physics-based motion.
* **`agent-reach`**: Search Twitter, Reddit, YouTube, and GitHub with zero API fees.
* **`agentmemory`**: Persistent cross-session memory for AI coding agents.
* **`strix`**: AI penetration testing and automated vulnerability patch diffs.
* **`auto-editor`**: Automatic silence and dead-air cutting for video/audio.
* **`9router`**: 40+ provider fallback router with -40% RTK token reduction.

---

## 📄 License
MIT License. Built for modern, high-speed autonomous software engineering.
