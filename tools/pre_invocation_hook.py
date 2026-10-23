#!/usr/bin/env python3
"""
tools/pre_invocation_hook.py
Antigravity Native Lifecycle Hook (`PreInvocation`).

Automatically runs BEFORE the model is invoked on every turn in Antigravity chat:
1. Zero-Touch First-Run Auto-Bootstrap: If a user clones this repository and opens it in
   Antigravity before running `./install.sh` or `setup_wizard.py`, automatically triggers
   background installation of the global Antigravity plugin, `.venv`, 32 repositories,
   and port 8000 gateway.
2. Reads the latest user prompt from `transcriptPath` (passed on stdin by Antigravity).
3. Runs the 5-Tier Smart Model Classifier (`resolve_smart_model`) and the
   Zero-Name 32-Repo Skill Router (`skill_router.auto_route_domain_tools`).
4. Saves the live routing decision to `~/.agent_workstation/last_route.json`
   (surfaced in real time on http://127.0.0.1:8000/dashboard).
5. Injects an `ephemeralMessage` into the model context (with per-turn deduplication)
   so every chat turn is automatically routed without manual tool calls.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
STATE_DIR = Path.home() / ".agent_workstation"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LAST_ROUTE_FILE = STATE_DIR / "last_route.json"
BOOTSTRAP_LOCK_FILE = STATE_DIR / "bootstrap.lock"


def ensure_first_run_bootstrap() -> bool:
    """
    If a user just cloned/pulled the repo and opened it in Antigravity without running
    setup_wizard.py yet, launches non-blocking background auto-setup automatically.
    Returns True if a background bootstrap was just triggered.
    """
    global_plugin = Path.home() / ".gemini" / "config" / "plugins" / "antigravity-workstation" / "plugin.json"
    if global_plugin.exists():
        return False
    if BOOTSTRAP_LOCK_FILE.exists():
        try:
            if time.time() - BOOTSTRAP_LOCK_FILE.stat().st_mtime < 600:
                return False
        except Exception:
            pass
    try:
        BOOTSTRAP_LOCK_FILE.write_text(str(int(time.time())), encoding="utf-8")
        wizard_py = TOOLS_DIR / "setup_wizard.py"
        if wizard_py.exists():
            log_path = STATE_DIR / "auto_bootstrap.log"
            with open(log_path, "a", encoding="utf-8") as lf:
                subprocess.Popen(
                    [sys.executable, str(wizard_py), "--auto"],
                    cwd=str(REPO_ROOT),
                    stdout=lf,
                    stderr=lf,
                    start_new_session=True,
                )
            return True
    except Exception:
        pass
    return False


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
    if brain_root.exists():
        candidates = list(brain_root.glob("*/.system_generated/logs/transcript.jsonl"))
        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return candidates[0]
    return Path("")


def extract_latest_user_prompt(tp: Path) -> str:
    """Reads the tail of transcript.jsonl to extract the most recent USER_INPUT content."""
    if not tp or not tp.exists() or not tp.is_file():
        return ""
    try:
        file_size = tp.stat().st_size
        with open(tp, "rb") as f:
            if file_size > 524288:
                f.seek(file_size - 524288)
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


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        raw_in = sys.stdin.read()
        payload = json.loads(raw_in) if raw_in.strip() else {}
    except Exception:
        payload = {}

    bootstrapped_now = ensure_first_run_bootstrap()

    invocation_num = payload.get("invocationNum", 1)
    if invocation_num and int(invocation_num) > 1:
        print(json.dumps({"injectSteps": []}))
        return

    conv_id = str(payload.get("conversationId", ""))

    tp = resolve_transcript_file(payload)
    user_prompt = extract_latest_user_prompt(tp)
    if not user_prompt:
        print(json.dumps({"injectSteps": []}))
        return

    # Deduplication guard: only inject ONCE per unique user prompt turn (prevents duplicate firing from workspace + global hooks or mid-turn tool steps)
    if LAST_ROUTE_FILE.exists():
        try:
            prev = json.loads(LAST_ROUTE_FILE.read_text(encoding="utf-8"))
            if (
                prev.get("conversation_id") == conv_id
                and prev.get("prompt_preview") == user_prompt[:180]
            ):
                print(json.dumps({"injectSteps": []}))
                return
        except Exception:
            pass

    # 1. Run 5-Tier Smart Model Classifier & 32-Repo Skill Router
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    resolved_tier = "coder"
    try:
        import orchestrate
        resolved_tier = orchestrate.resolve_smart_model(user_prompt, "auto")
    except Exception:
        pass

    matched_repos = []
    matched_skills = []
    matched_domains = []
    matched_skill_abs_paths = []
    context_block = ""
    try:
        import skill_router
        routed = skill_router.auto_route_domain_tools(user_prompt, max_skills=3, max_chars=1800)
        matched_repos = routed.get("matched_repos", [])
        matched_skills = routed.get("matched_skills", [])
        matched_domains = routed.get("matched_domains", [])
        matched_skill_abs_paths = routed.get("matched_skill_abs_paths", [])
        context_block = routed.get("context_block", "")
    except Exception:
        pass

    # Persist latest route telemetry for /dashboard
    route_record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": time.time(),
        "conversation_id": conv_id,
        "invocation_num": invocation_num,
        "prompt_preview": user_prompt[:180],
        "tier": resolved_tier,
        "resolved_tier": resolved_tier,
        "matched_domains": matched_domains,
        "matched_repos": matched_repos[:6],
        "matched_skills": matched_skills,
        "matched_skill_abs_paths": matched_skill_abs_paths[:3],
    }
    try:
        LAST_ROUTE_FILE.write_text(json.dumps(route_record, indent=2), encoding="utf-8")
    except Exception:
        pass

    repos_str = ", ".join(matched_repos[:5]) if matched_repos else "Core Workstation Engine"
    skills_str = ", ".join(matched_skills) if matched_skills else "Principal Engineering Constitution"
    creds_ok = check_credentials_configured()
    bootstrap_note = ""
    if bootstrapped_now:
        bootstrap_note += (
            "\n• First-Run Auto-Bootstrap    : Triggered automatically in background (~/.agent_workstation/auto_bootstrap.log)"
        )
    if not creds_ok:
        bootstrap_note += (
            "\n• Personal API Keys Status    : Not yet configured in local .env (Tier 1 Local Ollama works at $0.00). "
            "If the user is setting up the workstation, ask them for their personal API keys (NVIDIA NIM / AWS / Gemini / OpenRouter) "
            "or direct them to http://127.0.0.1:8000/dashboard ('API Keys & Cloud' button) or `python3 tools/setup_wizard.py`."
        )
    native_skill_note = ""
    if matched_skill_abs_paths:
        native_skill_note = (
            f"\n• Native Skill File to Read   : {matched_skill_abs_paths[0]}\n"
            f"• Native UI Skill Activation  : When executing this task, call `read_file` on `{matched_skill_abs_paths[0]}` so Antigravity IDE natively marks the skill as Active in the chat UI and loads the complete runbook."
        )

    injected_msg = (
        f"[AUTONOMOUS WORKSTATION PRE-INVOCATION ROUTER — ACTIVE]\n"
        f"• Prompt Auto-Classified Tier : {resolved_tier.upper()}\n"
        f"• Auto-Activated Repositories : {repos_str}\n"
        f"• Auto-Injected Skill Runbooks: {skills_str}{bootstrap_note}{native_skill_note}\n"
        f"{context_block}\n"
        f"MANDATORY RESPONSE REQUIREMENT: Start your response to the user with this exact 1-line status banner:\n"
        f"> ⚡ **Auto-Router**: Tier = `{resolved_tier}` | Activated Repos = `{repos_str}` | Graphify AST = `Synced`"
    )

    print(json.dumps({
        "injectSteps": [
            {
                "ephemeralMessage": injected_msg
            }
        ]
    }))


if __name__ == "__main__":
    main()
