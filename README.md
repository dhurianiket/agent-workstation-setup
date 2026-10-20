# Agent Workstation OS (v2.0)

> Turn any Mac, Windows, or Linux machine into an autonomous, cost-protected AI development powerhouse with one command.

Brings together frontier cloud models (**Claude 4.5 Sonnet/Opus, DeepSeek R1, Llama 3.3 70B, Llama 4 Scout** via AWS Startup credits), local discrete GPU inference (**Ollama on AMD/NVIDIA/Metal**), and battle-tested agent harnesses (**Aider, Claude Code, Codex, OpenCode**) behind a zero-maintenance OpenAI-compatible gateway with **automatic credit protection and fallback**.

---

## ⚡ 1-Command Setup

### macOS (Apple Silicon / Intel) & Linux
```bash
curl -sSL https://raw.githubusercontent.com/dhurianiket/agent-workstation-setup/main/install.sh | bash
```

### Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/dhurianiket/agent-workstation-setup/main/install.ps1 | iex
```

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
 │  4. Closed-Loop Auto-Verification (syntax, tests, git diff)   │
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
