---
name: agent-orchestrator
description: Autonomous master controller for multi-agent workflows, frontier model routing, local GPU inference, and curated developer tooling. Activates automatically across any project.
---

# Agent Orchestrator & Autonomous Controller Skill

This skill establishes the AI agent as the primary autonomous controller for this developer workstation. You do not need the user to re-explain the setup, models, or service endpoints.

## 1. System Architecture & Endpoints

- **Unified Laptop AI API Server:** `http://127.0.0.1:8000`
  - Health check: `GET http://127.0.0.1:8000/health`
  - OpenAI-compatible completion: `POST http://127.0.0.1:8000/v1/chat/completions` (with SSE streaming)
  - Auto-starts silently on Windows boot via `StartAIStack.vbs`. If offline, auto-start via `start_laptop_api_silent.ps1`.
- **Local GPU Inference Engine:** `http://127.0.0.1:11434` (Ollama)
  - Runs on AMD Radeon RX 5500M Discrete GPU via Vulkan at 59 tokens/second (`llama3.2:1b`).
- **AWS Bedrock Integration:**
  - Active profile: `msi-lappy` (Region: `us-east-1`, Account ID: `523271873017`)
  - Funded by AWS Startup program credits.

## 2. Frontier Model Routing Strategy

Always select the optimal model based on the complexity and nature of the task:

| Model Alias | Target Engine | When to Use |
| :--- | :--- | :--- |
| **`claude`** / **`sonnet`** | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | **Default / SOTA Agentic Coding**: Repository-wide edits, feature implementation, refactoring, tool calls. |
| **`opus`** | `us.anthropic.claude-opus-4-5-20251101-v1:0` | **Complex Systems Architecture**: Deep analytical planning, algorithmic synthesis, security auditing. |
| **`reasoner`** | `us.deepseek.r1-v1:0` | **Mathematical Logic**: 671B MoE model with complete reasoning chain-of-thought traces. |
| **`coder`** | `us.meta.llama3-3-70b-instruct-v1:0` | **High-Throughput Fast Coding**: Meta 70B parameter coder (~300ms latency). |
| **`fast`** | `us.meta.llama4-scout-17b-instruct-v1:0` | **Inner Loops & Auto-Completions**: 17B parameter model (~190ms latency). |
| **`pixtral`** | `us.mistral.pixtral-large-2502-v1:0` | **Multimodal Vision**: Image inspection, UI mockups, diagrams. |
| **`local`** | `llama3.2:1b` (Ollama GPU) | **Offline / Zero-Cost Privacy**: Local on-device execution. |

## 3. Autonomous Execution & Agent Dispatch

When the user asks for a coding task, refactoring, or audit:
1. Formulate the technical implementation plan.
2. If delegating to an external harness, invoke `orchestrate.py`:
   ```bash
   python orchestrate.py --task "<instruction>" --agent [aider|claude|codex] --model [claude|opus|reasoner|coder]
   ```
3. Or dispatch via Aider pointing to the local gateway:
   ```bash
   aider --openai-api-base http://127.0.0.1:8000/v1 --openai-api-key dummy --model openai/claude --message "<instruction>" --yes-always
   ```

## 4. Curated Tooling & Skills Available

- **`graphify`**: Codebase AST knowledge graph generator (local parsing, no vector store).
- **`ui-ux-pro-max`**: Design intelligence, typography, spacing, palettes, responsive layouts.
- **`apple-design`**: Apple Human Interface Guidelines and UI physics.
- **`agent-reach`**: Web intelligence across Twitter, Reddit, YouTube, GitHub without API fees.
- **`agentmemory`**: Cross-session persistent memory for AI agents.
- **`strix`**: AI penetration testing and vulnerability auditing.
- **`9router`**: Free multi-provider failover router for coding agents.

## 5. Security & Zero Secret Leakage (MANDATORY)

- Never output or transmit API keys, AWS credentials, NVIDIA tokens, or secrets online or to git repositories.
- Keep `.env`, `secrets.*`, and credentials in `.gitignore`.
