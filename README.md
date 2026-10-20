# Agent Workstation OS

> Turn any Mac, Windows, or Linux machine into an autonomous, multi-agent AI development powerhouse with one command.

Brings together frontier cloud models (**Claude 4.5 Sonnet/Opus, DeepSeek R1, Llama 3.3 70B** via AWS Startup credits), local discrete GPU inference (**Ollama on AMD/NVIDIA/Metal**), and battle-tested agent harnesses (**Aider, Claude Code, Codex, OpenCode**) behind a single, zero-maintenance OpenAI-compatible gateway.

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

## 🧠 What It Is & How It Works

Instead of juggling separate API keys, port configurations, and model quotas across different tools, this system unifies everything into a local autonomous pipeline:

```
                  ┌─────────────────────────────────────────┐
                  │          Your Prompt / Task             │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │       Antigravity / Orchestrator        │
                  │   (Selects agent harness & strategy)    │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │      Local AI Gateway (:8000)           │
                  │   (OpenAI-compatible + SSE streaming)   │
                  └────────────┬───────────────┬────────────┘
                               │               │
            ┌──────────────────┘               └──────────────────┐
            ▼                                                     ▼
┌───────────────────────────────┐               ┌───────────────────────────────────┐
│       AWS Bedrock Models      │               │          Local GPU Engine         │
│  (Funded by Startup Credits)  │               │      (AMD / NVIDIA / Metal)       │
│                               │               │                                   │
│ • Claude Sonnet 4.5  (Coding) │               │ • Llama 3.2 1B (59 tokens/sec)    │
│ • Claude Opus 4.5    (Arch)   │               │ • Fully offline, zero API cost    │
│ • DeepSeek R1 671B   (Math)   │               └───────────────────────────────────┘
│ • Llama 3.3 70B      (Fast)   │
└───────────────────────────────┘
```

### Real-World Example
1. **You ask**: *"Refactor the authentication handler to use OAuth2 PKCE and write unit tests."*
2. **The Orchestrator**: Automatically selects **Aider** paired with **Claude Sonnet 4.5**.
3. **The Gateway**: Directs the request through `http://127.0.0.1:8000/v1` authenticated by your AWS Startup credits with live SSE streaming.
4. **Execution**: The agent indexes your repository AST, performs the refactoring, executes the test suite, and commits clean Git diffs.
5. **Result**: Completed in seconds. No API keys exposed, zero manual environment configuration.

---

## 🛡️ The Zero-Friction Guarantee

**You never have to configure or explain this setup again.**

* **No Manual Server Starts**: Boots invisibly in the background on system login (`launchd` on macOS, silent VBScript on Windows).
* **Self-Healing Guard**: If the gateway is ever offline, the orchestrator detects it and brings it up in 2 seconds.
* **Global Agent Skill**: Pre-configured global skill (`agent-orchestrator`) teaches Antigravity, Claude Code, and Codex how to route and build across every workspace automatically.

---

## 🎛️ Model Routing Matrix

| Alias | Engine / Real Model ID | Best For | Latency |
| :--- | :--- | :--- | :--- |
| **`claude`** | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | **Default / SOTA Coding**: Multi-file repository edits & tools | ~2.0s |
| **`opus`** | `us.anthropic.claude-opus-4-5-20251101-v1:0` | **Systems Architecture**: Deep analytical planning & security | ~2.0s |
| **`reasoner`** | `us.deepseek.r1-v1:0` | **Logic & Math**: 671B MoE with full reasoning chains | ~1.1s |
| **`coder`** | `us.meta.llama3-3-70b-instruct-v1:0` | **Rapid Iterations**: High-throughput 70B parameter coding | ~300ms |
| **`fast`** | `us.meta.llama4-scout-17b-instruct-v1:0` | **Inner Loops**: Sub-200ms completions and summaries | ~190ms |
| **`local`** | `llama3.2:1b` (Ollama GPU) | **Offline / Privacy**: Free, zero-API local execution | ~17ms |

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

## 💻 CLI Quick Commands

```bash
# Run task using Claude Sonnet 4.5
python orchestrate.py --task "Add healthcheck endpoint" --agent aider --model claude

# Run complex architecture using Claude Opus 4.5
python orchestrate.py --task "Design distributed caching system" --agent aider --model opus

# Use local GPU offline model
python orchestrate.py --task "Scan project dependencies" --agent codex --model local

# Check full system & agent health
powershell -ExecutionPolicy Bypass -File .\ai_agent_status.ps1
```
