#!/usr/bin/env python3
"""
tools/pre_invocation_hook.py
Antigravity Native Lifecycle Hook (`SessionStart` and `PreInvocation`).

Automatically runs in ANY active Antigravity workspace across the entire machine:
1. Universal Workspace Auto-Activation: Detects the active workspace from `workspacePaths`
   (e.g., Aegis-health-ai-, CHATE PREP PLUS, aniket-living-cv, pc local work) and ensures
   it is activated with workstation rules and hooks.
2. Auto-Fetch Guard: Automatically verifies all 41 curated repositories and triggers background
   fetch/clone if any are missing or out of date.
3. 5-Tier Smart Model Classifier & Zero-Name 41-Repo Skill Router:
   Resolves the optimal model (NVIDIA NIM $0 developer models, Bedrock Claude, Gemini, DeepSeek, Ollama)
   and auto-injects matching skill runbooks directly into model context.
4. Mandatory Telemetry Banner: Enforces the exact 1-line routing status banner:
   `> ⚡ **Auto-Router**: Workspace = <workspace_name> | Tier = <tier> (<model>) | Auto Skill = <skill> | Activated Repos = <repos> | Graphify AST = Synced`
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
STATE_DIR = Path.home() / ".agent_workstation"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LAST_ROUTE_FILE = STATE_DIR / "last_route.json"
LAST_FETCH_LOCK = STATE_DIR / "last_fetch.lock"


def activate_target_workspace(ws_path: Path) -> bool:
    """Ensures any opened workspace folder is fully activated with workstation hooks & rules."""
    if not ws_path.exists() or not ws_path.is_dir():
        return False
    try:
        agents_dir = ws_path / ".agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        rules_dir = agents_dir / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        py_exe = sys.executable
        hook_py = str((TOOLS_DIR / "pre_invocation_hook.py").resolve())

        # 1. Write workspace .agents/hooks.json
        hooks_file = agents_dir / "hooks.json"
        hooks_payload = {
            "workstation-auto-router": {
                "enabled": True,
                "SessionStart": [
                    {
                        "type": "command",
                        "command": f'"{py_exe}" "{hook_py}" --session-start',
                        "timeout": 15
                    }
                ],
                "PreInvocation": [
                    {
                        "type": "command",
                        "command": f'"{py_exe}" "{hook_py}"',
                        "timeout": 15
                    }
                ]
            }
        }
        hooks_file.write_text(json.dumps(hooks_payload, indent=2), encoding="utf-8")

        # 2. Write workspace .agents/rules/workstation.md
        rules_file = rules_dir / "workstation.md"
        if not rules_file.exists():
            rules_content = f"""# Workstation Autonomous Operating Guidelines

This project is actively managed by the **Antigravity Pro Autonomous Developer Workstation**.

## 1. Mandatory Step 0: Automatic Request Routing & Telemetry Banner
- Every user prompt is automatically routed by `tools/pre_invocation_hook.py` and the Zero-Name Skill Router.
- **Mandatory Telemetry Banner**: Start every response with this exact 1-line summary:
  `> ⚡ **Auto-Router**: Workspace = {ws_path.name} | Tier = <tier> (<model>) | Auto Skill = <skill> | Activated Repos = <repos> | Graphify AST = Synced`
- **Active Execution Mandate**: Actively follow the resolved skill runbooks and dispatch code synthesis through the Unified Gateway (`http://127.0.0.1:8000/v1`).

