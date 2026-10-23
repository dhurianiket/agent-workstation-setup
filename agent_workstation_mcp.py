#!/usr/bin/env python3
"""
agent_workstation_mcp.py
Antigravity Autonomous Developer Workstation - Model Context Protocol (MCP) Server.

Exposes native tools for Cursor, Windsurf, Claude Code, and Antigravity:
  - workstation_health: Gateway health, active models, latency.
  - workstation_spend: Real-time token metrics and USD budget guardrails.
  - workstation_orchestrate: Autonomous 5-tier task execution with AST sensors.
  - workstation_judge: Frontier critic consensus review on git diffs.
  - workstation_scan_secrets: GitGuardian (ggshield) zero-leakage secret audit.
  - workstation_list_tools: Inspection and status of all curated tools.
"""

import os
import sys
import json
import shutil
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, List

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    try:
        from mcp.server.mcpserver import MCPServer as FastMCP
    except ImportError:
        print("Error: 'mcp' package is required. Install via 'pip install \"mcp<2\"'", file=sys.stderr)
        sys.exit(1)

# Initialize FastMCP Server
mcp = FastMCP("Autonomous-Agent-Workstation")

WORKSPACE_DIR = Path(__file__).parent.resolve()
TOOLS_DIR = WORKSPACE_DIR / "tools"
ORCHESTRATE_PY = WORKSPACE_DIR / "orchestrate.py"
STATS_FILE = Path.home() / ".agent_workstation" / "usage_stats.json"

_EXTRA_PATH = os.pathsep.join([
    str(Path.home() / ".local" / "bin"),
    str(Path.home() / "bin"),
    "/opt/homebrew/bin",
    "/usr/local/bin",
])
if str(Path.home() / ".local" / "bin") not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{_EXTRA_PATH}{os.pathsep}{os.environ.get('PATH', '')}"

@mcp.tool()
async def workstation_health() -> str:
    """Check gateway health, active providers (AWS Bedrock, Ollama GPU, BYOK), and latency."""
    import urllib.request
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/health")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return json.dumps(data, indent=2)
    except Exception as e:
        return f"Local Gateway Offline or Unreachable (http://127.0.0.1:8000): {e}"

@mcp.tool()
async def workstation_spend() -> str:
    """Return real-time token spend, requests count, and free local compute savings."""
    if not STATS_FILE.exists():
        return "No usage statistics recorded yet (~/.agent_workstation/usage_stats.json)."
    try:
        data = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        totals = data.get("totals", {})
        by_model = data.get("by_model", {})
        total_spent = totals.get("estimated_usd", data.get("total_cost_usd", 0.0))
        reqs = totals.get("requests", data.get("total_requests", 0))
        prompt_t = totals.get("prompt_tokens", data.get("total_prompt_tokens", 0))
        compl_t = totals.get("completion_tokens", data.get("total_completion_tokens", 0))
        
        # Estimate savings: if all tokens ran on Claude Opus ($15/$75 per M) vs what was actually spent
        opus_equiv = (prompt_t / 1e6 * 15.0) + (compl_t / 1e6 * 75.0)
        saved = max(0.0, opus_equiv - total_spent)

        output = [
            "=== WORKSTATION SPEND & CREDIT GUARD ===",
            f"Total Requests:       {reqs}",
            f"Prompt Tokens:        {prompt_t:,}",
            f"Completion Tokens:    {compl_t:,}",
            f"Total Cost (USD):     ${total_spent:.4f}",
            f"Frontier Cost Equiv:  ${opus_equiv:.4f}",
            f"Smart-Tier Savings:   ${saved:.4f} USD saved",
            "----------------------------------------"
        ]
        for m_id, m_stat in by_model.items():
            m_reqs = m_stat.get("requests", 0)
            m_toks = m_stat.get("prompt_tokens", 0) + m_stat.get("completion_tokens", 0)
            m_usd = m_stat.get("estimated_usd", 0.0)
            output.append(f"  {m_id:<34} | {m_reqs:>3} reqs | {m_toks:>7,} toks | ${m_usd:.4f}")
        output.append("========================================")
        return "\n".join(output)
    except Exception as e:
        return f"Error reading stats: {e}"

