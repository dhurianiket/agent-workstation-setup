---
name: agent-orchestrator
description: Autonomous master controller for multi-agent workflows, frontier model routing, local GPU inference, and curated developer tooling. Activates automatically by default on every task without manual trigger.
---

# Agent Orchestrator & Autonomous Controller Skill (v2.0)

This skill establishes the AI agent as the primary autonomous controller for this developer workstation. It is **always active by default**. The user does not need to re-explain the setup, endpoints, or manually request orchestration.

## 1. Always-On Autonomous Orchestration
- When the user gives ANY coding, refactoring, building, or debugging instruction:
  1. **Triage & Plan**: Formulate the architectural plan.
  2. **Execute**: Either edit files directly using Principal Engineering standards (100% complete implementations, zero placeholders, strict types) or proactively dispatch to an external harness (`aider`, `claude`, `codex`) via `python orchestrate.py`.
  3. **Auto-Verify**: Run syntax checks, tests, and `git status -s` to confirm zero regressions before declaring done.

## 2. System Architecture & Endpoints
- **Unified Laptop AI API Server:** `http://127.0.0.1:8000`
  - Health check: `GET http://127.0.0.1:8000/health`
  - Usage tracker: `GET http://127.0.0.1:8000/v1/usage`
  - OpenAI-compatible completion: `POST http://127.0.0.1:8000/v1/chat/completions` (with SSE streaming, zero-downtime auto-fallback, and Principal Engineer quality directives)
  - Auto-starts silently on boot via `StartAIStack.vbs`. If offline, auto-starts via `start_laptop_api_silent.ps1`.
- **Local GPU Inference Engine:** `http://127.0.0.1:11434` (Ollama)
  - Runs on AMD Radeon RX 5500M Discrete GPU via Vulkan at 59 tokens/second (`llama3.2:1b`).
- **AWS Bedrock Integration:**
  - Active profile: `msi-lappy` (Region: `us-east-1`, Account ID: `523271873017`)
  - Funded by AWS Startup program credits.

## 3. Smart 5-Tier Model Routing Matrix (`--model auto`)

| Tier | Alias | Real Model ID | Best For | Latency | Est. Cost / 1M Toks |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Local (Free)** | `local` | `llama3.2:1b` (Ollama GPU) | Linting, formatting, comment cleanups, docstrings | ~17ms | **$0.00** |
| **Scout** | `fast` | `us.meta.llama4-scout-17b-instruct-v1:0` | Unit tests, boilerplate, configs, HTML/CSS | ~190ms | **~$0.08 in / $0.30 out** |
| **Workhorse** | `coder` | `us.meta.llama3-3-70b-instruct-v1:0` | Standard full-stack features, API endpoints, CRUD | ~300ms | **~$0.72 in / $0.72 out** |
| **Reasoning** | `reasoner` | `us.deepseek.r1-v1:0` | Complex algorithms, race conditions, memory leaks | ~1.1s | **~$1.35 in / $2.19 out** |
| **Frontier** | `claude` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Systems architecture, security reviews, auth overhauls | ~2.0s | **~$3.00 in / $15.00 out** |

## 4. Curated Tooling & Skills Available
- **`graphify`**: Codebase AST knowledge graph generator (local parsing, no vector store).
- **`ui-ux-pro-max`**: Design intelligence, typography, spacing, palettes, responsive layouts.
- **`apple-design`**: Apple Human Interface Guidelines and UI physics.
- **`agent-reach`**: Web intelligence across Twitter, Reddit, YouTube, GitHub without API fees.
- **`agentmemory`**: Cross-session persistent memory for AI agents.
- **`strix`**: AI penetration testing and vulnerability auditing.
- **`auto-editor`**: Programmatic silence removal for video/audio.
- **`9router`**: Free multi-provider failover router for coding agents.

## 5. Security & Zero Secret Leakage (MANDATORY)
- Never output or transmit API keys, AWS credentials, NVIDIA tokens, or secrets online or to git repositories.
- Keep `.env`, `secrets.*`, and credentials in `.gitignore`.
