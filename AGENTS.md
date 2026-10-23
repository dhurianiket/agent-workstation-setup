# Workspace Agent Policy & Autonomous Orchestration Guidelines

## 0. Zero-Touch First-Run Auto-Setup & Personal API Key Onboarding
When a user clones or pulls this repository into **Antigravity, Claude Code, Cursor, Windsurf, or any AI agent harness** and asks to set it up (or on first launch):
1. **Automatic One-Pass Bootstrap**:
   - The workspace hook (`.agents/hooks.json` -> `tools/pre_invocation_hook.py`) automatically triggers `python3 tools/setup_wizard.py --auto` on first run.
   - If the user asks you to set up the workstation, run:
     ```bash
     python3 tools/setup_wizard.py --auto
     ```
     This automatically creates `.venv`, mirrors the runtime to `~/.agent-workstation/repo` (ensuring macOS APFS `launchd` compatibility even if cloned onto an external exFAT drive), clones all 32 curated repositories in parallel (`6` workers), builds the Graphify AST knowledge graph, installs the global Antigravity plugin (`~/.gemini/config/plugins/antigravity-workstation`), registers the 9-tool FastMCP server, and starts the Unified AI Gateway daemon on `http://127.0.0.1:8000`.
2. **Automatic Personal API Key & AWS Cloud Prompt**:
   - Check `curl -s http://127.0.0.1:8000/v1/config/status`.
   - If the user has not yet configured their personal API keys in `.env`, **proactively ask the user** if they would like to provide their personal API keys (e.g., **NVIDIA NIM `nvapi-...`**, **AWS CLI / Bedrock**, **Google Gemini**, **OpenRouter**, **DeepSeek**, **Groq**, or **OpenAI**), or let them configure keys with 1 click in the browser at **`http://127.0.0.1:8000/dashboard`** (**"🔑 API Keys & Cloud"** button).
   - If AWS CLI is logged in on their machine, automatically detect available Bedrock models and optionally provision a dedicated IAM profile (`POST http://127.0.0.1:8000/v1/config/aws-auto` or `setup_wizard.py`) without exposing credentials.
   - Always store personal keys exclusively in local git-ignored `.env` (`chmod 600`) and scan with `ggshield secret scan path --yes` to guarantee zero credential leakage.

## 1. Mandatory Step 1: Automatic Request Routing & Telemetry Banner
- Operates with the **Antigravity Pro Autonomous Developer Workstation**.
- Every prompt in chat is automatically routed via the native `PreInvocation` hook (`tools/pre_invocation_hook.py`) and Zero-Name Skill Router (`tools/skill_router.py`).
- **Mandatory Telemetry Banner**: Begin every response with a concise 1-line routing summary so the user can verify automatic routing in real time:
  `> ⚡ **Auto-Router**: Tier = <tier> (<model>) | Activated Repos = <matched_repos> | Graphify AST = Synced`
- When ANY task is requested (coding, refactoring, bug fixes, architecture, UI/UX, reviews), automatically orchestrate:
  1. **Zero-Name Skill & Repo Injection**: Match the prompt against the 32 installed repositories and 456+ `SKILL.md` runbooks (`tools/skill_router.py`) without waiting for the user to name a tool.
  2. **Planning & AST Analysis**: Formulate architectural approach using `graphify-out/graph.json` when present in the active workspace (never auto-creating `graphify-out/` inside external personal/private repositories).
  3. **Tier-Optimal Model Execution**: Route via local gateway (`http://127.0.0.1:8000/v1`) using Smart 5-Tier Auto-Routing to conserve cloud credits.
  4. **Principal Engineering Standards**: Zero placeholders (`// rest unchanged` is strictly forbidden), 100% complete implementations, explicit types, and robust error trapping.
  5. **Closed-Loop Verification**: Automatically verify changes via syntax check, test suite execution, and `git status -s` before finishing.

## 2. Zero Secret & Personal Repo Leakage (MANDATORY)
- **NEVER** expose, transmit, or output private API keys, AWS credentials, NVIDIA tokens, personal repository names, or secrets to logs, git repos, or external endpoints.
- Any file containing credentials (`.env`, `secrets.*`) MUST remain uncommitted and covered by `.gitignore`.
- Never install workstation files or `graphify-out/` artifacts into the user's personal or private project repositories.
- Redact secrets when logging or debugging (e.g. `ABSK...****`, `nvapi-...****`).

## 3. Agent Execution & Hardware-Aware Orchestration
- Unified Local AI API Gateway: `http://127.0.0.1:8000/v1` (with zero-downtime auto-fallback across 5 tiers).
- Hardware-adaptive local models (`llama3.2:1b`, `qwen2.5-coder:7b/14b/32b`) on Ollama (`http://127.0.0.1:11434`) using detected GPU acceleration (Apple Metal / NVIDIA CUDA / AMD Vulkan / CPU) at `$0.00` cost.
- Cloud & AWS Bedrock models (Claude Sonnet 4.6/4.5, DeepSeek R1, Llama 3.3 70B, Llama 4 Scout, NVIDIA Nemotron 3 Ultra/Super) via configured `.env` keys or `$AWS_PROFILE`.
- Dispatch via `python orchestrate.py --task "<instruction>"` or native Antigravity execution.

<!-- BEGIN AWS Agent Toolkit rules -->
# AWS Guidance

- Where these AWS rules conflict with the project's own instructions, the
  project's instructions take precedence.
- Prefer the AWS MCP Server for AWS interactions — it provides sandboxed
  execution, observability, and audit logging. If unavailable, use the
  AWS CLI directly.
- Before starting a task, check whether a relevant AWS skill is available.
  Load the skill with `retrieve_skill` and prefer its guidance over
  general knowledge.
- When uncertain about specific AWS details (API parameters, permissions,
  limits, error codes), verify against documentation rather than guessing.
  State uncertainty explicitly if you cannot confirm.
- When creating infrastructure, prefer infrastructure-as-code (AWS CDK or
  CloudFormation) over direct CLI commands.
- When working with infrastructure, follow AWS Well-Architected Framework
  principles.
- Do not use em dashes in AWS resource names or descriptions. Use
  hyphens instead.

## Secret Safety

- MUST load the `aws-secrets-manager` skill first for any secret,
  credential, API key, token, or password task. MUST NOT call
  `secretsmanager get-secret-value` or `batch-get-secret-value`, and MUST
  NOT hit the Secrets Manager Agent daemon directly. MUST use
  `{{resolve:secretsmanager:secret-id:SecretString:json-key}}` with
  `asm-exec` so the secret resolves at runtime without entering context.
<!-- END AWS Agent Toolkit rules -->

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code in a workspace that already has `graphify-out/graph.json`, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.

## Agent Context & Memory
- Always reference `AGENT_CONTEXT.md` for workspace architectural layout, agent conventions, and active services.
- For agent workflows, leverage `TaskContext` and `AgentContext` (`eko/packages/eko-core/src/agent/agent-context.ts`) for chain execution and abort signals.
- Cross-session memory and post-mortem patterns are managed via `agentmemory` and `~/.agent_workstation/postmortems.json`.