@mcp.tool()
async def workstation_orchestrate(task: str, model: str = "auto", agent: str = "aider", judge: bool = False) -> str:
    """
    Execute a development task using the Autonomous Workstation Orchestrator.
    Auto-routes through 5 model tiers, enforces AST Code Constitution, runs bytecode
    sensors, and optionally runs Frontier Critic consensus review.
    """
    cmd = [sys.executable, str(ORCHESTRATE_PY), "--task", task, "--model", model, "--agent", agent]
    if judge:
        cmd.append("--judge")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(WORKSPACE_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    stdout, stderr = await proc.communicate()
    out_str = stdout.decode("utf-8", errors="replace")
    err_str = stderr.decode("utf-8", errors="replace")
    
    if proc.returncode != 0:
        return f"[ORCHESTRATION FAILED (code {proc.returncode})]\n{err_str}\n{out_str}"
    return f"[ORCHESTRATION SUCCESS]\n{out_str}"

@mcp.tool()
async def workstation_judge() -> str:
    """Run Frontier Critic consensus review + AST Constitution + ggshield audit on current git diff without modifying files."""
    cmd = [sys.executable, str(ORCHESTRATE_PY), "--judge-only"]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(WORKSPACE_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    stdout, stderr = await proc.communicate()
    out_str = stdout.decode("utf-8", errors="replace")
    err_str = stderr.decode("utf-8", errors="replace")
    return out_str if out_str.strip() else err_str

@mcp.tool()
async def workstation_scan_secrets(files: Optional[List[str]] = None) -> str:
    """Run GitGuardian (ggshield) secret scanner to ensure zero credential or API key leakage."""
    if not shutil.which("ggshield"):
        return "Warning: ggshield is not installed or not in PATH."

    target_files = files
    if not target_files:
        # Detect modified files from git status
        try:
            res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=str(WORKSPACE_DIR))
            target_files = [line[3:].strip() for line in res.stdout.splitlines() if line.strip() and not line[3:].strip().endswith(".log")]
        except Exception:
            target_files = []

    if not target_files:
        return "No modified files detected to scan. Workspace clean."

    # Filter out large venv or git directories
    scan_list = [f for f in target_files if not any(ign in f for ign in [".venv", "node_modules", ".git"])]
    if not scan_list:
        return "No non-ignored files to scan."

    cmd = ["ggshield", "secret", "scan", "path", "--yes"] + scan_list
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(WORKSPACE_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode("utf-8", errors="replace")
    
    if proc.returncode == 0:
        return f"[PASSED] Zero secrets detected across {len(scan_list)} file(s).\n{out}"
    else:
        return f"[FAILED - SECRETS DETECTED]\n{out}\n{stderr.decode('utf-8', errors='replace')}"

@mcp.tool()
async def workstation_sync_graph() -> str:
    """Synchronize the Graphify AST knowledge graph across the codebase (graphify update .)."""
    cmd = [sys.executable, "-m", "graphify", "update", "."]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(WORKSPACE_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode("utf-8", errors="replace")
    if proc.returncode == 0:
        return f"[GRAPHIFY SYNC SUCCESS]\n{out}"
    return f"[GRAPHIFY SYNC ERROR]\n{stderr.decode('utf-8', errors='replace')}\n{out}"

@mcp.tool()
async def workstation_query_graph(query: str) -> str:
    """Query the Graphify AST knowledge graph to trace symbols, relationships, and call flow."""
    cmd = [sys.executable, "-m", "graphify", "query", query]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(WORKSPACE_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode("utf-8", errors="replace")
    err = stderr.decode("utf-8", errors="replace")
    return out if out.strip() else err

@mcp.tool()
async def workstation_list_tools() -> str:
    """List all curated developer tools, harnesses, and frameworks available in the workstation."""
    manage_py = TOOLS_DIR / "manage_tools.py"
    if not manage_py.exists():
        return "manage_tools.py not found in tools/."

    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(manage_py), "audit",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode("utf-8", errors="replace")

@mcp.tool()
async def workstation_auto_route_skills(prompt: str) -> str:
    """
    Automatically match any natural-language user prompt (from any project on the laptop)
    against the 32 installed repositories and 456+ indexed SKILL.md files without needing
    to know the repository or skill names.
    """
    router_py = TOOLS_DIR / "skill_router.py"
    if not router_py.exists():
        return "skill_router.py not found in tools/."
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(router_py), prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode("utf-8", errors="replace")
    return out if out.strip() else stderr.decode("utf-8", errors="replace")

if __name__ == "__main__":
    mcp.run()
