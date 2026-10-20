# Agent Architecture Context & Operating Manual (AGENT_CONTEXT.md)

This document provides the foundational, high-fidelity context for any AI coding agent (Antigravity, Cursor, Claude Code, Aider, Codex, OpenCode) operating in this developer workspace.

---

## 1. System Architecture & Gateway

* **Unified Local AI API Gateway**: `http://127.0.0.1:8000/v1`
  * OpenAI-compatible `/v1/chat/completions` (with SSE streaming) & `/v1/models`.
  * **Interactive Web Dashboard**: `http://127.0.0.1:8000/dashboard` (real-time telemetry, model latencies, token spend).
  * **Local GPU Daemon**: Ollama running `llama3.2:1b` on AMD Radeon RX 5500M discrete GPU via Vulkan (**$0.00 / free**).
  * **AWS Bedrock Integration**: Profile `msi-lappy`, Region `us-east-1` (Claude 4.5 Sonnet & Opus, DeepSeek R1, Llama 3.3 70B, Llama 4 Scout).
  * **Bring Your Own Keys (BYOK)**: Native fallback to OpenRouter, NVIDIA NIM, DeepSeek, Groq, and OpenAI.

---

## 2. Knowledge Graph Context (Graphify)

* **Location**: `graphify-out/` (`graph.json`, `graph.html`, `GRAPH_REPORT.md`).
* **Scale**: 2,351+ nodes, 4,358+ edges, 141 detected communities across the workspace.
* **Operating Protocol**:
  1. **Query Before Searching**: Before executing broad file greps or exploratory directory scans, always run:
     ```bash
     python -m graphify query "<your question or symbol>"
     ```
  2. **Trace Paths**: For understanding dependencies between modules:
     ```bash
     python -m graphify path "<SourceModule>" "<TargetModule>"
     ```
  3. **Auto-Synchronization**: After creating or refactoring code files, run:
     ```bash
     python -m graphify update .
     ```
     *(This is also automatically triggered by `orchestrate.py` post-execution sensors).*

---

## 3. Agent Lifecycle & Task Context (`eko`)

When orchestrating multi-step workflows or autonomous browser/desktop actions, leverage the core `AgentContext` and `TaskContext` models (`eko/packages/eko-core/src/agent/agent-context.ts`):

* **`TaskContext`**:
  * Tracks `chatId`, `taskId`, and `EkoConfig`.
  * Provides `checkAborted()` handling cancellation signals and pause/resume states (`pauseStatus`).
  * Manages `currentStepControllers` ensuring clean step interruptions.
* **`AgentContext`**:
  * Maintains per-agent variables, tool execution contexts, and multi-agent chains (`AgentChain`).
* **Persistent Memory**:
  * Cross-session learnings and bug prevention patterns are stored in `~/.agent_workstation/postmortems.json` and mirrored via `agentmemory`.

---

## 4. GitGuardian (`ggshield`) Zero-Leakage Policy

* **CRITICAL**: Never expose or commit private API keys, AWS credentials, NVIDIA tokens, or passwords to git, logs, or external models.
* All modified files must be verified with `ggshield secret scan path --yes <files>` before git commit.
* Sensitive files (`.env`, `secrets.*`, `*.pem`, `*.key`) are permanently ignored in `.gitignore`.

---

## 5. Master Curated Tools Index (32 Curated Tools)

All tools in `tools/` are verified and operational:
* **Harnesses**: `9router`, `ruflo`, `openclaude`, `jcode`, `agent-reach`, `agentmemory`, `hindsight`, `OpenDots`, `radiant`
* **Media & Video**: `auto-editor`, `open-higgsfield`, `higgsfield-video`, `LongCat-Video`, `bible-strong-avatar-lab`
* **UI/UX & Design**: `graphify`, `archify`, `ui-ux-pro-max-skill`, `emilkowalski-skills`, `dickwu-apple-design-skill`, `open-design`, `pretext`, `reimagine-it`, `hairline`
* **Security & Research**: `strix`, `open-seo`, `rea`, `timesfm`, `scientific-agent-skills`, `OpenMAIC`, `minimind`, `RuView`, `gods-eye-view`, `go-modern-guidelines`

Tool verification command:
```bash
python tools/manage_tools.py audit
```
