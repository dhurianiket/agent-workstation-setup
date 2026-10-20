"""
Agent Orchestration CLI & Controller
Direct command-line tool to dispatch and supervise tasks across Aider, Codex, Claude Code, and OpenCode
using the local laptop unified API (Bedrock Claude 4.5, DeepSeek R1, Llama 3.3, Ollama).
Includes automatic self-healing and zero-config service startup.
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

def run_agent(agent: str, task: str, model: str = "claude"):
    ensure_services_running()
    
    print(f"\n=======================================================")
    print(f"  ORCHESTRATING AGENT : {agent.upper()}")
    print(f"  MODEL PROFILE       : {model.upper()}")
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
            "--model", f"openai/{model}",
            "--message", task,
            "--yes-always"
        ]

    elif agent == "claude":
        cmd = ["claude", "-p", task, "--dangerously-skip-permissions"]

    elif agent == "codex":
        if model in ["local", "llama3.2"]:
            cmd = ["codex", "exec", task, "--oss", "--local-provider", "ollama", "-m", "llama3.2:1b", "--dangerously-bypass-approvals-and-sandbox"]
        else:
            env["OPENAI_BASE_URL"] = LOCAL_API_BASE
            env["OPENAI_API_KEY"] = DUMMY_KEY
            cmd = ["codex", "exec", task, "--model", model, "--dangerously-bypass-approvals-and-sandbox"]

    elif agent == "opencode":
        cmd = ["opencode", "run", "--prompt", task, "--auto"]

    else:
        print(f"Error: Unknown agent '{agent}'. Choose from: aider, claude, codex, opencode")
        sys.exit(1)

    try:
        subprocess.run(cmd, env=env, check=True)
        print("\n[OK] Agent task completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Agent failed with exit code {e.returncode}.")
        sys.exit(e.returncode)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Agent Orchestration Dispatcher")
    parser.add_argument("--task", "-t", required=True, help="The instruction or task prompt for the agent")
    parser.add_argument("--agent", "-a", default="aider", choices=["aider", "claude", "codex", "opencode"], help="Agent harness to dispatch")
    parser.add_argument("--model", "-m", default="claude", choices=["claude", "opus", "sonnet", "reasoner", "coder", "fast", "local"], help="Model routing profile")
    
    args = parser.parse_args()
    run_agent(args.agent, args.task, args.model)
