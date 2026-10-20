# Antigravity Autonomous AI Developer Workstation OS (v3.2)

[![Gateway Status](https://img.shields.io/badge/Gateway-Active%20(Port%208000)-10b981?style=for-the-badge&logo=fastapi)](http://127.0.0.1:8000/dashboard)
[![MCP Protocol](https://img.shields.io/badge/MCP-FastMCP%20Ready-38bdf8?style=for-the-badge&logo=anthropic)](https://github.com/dhurianiket/agent-workstation-setup)
[![Security](https://img.shields.io/badge/Security-GitGuardian%20ggshield%20Verified-purple?style=for-the-badge&logo=gitguardian)](https://gitguardian.com)
[![Routing](https://img.shields.io/badge/Smart%20Routing-5--Tier%20Credit%20Guard-f59e0b?style=for-the-badge)](https://github.com/dhurianiket/agent-workstation-setup)
[![Docker](https://img.shields.io/badge/Docker-Sandbox%20Ready-2496ed?style=for-the-badge&logo=docker)](https://github.com/dhurianiket/agent-workstation-setup)
[![License](https://img.shields.io/badge/License-MIT-gray?style=for-the-badge)](LICENSE)

> **Turn any Mac, Windows, or Linux machine into a private, cost-protected, autonomous AI engineering workstation with one command.**

The **Antigravity Autonomous Workstation** bridges frontier cloud reasoning (**Claude 4.5 Sonnet & Opus, DeepSeek R1, Llama 3.3 70B, Llama 4 Scout** via AWS Bedrock or direct BYOK keys), local discrete GPU acceleration (**Ollama on Apple Metal / AMD Radeon Vulkan / NVIDIA CUDA**), and battle-tested coding agent harnesses (**Aider, Claude Code, Codex, OpenCode**). All unified behind an OpenAI-compatible gateway with **Smart 5-Tier Auto-Routing, GitGuardian zero-leakage security gates, deterministic AST validation, and a real-time web telemetry dashboard**.

---

## 📑 Table of Contents

1. [⚡ 1-Command Universal Installers](#-1-command-universal-installers)
2. [🌐 Interactive Web & Telemetry Dashboard](#-interactive-web--telemetry-dashboard)
3. [🔌 Model Context Protocol (MCP) Server for Cursor & Claude Code](#-model-context-protocol-mcp-server)
4. [🔒 GitGuardian (`ggshield`) Zero-Leakage & AST Sensors](#-gitguardian-ggshield-zero-leakage--ast-sensors)
5. [🎛️ 5-Tier Smart Auto-Routing & Credit Guard](#️-5-tier-smart-auto-routing--credit-guard)
6. [🐳 Dockerized Sandbox Execution](#-dockerized-sandbox-execution)
7. [💻 Multi-Device Hardware Optimization Setup](#-multi-device-hardware-optimization-setup)
8. [🔑 Bring Your Own Key (BYOK) & Cloud Backends](#-bring-your-own-key-byok--cloud-backends)
9. [🧰 Master Curated Tools Ecosystem (32 of 32 Ready)](#-master-curated-tools-ecosystem)
10. [🚀 Antigravity Pro Always-On Orchestration Policy](#-antigravity-pro-always-on-orchestration-policy)
11. [📊 CLI Usage & Manual Orchestration](#-cli-usage--manual-orchestration)

---

## ⚡ 1-Command Universal Installers

### macOS (Apple Silicon M1/M2/M3/M4 & Intel) & Linux
```bash
curl -sSL https://raw.githubusercontent.com/dhurianiket/agent-workstation-setup/main/install.sh | bash
```

### Windows (PowerShell 7+ / Windows Terminal)
```powershell
irm https://raw.githubusercontent.com/dhurianiket/agent-workstation-setup/main/install.ps1 | iex
```

### Docker Sandbox (Isolated Multi-Platform Container)
```bash
git clone https://github.com/dhurianiket/agent-workstation-setup.git
cd agent-workstation-setup
cp .env.example .env
docker compose up -d
```

---

## 🌐 Interactive Web & Telemetry Dashboard

The workstation includes an embedded, high-performance web dashboard running natively at:
**`http://127.0.0.1:8000/dashboard`** (or `/status`)

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │ ⚡ Antigravity Workstation Control Plane          ONLINE • 16ms Latency │
 ├────────────────┬─────────────────┬─────────────────┬───────────────────┤
 │ Total Spend    │ Smart Savings   │ Total Tokens    │ Active Models     │
 │ $0.0410 USD    │ $0.2310 USD     │ 93,500          │ 21 Models Active  │
 ├────────────────┴─────────────────┴─────────────────┴───────────────────┤
 │ ⚡ 5-Tier Hierarchy: Local GPU ($0) ➔ Scout ➔ Coder ➔ Reasoner ➔ Claude│
 ├──────────────────────────────────┬─────────────────────────────────────┤
 │ 🧪 In-Browser Prompt Runner      │ 📊 Granular Model Spend Table       │
 │ [Select Tier: auto / coder / r1] │ • llama3.2:1b (GPU): 0.0000 USD     │
 │ [Enter Prompt & Run Live]        │ • llama-3.3-70b:     0.0120 USD     │
 │ [Streaming Output with Badges]   │ • deepseek-r1:       0.0290 USD     │
 └──────────────────────────────────┴─────────────────────────────────────┘
```

* **Live Latency & Health Pulse**: Continuous verification of AWS Bedrock, local GPU daemons, and BYOK providers.
* **Credit Spend & Savings Meter**: Tracks exact credit consumption and calculates real dollar savings compared to frontier model baselines.
* **Granular Usage Breakdown**: Token telemetry (input vs output) logged persistently in `~/.agent_workstation/usage_stats.json`.
* **In-Browser Playground**: Test any prompt against any model tier with sub-second feedback before dispatching heavy coding tasks.

---

## 🔌 Model Context Protocol (MCP) Server

Connect the workstation engine natively into **Cursor, Claude Code, Windsurf, or Google Antigravity** via the built-in FastMCP server (`agent_workstation_mcp.py`).

### 1. Configuration (`claude_desktop_config.json`, Cursor MCP, or Antigravity Settings)
```json
{
  "mcpServers": {
    "workstation": {
      "command": "python",
      "args": [
        "C:/Users/dhuri/Downloads/antigravity ai workspace/pc local work/agent-workstation-setup/agent_workstation_mcp.py"
      ]
    }
  }
}
```

### 2. Native MCP Tool Catalog
| Tool Name | Parameters | Purpose |
| :--- | :--- | :--- |
| **`workstation_health`** | None | Returns gateway online status, active providers, and server latency. |
| **`workstation_spend`** | None | Displays real-time request counts, token breakdown, and smart-tier USD savings. |
| **`workstation_orchestrate`** | `task`, `model` ("auto"), `agent` ("aider"), `judge` (bool) | Dispatches an autonomous task through 5-tier routing with AST sensors and post-action verification. |
| **`workstation_judge`** | None | Dispatches current git diff to DeepSeek R1 for Frontier Critic consensus review. |
| **`workstation_scan_secrets`** | `files` (optional list) | Runs GitGuardian (`ggshield`) across modified files with a 100% zero-leak guarantee. |
| **`workstation_list_tools`** | None | Audits and returns the operational status of all 32 curated developer tools. |

---

## 🔒 GitGuardian (`ggshield`) Zero-Leakage & AST Sensors

The workstation enforces a **Dual-Layer Deterministic Verification Gate** built directly into `orchestrate.py`:

```
                 [Agent Modifies Workspace Files]
                                │
                                ▼
      ┌───────────────────────────────────────────────────┐
      │        Deterministic Post-Action Sensors          │
      │                                                   │
      │  1. AST & Bytecode Syntax Gate:                   │
      │     • Python bytecode compilation (py_compile)    │
      │     • JSON schema & structure parsing             │
      │     • Node.js JavaScript/TypeScript syntax verify │
      │                                                   │
      │  2. Code Constitution AST Sensor:                 │
      │     • Blocks bare `except:` anti-patterns         │
      │     • Traps mutable default arguments (e.g. `[]`) │
      │     • Enforces 100% complete implementations      │
      │                                                   │
      │  3. GitGuardian (ggshield) Secret Shield:         │
      │     • Scans modified files for API keys & tokens  │
      │     • BLOCKS commits immediately if leaks found   │
      │                                                   │
      │  4. Frontier Critic Consensus (--judge):          │
      │     • Dispatches git diff to DeepSeek R1          │
      │     • Rejects logic flaws & docstring mismatches  │
      └─────────────────────────┬─────────────────────────┘
                                │
                                ▼
              [Verified & Clean Git Commit / Push]
```

* **Zero Secret Leakage Guarantee**: AWS access keys, OpenAI/OpenRouter tokens, private certificates, and passwords can never enter git history or external model contexts.
* **Persistent Post-Mortem Memory**: Failed runs, syntax errors, and edge-case exceptions are saved to `~/.agent_workstation/postmortems.json` and injected into future tasks so the orchestrator never repeats a past mistake.

---

## 🎛️ 5-Tier Smart Auto-Routing & Credit Guard

Frontier models are expensive. Routine tasks do not need a \$75/million token model. The orchestrator's smart auto-router (`--model auto` by default) dynamically delegates each prompt based on semantic intent:

```
                          [User Prompt / Task]
                                   │
       ┌───────────────────────────┼───────────────────────────┐
       ▼                           ▼                           ▼
[Docstring / Lint]        [Boilerplate / Test]        [Feature / Refactor]
       │                           │                           │
       ▼                           ▼                           ▼
 TIER 1: Local GPU         TIER 2: Fast Scout          TIER 3: Coder
  (Llama 3.2 1B)            (Llama 4 Scout)           (Llama 3.3 70B)
    $0.00 / 1M                $0.08 / 1M                 $0.72 / 1M
                                                               │
                                   ┌───────────────────────────┘
                                   ▼
                         [Reasoning / Critique]
                                   │
                                   ▼
                            TIER 4: Reasoner
                             (DeepSeek R1)
                               $1.35 / 1M
                                   │
                                   ▼
                         [System Architecture]
                                   │
                                   ▼
                            TIER 5: Frontier
                        (Claude Sonnet/Opus 4.5)
                              $3.00 / 1M
```

### Zero-Downtime Auto-Fallback Cascade
If a cloud provider hits rate limits or depletes credits, the gateway cascades instantly without crashing:
$$\text{Opus} \longrightarrow \text{Sonnet} \longrightarrow \text{DeepSeek R1} \longrightarrow \text{Llama 3.3 70B} \longrightarrow \text{Llama 4 Scout} \longrightarrow \text{Local GPU ($0.00)}$$

| Tier | Alias | Model Backend | Latency | Pricing / 1M Tokens | Best Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Local Free** | `local` | `llama3.2:1b` (Ollama GPU) | ~17ms | **$0.00** | Linting, docstrings, typos, 100% offline |
| **Tier 2: Fast Scout** | `fast` | `llama4-scout-17b` | ~190ms | **$0.08 in / $0.30 out** | Unit tests, boilerplate, HTML/CSS tweaks |
| **Tier 3: Production Coder** | `coder` | `llama3-3-70b-instruct` | ~300ms | **$0.72 in / $0.72 out** | Full-stack APIs, React components, bug fixes |
| **Tier 4: Deep Reasoner** | `reasoner` | `deepseek.r1-v1:0` | ~1.1s | **$1.35 in / $2.19 out** | Algorithmic logic, concurrency, critic review |
| **Tier 5: Frontier Flagship**| `claude` | `claude-sonnet-4-5` | ~2.0s | **$3.00 in / $15.00 out** | High-level system architecture, security |
| **Tier 5+: Frontier Opus** | `opus` | `claude-opus-4-5` | ~4.2s | **$15.00 in / $75.00 out**| Strategic multi-repository refactoring |

---

## 🐳 Dockerized Sandbox Execution

To run the entire developer workstation in a secure, sandboxed container without touching your host Python or Node environment:

```bash
# 1. Clone repository
git clone https://github.com/dhurianiket/agent-workstation-setup.git
cd agent-workstation-setup

# 2. Configure credentials safely
cp .env.example .env

# 3. Spin up the containerized gateway
docker compose up -d

# 4. Verify status
curl http://localhost:8000/health
# Open http://localhost:8000/dashboard in your browser
```

---

## 💻 Multi-Device Hardware Optimization Setup

### 1. Apple Silicon (MacBook Pro, iMac, Mac Studio M1/M2/M3/M4)
Apple Silicon chips feature unified memory shared between CPU and Metal GPU cores.
1. Install and start Ollama:
   ```bash
   brew install ollama
   ollama serve
   ```
2. Pull recommended local models:
   ```bash
   # Lightweight (8GB-16GB RAM):
   ollama pull llama3.2:1b

   # Heavyweight local coder (32GB-128GB Unified RAM on Mac Studio):
   ollama pull qwen2.5-coder:14b
   ollama pull qwen2.5-coder:32b
   ```

### 2. Windows PC with Discrete GPU
- **AMD Radeon Discrete GPU**: Ollama auto-detects Vulkan GPU offloading. Verified on AMD Radeon RX 5500M with ~17ms sub-second generation.
- **NVIDIA GeForce / RTX**: Ollama auto-detects CUDA cores.
- Set Windows power plan to **Ultimate Performance** to eliminate idle sleep throttling during long agent orchestrations.

### 3. Linux Servers & Workstations
Install system packages and start the background daemon:
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama run llama3.2:1b
```

---

## 🔑 Bring Your Own Key (BYOK) & Cloud Backends

The workstation operates seamlessly with your existing cloud accounts or API keys:

### Option A: AWS Bedrock (Claude 4.5, DeepSeek R1, Llama 3.3)
If you have AWS Startup credits, Activate credits, or an enterprise AWS account:
```bash
aws configure --profile my-profile
# Or using AWS IAM Identity Center SSO:
aws sso login --profile my-profile
```
In your `.env` file:
```env
AWS_PROFILE=my-profile
AWS_DEFAULT_REGION=us-east-1
```

### Option B: Direct BYOK Provider Keys (No AWS Needed)
Set any key in `.env`; the gateway auto-detects it with zero configuration changes:
```env
# Access Claude, DeepSeek, and Llama via OpenRouter with 1 key:
OPENROUTER_API_KEY=sk-or-v1-...

# Free / cloud inference via NVIDIA NIM:
NVIDIA_API_KEY=nvapi-...

# Direct Provider Keys:
DEEPSEEK_API_KEY=sk-...
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-proj-...
```

---

## 🧰 Master Curated Tools Ecosystem

All 32 curated AI developer tools, harnesses, and skills can be verified and managed in one command:
```bash
# Check audit status of all tools
python tools/manage_tools.py audit

# Synchronize and clone missing repositories (blobless single-branch clones)
python tools/manage_tools.py sync
```

### Curated Repositories Summary:

#### 1. Autonomous Harnesses & Memory
* **`9router`**: Connects coding agents to 40+ free AI providers with -40% RTK token compression.
* **`ruflo`**: Multi-agent swarm coordinator with adaptive memory and vector RAG.
* **`openclaude`**: Model-agnostic terminal coding agent harness.
* **`jcode`**: Memory-efficient Rust-powered coding agent.
* **`agent-reach`**: Live internet research across YouTube, GitHub, Reddit, and X.
* **`agentmemory`**: #1 benchmarked persistent memory layer for coding agents.
* **`hindsight`**: Cross-session post-mortem error prevention memory.
* **`OpenDots`**: Autonomous AI coworker framework.
* **`radiant`**: Shared conversation swarms for multi-agent threads.

#### 2. Media Automation & Video Generation
* **`auto-editor`**: Automatic dead-air and silence cutting for rough video cuts.
* **`open-higgsfield`**: Open-source AI video studio workspace.
* **`higgsfield-video`**: Programmatic video generation pipelines.
* **`LongCat-Video`**: Long-form video synthesis foundation model.
* **`bible-strong-avatar-lab`**: Avatar and character generation lab for video channels.

#### 3. UI/UX & Architecture Design
* **`graphify`**: Codebase AST knowledge graph without vector databases.
* **`archify`**: Interactive codebase architecture diagrams.
* **`ui-ux-pro-max-skill`**: Cross-platform design intelligence, typography, and palettes.
* **`emilkowalski-skills`**: Apple HIG physics-based motion and spring animations.
* **`dickwu-apple-design-skill`**: Dedicated Apple design standards reviewer.
* **`open-design`**: Local-first collaborative AI design system.
* **`pretext`**: Pure arithmetic DOM-less text measurement (10x faster canvas rendering).
* **`reimagine-it`**: Content-derived UI refactoring.
* **`hairline`**: Interactive pointer-reactive isometric line figures.

#### 4. Security, Research & Specialized Models
* **`strix`**: AI penetration testing discovering OWASP vulnerabilities with patch diffs.
* **`open-seo`**: Automated SEO audit and ranking optimization.
* **`rea`**: Agentic reverse engineering and binary decompilation.
* **`timesfm`**: Google Research foundation model for zero-shot time-series forecasting.
* **`scientific-agent-skills`**: 50+ specialized scientific, clinical, and data pipeline skills.
* **`OpenMAIC`**: Interactive AI-native classroom framework for LMS platforms.
* **`minimind`**: Framework for training tiny language models from scratch on consumer GPUs.
* **`RuView`**: Ambient WiFi spatial sensing and vital sign monitoring without cameras.
* **`gods-eye-view`**: Real-time 3D global data feed spatial telemetry tracker.
* **`go-modern-guidelines`**: Idiomatic conventions for modern Go engineering.

---

## 🚀 Antigravity Pro Always-On Orchestration Policy

When paired with your **Antigravity Pro subscription**, you **never** need to prompt `"orchestrate task X using aider"`. The workspace rules automatically trigger full autonomous orchestration:

1. **AST & Architecture Triage**: Maps dependencies before editing.
2. **Tier-Optimal Execution**: Routes to local GPU ($0) or fast models first to conserve AWS credits.
3. **Principal Engineer Standards**: Strict zero-placeholder policy (`// rest unchanged` is strictly forbidden). 100% complete, defensively typed implementations.
4. **Closed-Loop Verification**: Automatically verifies syntax (`py_compile`, Node check), test suites, and git status before declaring tasks complete.

---

## 📊 CLI Usage & Manual Orchestration

```bash
# Auto-tiering (Default: intelligent 5-tier routing based on task)
python orchestrate.py -t "Refactor the authentication flow with JWT refresh tokens"

# Target specific agent harnesses
python orchestrate.py -a aider -t "Fix null pointer in user profile component"
python orchestrate.py -a claude -t "Audit API security and rate limiting"

# Force specific model tier
python orchestrate.py -m fast -t "Generate unit tests for auth middleware"
python orchestrate.py -m reasoner -t "Debug race condition in WebSocket stream"

# Run with Frontier Critic consensus review
python orchestrate.py -t "Optimize database query batching" --judge

# Inspect token consumption and credit spend
python orchestrate.py --usage
```

---

## 📄 License
MIT License. Built for modern, high-speed, cost-protected autonomous software engineering.
