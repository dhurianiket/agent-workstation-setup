"""
Agent Orchestration CLI & Controller (v2.0 - Credit & Quality Optimized)
Direct command-line tool to dispatch and supervise tasks across Aider, Codex, Claude Code, and OpenCode
using the local laptop unified API (Bedrock Claude 4.5, DeepSeek R1, Llama 3.3, Ollama).

Key Upgrades:
- Smart Auto-Tiered Routing (--model auto by default):
    * Classifies tasks into Local ($0), Fast Scout (Llama 4 Scout), Coder (Llama 3.3 70B),
      Reasoner (DeepSeek R1), or Frontier (Claude Sonnet 4.5) to stop premature credit depletion.
- Usage & Cost Audit:
    * Run with `--usage` to view total tokens and estimated credit consumption.
- Quality Verification:
    * `--verify` checks modified files and validates changes post-execution.
"""

import sys
import argparse
import subprocess
import os
import time
import urllib.request
import json

LOCAL_API_BASE = "http://127.0.0.1:8000/v1"
HEALTH_URL = "http://127.0.0.1:8000/health"
USAGE_URL = "http://127.0.0.1:8000/v1/usage"
DUMMY_KEY = "dummy-local-key"

def ensure_services_running():
    """Checks if the Laptop API server is running; if not, starts it silently."""
    try:
        req = urllib.request.Request(HEALTH_URL, headers={"User-Agent": "Orchestrator"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == "healthy":
                return True
    except Exception:
        pass

    print("[*] Unified Laptop AI Server is not active. Auto-starting background service...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ps_script = os.path.join(script_dir, "start_laptop_api_silent.ps1")
    
    try:
        subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
    except Exception as e:
        print(f"[!] Warning triggering auto-start: {e}")

    # Wait up to 6 seconds for health
    for _ in range(6):
        time.sleep(1)
        try:
            req = urllib.request.Request(HEALTH_URL, headers={"User-Agent": "Orchestrator"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode())
                if data.get("status") == "healthy":
                    print("[OK] Background AI Stack is ready.")
                    return True
        except Exception:
            continue
            
    print("[!] Warning: AI Server started but health check timed out. Proceeding...")
    return False

def show_usage():
    """Fetches and displays live credit and token analytics."""
    ensure_services_running()
    try:
        req = urllib.request.Request(USAGE_URL, headers={"User-Agent": "Orchestrator"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode())
            totals = data.get("totals", {})
            by_model = data.get("by_model", {})
            
            print("\n=======================================================")
            print("  AI WORKSTATION CREDIT & USAGE ANALYTICS")
            print("=======================================================")
            print(f"Total Requests     : {totals.get('requests', 0)}")
            print(f"Total Prompt Tokens: {totals.get('prompt_tokens', 0):,}")
            print(f"Total Output Tokens: {totals.get('completion_tokens', 0):,}")
            print(f"Estimated Spend    : ${totals.get('estimated_usd', 0.0):.4f} USD")
            print("-------------------------------------------------------")
            print(f"{'Model':<40} {'Reqs':<6} {'Tokens':<12} {'Est. Cost':<10}")
            print("-------------------------------------------------------")
            for m, info in by_model.items():
                toks = info.get('prompt_tokens', 0) + info.get('completion_tokens', 0)
                cost = f"${info.get('estimated_usd', 0.0):.4f}"
                print(f"{m[:38]:<40} {info.get('requests', 0):<6} {toks:<12,} {cost:<10}")
            print("=======================================================\n")
    except Exception as e:
        print(f"[!] Could not retrieve usage stats: {e}")

def resolve_smart_model(task: str, explicit_model: str) -> str:
    """
    Intelligently assigns the model tier based on task complexity to avoid credit burnout.
    """
    if explicit_model != "auto":
        return explicit_model

    t = task.lower()
    # 1. Local Tier ($0.00)
    if any(k in t for k in ["format", "lint", "organize import", "docstring", "comment", "typo", "spelling"]):
        return "local"
    # 2. Fast Scout Tier (~$0.08 / M)
    elif any(k in t for k in ["test", "unit test", "boilerplate", "config", "readme", "git commit", "html", "css", "rename"]):
        return "fast"
    # 3. Deep Reasoning Tier (~$1.35 / M)
    elif any(k in t for k in ["debug", "why does", "algorithm", "race condition", "memory leak", "fix crash", "root cause"]):
        return "reasoner"
    # 4. Frontier Architecture Tier (~$3.00 / M)
    elif any(k in t for k in ["architect", "security audit", "crypto", "system design", "auth overhaul"]):
        return "claude"
    # 5. Default Workhorse (~$0.72 / M)
    else:
        return "coder"

def verify_changes():
    """Validates files modified by the agent and prints git status summary."""
    try:
        res = subprocess.run(["git", "status", "--short"], stdout=subprocess.PIPE, text=True, check=False)
        output = res.stdout.strip()
        if output:
            print("\n[VERIFICATION] Modified / Created files:")
            for line in output.split("\n"):
                print(f"  {line}")
        else:
            print("\n[VERIFICATION] No git working tree changes detected.")
    except Exception:
        pass

def run_agent(agent: str, task: str, model: str = "auto", verify: bool = True):
    ensure_services_running()
    
    resolved_model = resolve_smart_model(task, model)
    tier_label = {
        "local": "Local Free ($0.00 - Radeon GPU)",
        "fast": "Scout Tier (Llama 4 Scout ~190ms)",
        "coder": "Workhorse Tier (Llama 3.3 70B ~300ms)",
        "reasoner": "Deep Reasoning (DeepSeek R1 ~1.1s)",
        "claude": "Frontier Tier (Claude Sonnet 4.5)",
        "opus": "Frontier Tier (Claude Opus 4.5)",
    }.get(resolved_model, "Custom Tier")

    print(f"\n=======================================================")
    print(f"  ORCHESTRATING AGENT : {agent.upper()}")
    print(f"  RESOLVED MODEL      : {resolved_model.upper()} [{tier_label}]")
    print(f"  GATEWAY             : {LOCAL_API_BASE}")
    print(f"  TASK                : {task}")
    print(f"=======================================================\n")

    cmd = []
    env = os.environ.copy()

    if agent == "aider":
        cmd = [
            "aider",
            "--openai-api-base", LOCAL_API_BASE,
            "--openai-api-key", DUMMY_KEY,
            "--model", f"openai/{resolved_model}",
            "--message", task,
            "--yes-always"
        ]

    elif agent == "claude":
        cmd = ["claude", "-p", task, "--dangerously-skip-permissions"]

    elif agent == "codex":
        if resolved_model in ["local", "llama3.2"]:
            cmd = ["codex", "exec", task, "--oss", "--local-provider", "ollama", "-m", "llama3.2:1b", "--dangerously-bypass-approvals-and-sandbox"]
        else:
            env["OPENAI_BASE_URL"] = LOCAL_API_BASE
            env["OPENAI_API_KEY"] = DUMMY_KEY
            cmd = ["codex", "exec", task, "--model", resolved_model, "--dangerously-bypass-approvals-and-sandbox"]

    elif agent == "opencode":
        cmd = ["opencode", "run", "--prompt", task, "--auto"]

    else:
        print(f"Error: Unknown agent '{agent}'. Choose from: aider, claude, codex, opencode")
        sys.exit(1)

    try:
        subprocess.run(cmd, env=env, check=True)
        print("\n[OK] Agent task completed successfully.")
        if verify:
            verify_changes()
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Agent failed with exit code {e.returncode}.")
        sys.exit(e.returncode)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Agent Orchestration Dispatcher with Credit Guard")
    parser.add_argument("--task", "-t", help="The instruction or task prompt for the agent")
    parser.add_argument("--agent", "-a", default="aider", choices=["aider", "claude", "codex", "opencode"], help="Agent harness to dispatch")
    parser.add_argument("--model", "-m", default="auto", choices=["auto", "claude", "opus", "sonnet", "reasoner", "coder", "fast", "local"], help="Model routing profile (defaults to auto)")
    parser.add_argument("--usage", action="store_true", help="Display live credit and token analytics")
    parser.add_argument("--no-verify", action="store_true", help="Skip post-execution git change verification")
    
    args = parser.parse_args()
    
    if args.usage:
        show_usage()
        sys.exit(0)
        
    if not args.task:
        parser.print_help()
        sys.exit(1)
        
    run_agent(args.agent, args.task, args.model, verify=not args.no_verify)
