---
name: agent-orchestrator
description: Autonomous master controller for multi-agent workflows, frontier model routing, local GPU inference, and 32 curated developer repositories. Activates automatically by default on every task without manual trigger.
---

# Agent Orchestrator & Autonomous Controller Skill (v3.4)

This skill establishes the AI agent as the primary autonomous controller for this developer workstation. It is **always active by default**. The user does not need to re-explain the setup, endpoints, or manually request orchestration or repository names.

## 1. Always-On Autonomous Orchestration & Zero-Name Skill Routing
- When the user gives ANY coding, refactoring, building, UI/UX, or debugging instruction:
  1. **Auto-Route & Inject Skills**: Match the prompt against the 32 curated repositories and 456+ `SKILL.md` runbooks via `tools/skill_router.py` and `tools/pre_invocation_hook.py`.
  2. **Triage & Plan**: Formulate the architectural plan using `graphify-out/graph.json` when present in the active workspace.
  3. **Execute**: Edit files using Principal Engineering standards (100% complete implementations, zero placeholders, strict types) or dispatch to an external harness (`aider`, `claude`, `codex`) via `python orchestrate.py`.
  4. **Auto-Verify**: Run syntax checks, tests, and `git status -s` to confirm zero regressions before declaring done.

## 2. System Architecture & Endpoints
- **Unified AI API Server:** `http://127.0.0.1:8000`
  - Health check: `GET http://127.0.0.1:8000/health`
  - Web Dashboard: `GET http://127.0.0.1:8000/dashboard`
  - Interactive Graphify AST Explorer: `GET http://127.0.0.1:8000/graphify`
  - Hardware Profile: `GET http://127.0.0.1:8000/v1/hardware`
  - OpenAI-compatible completion: `POST http://127.0.0.1:8000/v1/chat/completions` (supports `model="auto"`, SSE streaming, zero-downtime 5-tier fallback, and Principal Engineer quality directives)
- **Hardware-Adaptive Local GPU Engine:** `http://127.0.0.1:11434` (Ollama)
  - Automatically selects optimal local model (`llama3.2:1b`, `qwen2.5-coder:7b/14b/32b`) for the host PC/Mac GPU (Apple Metal, NVIDIA CUDA, AMD Vulkan, or CPU).
- **Cloud & AWS Bedrock Integration:**
  - Supports BYOK (`.env`: OpenRouter, NVIDIA NIM, DeepSeek, Groq, OpenAI) and optional AWS Bedrock (`$AWS_PROFILE`).

## 3. Smart 5-Tier Model Routing Matrix (`--model auto`)

| Tier | Alias | Primary Model | Best For | Est. Cost / 1M Toks |
| :--- | :--- | :--- | :--- | :--- |
| **Local (Free)** | `local` | `llama3.2:1b` / `qwen2.5-coder` (Ollama GPU) | Linting, formatting, comment cleanups, docstrings | **$0.00** |
| **Scout** | `fast` | `us.meta.llama4-scout-17b-instruct-v1:0` | Unit tests, boilerplate, configs, HTML/CSS | **~$0.08 in / $0.30 out** |
| **Workhorse** | `coder` | `us.meta.llama3-3-70b-instruct-v1:0` | Standard full-stack features, API endpoints, CRUD | **~$0.72 in / $0.72 out** |
| **Reasoning** | `reasoner` | `us.deepseek.r1-v1:0` | Complex algorithms, race conditions, memory leaks | **~$1.35 in / $2.19 out** |
| **Frontier** | `claude` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Systems architecture, security reviews, auth overhauls | **~$3.00 in / $15.00 out** |

## 4. Curated Tooling & Skills Available (32 Repositories)
- **`graphify` & `archify`**: Codebase AST knowledge graph generator and interactive architecture diagrams.
- **`ui-ux-pro-max`, `apple-design`, `emil-design-eng`, `reimagine-it`**: Design intelligence, Apple HIG, spring physics, and content-derived UI refactoring.
- **`agent-reach`, `agentmemory`, `hindsight`**: Web intelligence and cross-session persistent memory/post-mortems.
- **`strix` & `ggshield`**: AI penetration testing, vulnerability patching, and pre-commit secret scanning.

## 5. Security & Personal Repo Isolation (MANDATORY)
- Never output or transmit API keys, AWS credentials, NVIDIA tokens, or secrets online or to git repositories.
- Never install workstation files or `graphify-out/` artifacts into external personal or private repositories.
- Keep `.env`, `secrets.*`, and credentials in `.gitignore`.
