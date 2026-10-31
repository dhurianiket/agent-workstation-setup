# Antigravity Pro Workspace Guidelines & Auto-Orchestration

## 0. Zero-Touch First-Run Setup & Personal API Key Onboarding
- When a user clones or pulls this repository into Antigravity or another agent harness, `.agents/hooks.json` (`tools/pre_invocation_hook.py`) automatically triggers `python3 tools/setup_wizard.py --auto` on first run.
- If asked to set up the repository, run `python3 tools/setup_wizard.py --auto` (which automatically creates `.venv`, clones all 32 repositories in parallel, builds the Graphify AST graph, installs the global Antigravity plugin & MCP server, and launches the port 8000 gateway daemon).
- Then check `http://127.0.0.1:8000/v1/config/status` and ask the user for their personal API keys (NVIDIA NIM, AWS Bedrock/CLI, Gemini, OpenRouter, DeepSeek, Groq) or guide them to click **"🔑 API Keys & Cloud"** on `http://127.0.0.1:8000/dashboard`. Save personal keys strictly to local git-ignored `.env` (`0600`) and scan with `ggshield`.

## 1. Mandatory Step 1: Automatic Request Routing & Telemetry Banner
- Every user prompt in this chat is automatically analyzed by the `PreInvocation` hook (`tools/pre_invocation_hook.py`) and Zero-Name Skill Router (`tools/skill_router.py`).
- **Always start your response** with the 1-line routing telemetry banner so the user can see automatic routing in action:
  `> ⚡ **Auto-Router**: Tier = <tier> (<model>) | Auto Skill = <skill> | Activated Repos = <matched_repos> | Graphify AST = Synced`
- **Active Execution Mandate**: The banner is strictly functional, not decorative. Actively apply the auto-routed skill runbook and execute tasks with the resolved model (invoking the gateway on `http://127.0.0.1:8000/v1` or `orchestrate.py` whenever multi-model reasoning or generation is needed).
- Do not wait for manual activation phrases or repository names. Auto-triage, plan, execute with Principal Engineer standards (no placeholders, strict typing, defensive errors), and verify results via syntax checks/tests before completion.
- Leverage the Unified AI Gateway on port 8000 (`http://127.0.0.1:8000/v1`) with Smart 5-Tier credit guard.

## 2. Knowledge Graph & Agent Context (Graphify + AgentContext)
- **Graphify Knowledge Graph**: Located at `graphify-out/graph.json`, `graphify-out/graph.html`, and `graphify-out/GRAPH_REPORT.md`.
- **Query First**: Always run `graphify query "<question>"` or check `graphify-out/graph.json` before performing raw searches or wide reads across the codebase.
- **Auto-Sync (Isolated)**: After modifying or creating code files in a workspace where `graphify-out/graph.json` exists, run `python -m graphify update .` to ensure the AST knowledge graph is synchronized. Never create `graphify-out/` inside external personal/private repositories unless opted in.
- **Agent Context**: Refer to `AGENT_CONTEXT.md` and the agent framework context (`eko/packages/eko-core/src/agent/agent-context.ts` / `agentmemory`) for agent state lifecycle, tool execution chains, and cross-session memory.

## 3. Security & Personal Repo Isolation (GitGuardian Zero-Leakage)
- Strictly prevent credential leakage and personal repository name exposure. Never output secrets or commit them to Git.
- Pass all diffs through `ggshield secret scan` before git commit or push.
- Redact all tokens in chat and logs.