## 2. Zero Secret Leakage & Verification
- Never expose API keys or personal credentials in chat or git.
- Pass code through `ggshield secret scan` before git commit or push.
"""
            rules_file.write_text(rules_content, encoding="utf-8")
        return True
    except Exception:
        return False


def ensure_background_repositories_fetched() -> None:
    """Automatically triggers background fetch/clone of repositories if missing or overdue."""
    manage_py = TOOLS_DIR / "manage_tools.py"
    if not manage_py.exists():
        return

    # Check if any curated repos are missing
    try:
        if str(TOOLS_DIR) not in sys.path:
            sys.path.insert(0, str(TOOLS_DIR))
        from manage_tools import CURATED_REPOS
        has_missing = any(not (TOOLS_DIR / name).exists() for name, _ in CURATED_REPOS)
    except Exception:
        has_missing = False

    overdue = True
    if LAST_FETCH_LOCK.exists():
        try:
            if time.time() - LAST_FETCH_LOCK.stat().st_mtime < 3600:  # 1 hour
                overdue = False
        except Exception:
            pass

    if has_missing or overdue:
        try:
            LAST_FETCH_LOCK.write_text(str(int(time.time())), encoding="utf-8")
            log_path = STATE_DIR / "auto_fetch.log"
            with open(log_path, "a", encoding="utf-8") as lf:
                cmd = [sys.executable, str(manage_py), "sync" if has_missing else "fetch"]
                subprocess.Popen(
                    cmd,
                    cwd=str(REPO_ROOT),
                    stdout=lf,
                    stderr=lf,
                    start_new_session=True,
                )
        except Exception:
            pass


def check_credentials_configured() -> bool:
    """Returns True if at least one cloud credential or AWS profile is configured in local .env."""
    candidates = [
        REPO_ROOT / ".env",
        Path.home() / ".agent-workstation" / "repo" / ".env",
    ]
    key_prefixes = (
        "NVIDIA_API_KEY=",
        "AWS_PROFILE=",
        "AWS_BEARER_TOKEN_BEDROCK=",
        "GEMINI_API_KEY=",
        "DEEPSEEK_API_KEY=",
        "OPENROUTER_API_KEY=",
        "GROQ_API_KEY=",
    )
    for env_path in candidates:
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    for pref in key_prefixes:
                        if s.startswith(pref) and len(s.split("=", 1)[1].strip()) > 2:
                            return True
            except Exception:
                pass
    return False


def resolve_transcript_file(payload: dict) -> Path:
    """Resolves the active transcript.jsonl path from hook payload or most recent brain session."""
    tp_str = payload.get("transcriptPath", "")
    if tp_str and Path(tp_str).exists():
        return Path(tp_str)
    conv_id = payload.get("conversationId", "")
    brain_root = Path.home() / ".gemini" / "antigravity" / "brain"
    if conv_id:
        candidate = brain_root / conv_id / ".system_generated" / "logs" / "transcript.jsonl"
        if candidate.exists():
            return candidate
    return Path("")


def extract_latest_user_prompt(tp: Path) -> str:
    """Reads the tail of transcript.jsonl to extract the most recent USER_INPUT content."""
    if not tp or not tp.exists() or not tp.is_file():
        return ""
    try:
        file_size = tp.stat().st_size
        with open(tp, "rb") as f:
            if file_size > 262144:
                f.seek(file_size - 262144)
            raw_lines = f.read().decode("utf-8", errors="replace").splitlines()
        for line in reversed(raw_lines):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
                if obj.get("type") == "USER_INPUT" or obj.get("source") == "USER_EXPLICIT":
                    content = obj.get("content", "")
                    if isinstance(content, str) and content.strip():
                        cleaned = content
                        if "<USER_REQUEST>" in cleaned:
                            cleaned = cleaned.split("<USER_REQUEST>", 1)[1].split("</USER_REQUEST>", 1)[0]
                        return cleaned.strip()
            except Exception:
                continue
    except Exception:
        pass
    return ""


def handle_session_start(payload: dict) -> None:
    """Handles Antigravity SessionStart lifecycle event."""
    ws_paths = payload.get("workspacePaths", [])
    active_ws = Path(ws_paths[0]) if ws_paths else REPO_ROOT
    active_ws_name = active_ws.name

    activate_target_workspace(active_ws)
    ensure_background_repositories_fetched()

    notice = (
        f"[ANTIGRAVITY WORKSTATION ACTIVATED]\n"
        f"• Active Project Workspace: {active_ws_name} ({active_ws})\n"
        f"• Workstation AI Gateway  : http://127.0.0.1:8000/v1 (5-Tier Smart Fallback)\n"
        f"• 41 Curated Repositories : Synced & auto-updating in background\n"
        f"• 100+ Production Skills  : Active globally across all projects\n"
        f"• Automatic Routing Policy: Every user turn is auto-classified with mandatory telemetry banner."
    )
    output = {
        "injectSteps": [
            {
                "systemMessage": {
                    "systemMessage": notice
                }
            }
        ]
    }
    print(json.dumps(output))


def handle_pre_invocation(payload: dict) -> None:
    """Handles Antigravity PreInvocation lifecycle event on every chat turn."""
    ws_paths = payload.get("workspacePaths", [])
    active_ws = Path(ws_paths[0]) if ws_paths else REPO_ROOT
    active_ws_name = active_ws.name

    # Auto-activate workspace if needed
    activate_target_workspace(active_ws)
    ensure_background_repositories_fetched()

    # 1. Extract user prompt with zero latency from payload if available
    user_prompt = payload.get("lastUserInput", "").strip()
    if not user_prompt:
        user_prompt = payload.get("userMessage", "").strip()
    if not user_prompt:
        tp = resolve_transcript_file(payload)
        user_prompt = extract_latest_user_prompt(tp)

    if not user_prompt:
        print(json.dumps({"injectSteps": []}))
        return

    conv_id = str(payload.get("conversationId", ""))

    # Deduplication guard: prevents duplicate injection if both workspace and global hooks fire on the exact same prompt
    if LAST_ROUTE_FILE.exists():
        try:
            prev = json.loads(LAST_ROUTE_FILE.read_text(encoding="utf-8"))
            if (
                prev.get("conversation_id") == conv_id
                and prev.get("prompt_preview") == user_prompt[:180]
                and time.time() - prev.get("epoch", 0) < 5
            ):
                print(json.dumps({"injectSteps": []}))
                return
        except Exception:
            pass

    # 2. Run 5-Tier Smart Model Classifier & 41-Repo Skill Router
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    model_info = {
        "tier": "coder",
        "model_name": "Nemotron 3.5 Lightning",
        "display": "Nemotron 3.5 Lightning (NVIDIA $0) / Llama 3.3 70B",
        "provider": "nvidia",
        "cost_tier": "Workhorse Coder ($0.00)",
    }
    resolved_tier = "coder"
    try:
        import orchestrate
        model_info = orchestrate.resolve_smart_model_telemetry(user_prompt, "auto")
        resolved_tier = model_info.get("tier", "coder")
    except Exception:
        pass

    matched_repos = []
    matched_skills = []
    matched_skill_names = []
    matched_domains = []
    matched_skill_abs_paths = []
    context_block = ""
    try:
        import skill_router
        routed = skill_router.auto_route_domain_tools(user_prompt, max_skills=3, max_chars=1800)
        matched_repos = routed.get("matched_repos", [])
        matched_skills = routed.get("matched_skills", [])
        matched_skill_names = routed.get("matched_skill_names", [])
        matched_domains = routed.get("matched_domains", [])
        matched_skill_abs_paths = routed.get("matched_skill_abs_paths", [])
        context_block = routed.get("context_block", "")
    except Exception:
        pass

    model_display = model_info.get("display", "Nemotron 3.5 Lightning (NVIDIA $0) / Llama 3.3 70B")
    model_name = model_info.get("model_name", "Nemotron 3.5 Lightning")
    skills_str = ", ".join(matched_skill_names) if matched_skill_names else (", ".join(matched_skills) if matched_skills else "workstation-auto-router, agent-orchestrator")
    repos_str = ", ".join(matched_repos[:5]) if matched_repos else "agent-orchestrator, workstation-auto-router, 9router"

    # Persist latest route telemetry for /dashboard
    route_record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": time.time(),
        "conversation_id": conv_id,
        "workspace_name": active_ws_name,
        "workspace_path": str(active_ws),
        "prompt_preview": user_prompt[:180],
        "tier": resolved_tier,
        "resolved_tier": resolved_tier,
        "model_name": model_name,
        "model_display": model_display,
        "matched_domains": matched_domains,
        "matched_repos": matched_repos[:6],
        "matched_skills": matched_skills,
        "matched_skill_names": matched_skill_names,
        "matched_skill_abs_paths": matched_skill_abs_paths[:3],
    }
    try:
        LAST_ROUTE_FILE.write_text(json.dumps(route_record, indent=2), encoding="utf-8")
    except Exception:
        pass

    creds_ok = check_credentials_configured()
    bootstrap_note = ""
    if not creds_ok:
        bootstrap_note += (
            "\n• Personal API Keys Status    : Not yet configured in local .env (Tier 1 Local Ollama works at $0.00). "
            "If the user is setting up the workstation, direct them to http://127.0.0.1:8000/dashboard ('API Keys & Cloud' button)."
        )

    native_skill_note = ""
    if matched_skill_abs_paths:
        native_skill_note = (
            f"\n• Native Skill File to Read   : {matched_skill_abs_paths[0]}\n"
            f"• Native UI Skill Activation  : When executing this task, call `read_file` on `{matched_skill_abs_paths[0]}` so Antigravity IDE natively marks the skill as Active in the chat UI and loads the complete runbook."
        )

    injected_msg = (
        f"[AUTONOMOUS WORKSTATION PRE-INVOCATION ROUTER — ACTIVE]\n"
        f"• Active Project Workspace    : {active_ws_name}\n"
        f"• Prompt Auto-Classified Tier : {resolved_tier.upper()}\n"
        f"• Auto-Resolved AI Model      : {model_display}\n"
        f"• Auto-Routed Active Skills   : {skills_str}\n"
        f"• Auto-Activated Repositories : {repos_str}{bootstrap_note}{native_skill_note}\n"
        f"{context_block}\n"
        f"MANDATORY EXECUTION DIRECTIVES:\n"
        f"1. Mandatory Status Banner: Start your response to the user with this exact 1-line status banner:\n"
        f"> ⚡ **Auto-Router**: Workspace = {active_ws_name} | Tier = `{resolved_tier}` (`{model_display}`) | Auto Skill = `{skills_str}` | Activated Repos = `{repos_str}` | Graphify AST = `Synced`\n"
        f"2. Active Skill Execution: Do NOT merely display the skill name. You MUST actively follow the concrete methodology, tools, and runbook instructions from `{skills_str}`.\n"
        f"3. Active Model Execution: When generating code, performing architectural analysis, running multi-model verification, or evaluating complex logic, actively dispatch to `{model_display}` via the Unified Gateway (http://127.0.0.1:8000/v1/chat/completions) or `workstation_complete` / `orchestrate.py`."
    )

    output = {
        "injectSteps": [
            {
                "systemMessage": {
                    "systemMessage": injected_msg
                }
            }
        ]
    }
    print(json.dumps(output))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        raw_in = sys.stdin.read()
        payload = json.loads(raw_in) if raw_in.strip() else {}
    except Exception:
        payload = {}

    is_session_start = ("--session-start" in sys.argv) or (payload.get("hookEvent") == "SessionStart")
    if is_session_start:
        handle_session_start(payload)
    else:
        handle_pre_invocation(payload)


if __name__ == "__main__":
    main()
