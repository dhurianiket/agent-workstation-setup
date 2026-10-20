# Agent Architecture Context & Operating Manual (AGENT_CONTEXT.md)

This document provides the foundational, high-fidelity context for any AI coding agent (Antigravity, Cursor, Claude Code, Aider, Codex, OpenCode) operating in this developer workspace.

---

## 1. System Architecture & Gateway

* **Unified Local AI API Gateway**: `http://127.0.0.1:8000/v1`
  * OpenAI-compatible `/v1/chat/completions` (with `model="auto"` and SSE streaming) & `/v1/models`.
  * **Interactive Web Dashboard**: `http://127.0.0.1:8000/dashboard` (real-time telemetry, model latencies, token spend, 1-click Graphify AST viewer).
  * **Interactive Graphify AST Viewer**: `http://127.0.0.1:8000/graphify` & `/graphify/report`.
  * **Hardware-Adaptive Local GPU Daemon**: Ollama (`http://127.0.0.1:11434`) running hardware-matched models (`llama3.2:1b`, `qwen2.5-coder:7b/14b/32b`) on Apple Metal, NVIDIA CUDA, or AMD Vulkan (**$0.00 / free**).
  * **Bring Your Own Keys (BYOK) & AWS Bedrock**: Native 5-tier fallback across OpenRouter, NVIDIA NIM, DeepSeek, Groq, OpenAI, and optional AWS Bedrock (`$AWS_PROFILE`).

---

## 2. Knowledge Graph Context (Graphify)

* **Location**: `graphify-out/` (`graph.json`, `graph.html`, `GRAPH_REPORT.md`).
* **Scale**: 2,351+ nodes, 4,358+ edges, 141 detected communities across the workstation repository.
* **Isolation Policy**: `graphify-out/` is only queried or updated in workspaces where `graphify-out/graph.json` already exists. The workstation never auto-creates `graphify-out/` inside external personal or private repositories.
* **Operating Protocol**:
  1. **Query Before Searching**: Before executing broad file greps or exploratory directory scans, always run:
     ```bash
     python -m graphify query "<your question or symbol>"
     ```
  2. **Trace Paths**: For understanding dependencies between modules:
     ```bash
     python -m graphify path "<SourceModule>" "<TargetModule>"
     ```
  3. **Auto-Synchronization**: After creating or refactoring code files in a Graphify-enabled workspace, run:
     ```bash
     python -m graphify update .
     ```

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

* **CRITICAL**: Never expose or commit private API keys, AWS credentials, NVIDIA tokens, personal repository names, or passwords to git, logs, or external models.
* All modified files must be verified with `ggshield secret scan path --yes <files>` before git commit.
* Sensitive files (`.env`, `secrets.*`, `*.pem`, `*.key`) are permanently ignored in `.gitignore`.

---

## 5. Master Curated Tools Index (32 Curated Tools & 456+ Skills)

All 32 repositories in `tools/` are automatically cloned and indexed by `python tools/setup_wizard.py`:
* **Harnesses**: `9router`, `ruflo`, `openclaude`, `jcode`, `agent-reach`, `agentmemory`, `hindsight`, `OpenDots`, `radiant`
* **Media & Video**: `auto-editor`, `open-higgsfield`, `higgsfield-video`, `LongCat-Video`, `bible-strong-avatar-lab`
* **UI/UX & Design**: `graphify`, `archify`, `ui-ux-pro-max-skill`, `emilkowalski-skills`, `dickwu-apple-design-skill`, `open-design`, `pretext`, `reimagine-it`, `hairline`
* **Security & Research**: `strix`, `open-seo`, `rea`, `timesfm`, `scientific-agent-skills`, `OpenMAIC`, `minimind`, `RuView`, `gods-eye-view`, `go-modern-guidelines`

Tool verification & zero-name skill router commands:
```bash
python tools/manage_tools.py audit
python tools/skill_router.py "<any task description>"
```
