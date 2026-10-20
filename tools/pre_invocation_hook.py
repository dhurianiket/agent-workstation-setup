#!/usr/bin/env python3
"""
tools/pre_invocation_hook.py
Antigravity Native Lifecycle Hook (`PreInvocation`).

Automatically runs BEFORE the model is invoked on every turn in Antigravity chat:
1. Reads the latest user prompt from `transcriptPath` (passed on stdin by Antigravity).
2. Runs the 5-Tier Smart Model Classifier (`resolve_smart_model`) and the
   Zero-Name 32-Repo Skill Router (`skill_router.auto_route_domain_tools`).
3. Saves the live routing decision to `~/.agent_workstation/last_route.json`
   (surfaced in real time on http://127.0.0.1:8000/dashboard).
4. Injects an `ephemeralMessage` into the model context so every chat turn is
   automatically routed without manual tool calls.
"""

import json
import sys
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
STATE_DIR = Path.home() / ".agent_workstation"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LAST_ROUTE_FILE = STATE_DIR / "last_route.json"


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
    # Fallback: most recently modified transcript.jsonl across active conversations
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
        # Read last 512KB of transcript.jsonl for fast tail scan
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

    invocation_num = payload.get("invocationNum", 1)
    # Only inject on the first invocation of a user turn to keep subsequent tool steps fast
    if invocation_num and int(invocation_num) > 1:
        print(json.dumps({"injectSteps": []}))
        return

    tp = resolve_transcript_file(payload)
    user_prompt = extract_latest_user_prompt(tp)
    if not user_prompt:
        print(json.dumps({"injectSteps": []}))
        return

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
    context_block = ""
    try:
        import skill_router
        routed = skill_router.auto_route_domain_tools(user_prompt, max_skills=3, max_chars=1400)
        matched_repos = routed.get("matched_repos", [])
        matched_skills = routed.get("matched_skills", [])
        matched_domains = routed.get("matched_domains", [])
        context_block = routed.get("context_block", "")
    except Exception:
        pass

    # Persist latest route telemetry for /dashboard
    route_record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "prompt_preview": user_prompt[:180],
        "tier": resolved_tier,
        "resolved_tier": resolved_tier,
        "matched_domains": matched_domains,
        "matched_repos": matched_repos[:6],
        "matched_skills": matched_skills
    }
    try:
        LAST_ROUTE_FILE.write_text(json.dumps(route_record, indent=2), encoding="utf-8")
    except Exception:
        pass

    repos_str = ", ".join(matched_repos[:5]) if matched_repos else "Core Workstation Engine"
    skills_str = ", ".join(matched_skills) if matched_skills else "Principal Engineering Constitution"

    injected_msg = (
        f"[AUTONOMOUS WORKSTATION PRE-INVOCATION ROUTER — ACTIVE]\n"
        f"• Prompt Auto-Classified Tier : {resolved_tier.upper()}\n"
        f"• Auto-Activated Repositories : {repos_str}\n"
        f"• Auto-Injected Skill Runbooks: {skills_str}\n"
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
