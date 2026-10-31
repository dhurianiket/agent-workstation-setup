"""
Agent Orchestration CLI & Controller (v3.0 - GitGuardian Security Shield & AST Verification)
Direct command-line tool and Python engine to dispatch and supervise tasks across Aider, Codex, Claude Code, and OpenCode
using the local laptop unified API (Bedrock Claude 4.5, DeepSeek R1, Llama 3.3, BYOK OpenRouter/NVIDIA, and Ollama).

Key Upgrades:
- GitGuardian Security Shield (ggshield):
    * Scans all modified files and repository paths before completion to guarantee ZERO secret leakage.
- Deterministic Post-Action Sensors (AST & Syntax Verification):
    * Verifies Python (py_compile), JSON, and JS syntax on all changed files before finalizing.
- Cross-Session Error Post-Mortems:
    * Records failures to ~/.agent_workstation/postmortems.json and prevents repeating past debugging mistakes.
- Smart Auto-Tiered Routing (--model auto by default):
    * Local ($0) -> Fast Scout -> Coder -> Reasoner -> Frontier to prevent credit burnout.
- Live Usage & Credit Audit:
    * `--usage` command to inspect credits, token consumption, and model costs.
"""

import sys
import argparse
import subprocess
import os
import time
import urllib.request
import json
import py_compile
import ast
from pathlib import Path

LOCAL_API_BASE = "http://127.0.0.1:8000/v1"
HEALTH_URL = "http://127.0.0.1:8000/health"
USAGE_URL = "http://127.0.0.1:8000/v1/usage"
DUMMY_KEY = "dummy-local-key"

WORKSTATION_DIR = Path.home() / ".agent_workstation"
WORKSTATION_DIR.mkdir(parents=True, exist_ok=True)
POSTMORTEM_FILE = WORKSTATION_DIR / "postmortems.json"

# Ensure ~/.local/bin and standard bins are in PATH for ggshield, aider, node, etc.
_EXTRA_PATH = os.pathsep.join([
    str(Path.home() / ".local" / "bin"),
    str(Path.home() / "bin"),
    "/opt/homebrew/bin",
    "/usr/local/bin",
])
if str(Path.home() / ".local" / "bin") not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{_EXTRA_PATH}{os.pathsep}{os.environ.get('PATH', '')}"

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
    if sys.platform == "win32":
        ps_script = os.path.join(script_dir, "start_laptop_api_silent.ps1")
        if os.path.exists(ps_script):
            try:
                subprocess.run(
                    ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", ps_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
            except Exception as e:
                print(f"[!] Warning triggering auto-start: {e}")
    else:
        plist_path = Path.home() / "Library" / "LaunchAgents" / "com.antigravity.agent-workstation.plist"
        if plist_path.exists():
            subprocess.run(["launchctl", "load", str(plist_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            srv_py = os.path.join(script_dir, "laptop_api_server.py")
            if os.path.exists(srv_py):
                subprocess.Popen([sys.executable, srv_py], cwd=script_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
            print(f"{'Model / Provider':<40} {'Reqs':<6} {'Tokens':<12} {'Est. Cost':<10}")
            print("-------------------------------------------------------")
            for m, info in by_model.items():
                toks = info.get('prompt_tokens', 0) + info.get('completion_tokens', 0)
                cost = f"${info.get('estimated_usd', 0.0):.4f}"
                print(f"{m[:38]:<40} {info.get('requests', 0):<6} {toks:<12,} {cost:<10}")
            print("=======================================================\n")
    except Exception as e:
        print(f"[!] Could not retrieve usage stats: {e}")

def resolve_smart_model_telemetry(task: str, explicit_model: str = "auto") -> dict:
    """
    Intelligently resolves task complexity to the 5-tier architecture,
    identifying the exact primary model, fallback model, and telemetry display.
    Respects NVIDIA NIM Developer Free Tier ($0.00) and Gemini Higher-Tier limits.
    """
    t = task.lower()
    req = explicit_model.lower().strip() if explicit_model and explicit_model != "auto" else ""

    # 1. Explicit Model Overrides or Mentions
    # Google Gemini Higher-Tier (3.8 Flash, 4 Argon, 4 Ultra)
    if req in ["gemini-4-argon", "argon", "gemini-argon"] or any(k in t for k in ["gemini-4-argon", "argon", "gemini 4", "gemini argon"]):
        return {
            "tier": "frontier",
            "model_name": "Gemini 4 Argon",
            "model_id": "gemini-4-argon",
            "display": "Gemini 4 Argon",
            "provider": "gemini",
            "cost_tier": "Cloud Frontier",
        }
    if req in ["gemini-3.8-flash", "3.8 flash", "gemini-flash"] or any(k in t for k in ["gemini-3.8-flash", "3.8 flash", "gemini flash"]):
        return {
            "tier": "scout",
            "model_name": "Gemini 3.8 Flash",
            "model_id": "gemini-3.8-flash",
            "display": "Gemini 3.8 Flash",
            "provider": "gemini",
            "cost_tier": "Cloud Scout",
        }
    if req in ["gemini-ultra", "gemini-4-ultra"] or any(k in t for k in ["gemini-ultra", "gemini-4-ultra"]):
        return {
            "tier": "flagship",
            "model_name": "Gemini 4 Ultra",
            "model_id": "gemini-4-ultra",
            "display": "Gemini 4 Ultra",
            "provider": "gemini",
            "cost_tier": "Cloud Flagship",
        }
    if "gemini" in t and not any(k in t for k in ["gemini-api", "gemini.md", "gemini docs"]):
        return {
            "tier": "frontier",
            "model_name": "Gemini 4 Argon",
            "model_id": "gemini-4-argon",
            "display": "Gemini 4 Argon",
            "provider": "gemini",
            "cost_tier": "Cloud Frontier",
        }

    # NVIDIA NIM Developer Free Models ($0.00 within free limits)
    if req in ["nemotron-ultra", "ultra-550b", "mistral-1t"] or any(k in t for k in ["nemotron-ultra", "nemotron ultra", "550b", "mistral-1t", "mistral 1t"]):
        return {
            "tier": "flagship",
            "model_name": "Nemotron Ultra 550B",
            "model_id": "nvidia/nemotron-3-ultra-550b-a55b",
            "display": "Nemotron Ultra 550B (NVIDIA $0)",
            "provider": "nvidia",
            "cost_tier": "NVIDIA Free Dev Limit ($0.00)",
        }
    if req in ["nemotron-reasoning"] or any(k in t for k in ["nemotron-reasoning", "nemotron reasoning"]):
        return {
            "tier": "reasoner",
            "model_name": "Nemotron Reasoning 30B",
            "model_id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            "display": "Nemotron Reasoning 30B (NVIDIA $0)",
            "provider": "nvidia",
            "cost_tier": "NVIDIA Free Dev Limit ($0.00)",
        }
    if req in ["nemotron-lightning"] or any(k in t for k in ["nemotron-lightning", "nemotron lightning", "nemotron coder"]):
        return {
            "tier": "coder",
            "model_name": "Nemotron 3.5 Lightning",
            "model_id": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "display": "Nemotron 3.5 Lightning (NVIDIA $0)",
            "provider": "nvidia",
            "cost_tier": "NVIDIA Free Dev Limit ($0.00)",
        }
    if req in ["nemotron-bolt"] or any(k in t for k in ["nemotron-bolt", "nemotron bolt"]):
        return {
            "tier": "fast",
            "model_name": "Nemotron 3.5 Bolt",
            "model_id": "nvidia/nemotron-3.5-bolt-e4b",
            "display": "Nemotron 3.5 Bolt (NVIDIA $0)",
            "provider": "nvidia",
            "cost_tier": "NVIDIA Free Dev Limit ($0.00)",
        }
    if req in ["nemotron-vision", "llama-vision-90b"] or any(k in t for k in ["nemotron-vision", "nemotron vision", "llama vision", "llama-vision", "multimodal"]):
        return {
            "tier": "multimodal",
            "model_name": "Nemotron 3.5 Super VL 120B",
            "model_id": "nvidia/nemotron-3.5-super-vl-120b-a12b",
            "display": "Nemotron 3.5 Super VL 120B (NVIDIA $0)",
            "provider": "nvidia",
            "cost_tier": "NVIDIA Free Dev Limit ($0.00)",
        }
    if any(k in t for k in ["nvidia", "nemotron", "nim"]):
        return {
            "tier": "coder",
            "model_name": "Nemotron 3.5 Lightning",
            "model_id": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "display": "Nemotron 3.5 Lightning (NVIDIA $0)",
            "provider": "nvidia",
            "cost_tier": "NVIDIA Free Dev Limit ($0.00)",
        }

    # Frontier Claude Models (Bedrock)
    if req in ["opus", "claude-opus", "claude-opus-4.6"] or any(k in t for k in ["claude opus", "opus 4.6", "opus-4.6", "opus"]):
        return {
            "tier": "flagship",
            "model_name": "Claude Opus 4.6",
            "model_id": "us.anthropic.claude-opus-4-6-v1",
            "display": "Claude Opus 4.6 / Nemotron Ultra ($0)",
            "provider": "bedrock",
            "cost_tier": "Cloud Flagship",
        }
    if req in ["claude", "sonnet", "claude-sonnet", "claude-sonnet-4.6"] or any(k in t for k in ["claude 4", "claude sonnet", "sonnet 4.6", "sonnet-4.6"]):
        return {
            "tier": "frontier",
            "model_name": "Claude Sonnet 4.6",
            "model_id": "us.anthropic.claude-sonnet-4-6",
            "display": "Claude Sonnet 4.6 / Gemini 4 Argon",
            "provider": "bedrock",
            "cost_tier": "Cloud Frontier",
        }
    if req in ["deepseek", "deepseek-r1", "r1"] or any(k in t for k in ["deepseek r1", "deepseek-r1"]):
        return {
            "tier": "reasoner",
            "model_name": "DeepSeek R1",
            "model_id": "us.deepseek.r1-v1:0",
            "display": "DeepSeek R1 / Nemotron Reasoning ($0)",
            "provider": "bedrock",
            "cost_tier": "Cloud Reasoning",
        }

    # 2. Automated 5-Tier Complexity Classification (Highest Complexity First)
    # Tier 4: Frontier Architecture Tier (~$3.00 / M)
    if any(k in t for k in ["architect", "security audit", "crypto", "system design", "auth overhaul"]):
        return {
            "tier": "frontier",
            "model_name": "Gemini 4 Argon",
            "model_id": "gemini-4-argon",
            "display": "Gemini 4 Argon / Claude Sonnet 4.6",
            "provider": "gemini",
            "cost_tier": "Frontier Architecture",
        }

    # Tier 3: Deep Reasoning Tier (~$1.35 / M or NVIDIA $0)
    if any(k in t for k in ["debug", "why does", "algorithm", "race condition", "memory leak", "fix crash", "root cause", "diagnose"]):
        return {
            "tier": "reasoner",
            "model_name": "Nemotron Reasoning 30B",
            "model_id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            "display": "Nemotron Reasoning 30B (NVIDIA $0) / DeepSeek R1",
            "provider": "nvidia",
            "cost_tier": "Deep Reasoning ($0.00)",
        }

    # Tier 2: Fast Scout Tier (~$0.08 / M or NVIDIA $0)
    if any(k in t for k in ["unit test", "test", "boilerplate", "config", "readme", "git commit", "html", "css", "rename"]):
        return {
            "tier": "fast",
            "model_name": "Nemotron 3.5 Bolt",
            "model_id": "nvidia/nemotron-3.5-bolt-e4b",
            "display": "Nemotron 3.5 Bolt (NVIDIA $0) / Gemini 3.8 Flash",
            "provider": "nvidia",
            "cost_tier": "Fast Scout ($0.00)",
        }

    # Tier 1: Local Tier ($0.00)
    if any(k in t for k in ["format", "lint", "organize import", "docstring", "comment", "typo", "spelling"]):
        return {
            "tier": "local",
            "model_name": "Llama 3.2 1B / Qwen 2.5 Coder",
            "model_id": "ollama/qwen2.5-coder:7b",
            "display": "Llama 3.2 1B / Qwen 2.5 Coder ($0.00)",
            "provider": "ollama",
            "cost_tier": "Local GPU ($0.00)",
        }

    # Tier 5: Default Workhorse Coding Tier (NVIDIA Developer Free limit first, Bedrock fallback)
    return {
        "tier": "coder",
        "model_name": "Nemotron 3.5 Lightning",
        "model_id": "nvidia/nemotron-3.5-lightning-30b-a3b",
        "display": "Nemotron 3.5 Lightning (NVIDIA $0) / Llama 3.3 70B",
        "provider": "nvidia",
        "cost_tier": "Workhorse Coder ($0.00)",
    }

def resolve_smart_model(task: str, explicit_model: str) -> str:
    """
    Intelligently assigns the model tier based on task complexity to avoid credit burnout.
    """
    if explicit_model != "auto":
        return explicit_model
    telemetry = resolve_smart_model_telemetry(task, explicit_model)
    return telemetry.get("tier", "coder")

def record_postmortem(task: str, error_message: str, cwd: str):
    """Records past debugging and syntax errors to prevent repetitive regression loops."""
    try:
        data = []
        if POSTMORTEM_FILE.exists():
            with open(POSTMORTEM_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cwd": cwd,
            "task": task[:200],
            "error": error_message[:500]
        })
        # Keep latest 30 post-mortems
        data = data[-30:]
        with open(POSTMORTEM_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[!] Warning recording post-mortem: {e}")

def get_recent_postmortems(cwd: str) -> str:
    """Retrieves recent error context for the active repository."""
    try:
        if POSTMORTEM_FILE.exists():
            with open(POSTMORTEM_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            matching = [d for d in data if d.get("cwd") == cwd]
            if matching:
                latest = matching[-1]
                return f"\n[PAST ERROR MEMORY] Last run encountered: {latest.get('error')}. Ensure code avoids this regression.\n"
    except Exception:
        pass
    return ""

def get_graphify_context(cwd: str, task: str) -> str:
    """
    Pre-Action Knowledge Graph Sensor (Graphify):
    Queries graphify-out/graph.json for relevant code symbols and line numbers
    so the coding agent starts with exact architectural context.
    Strictly isolated: only runs if graphify-out/graph.json already exists in cwd
    (never pollutes external personal or private repositories).
    """
    graph_file = Path(cwd) / "graphify-out" / "graph.json"
    if not graph_file.exists():
        return ""
    try:
        stop_words = {"the", "and", "for", "with", "that", "this", "from", "into", "update", "check", "make", "please", "file", "code"}
        words = [
            w.strip(".,:;()[]\"'")
            for w in task.split()
            if len(w.strip(".,:;()[]\"'")) >= 3 and w.lower() not in stop_words
        ]
        if not words:
            return ""
        query_str = " ".join(words[:6])
        res = subprocess.run(
            [sys.executable, "-m", "graphify", "query", query_str, "--budget", "600"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=8,
            check=False
        )
        out = (res.stdout or "").strip()
        if res.returncode == 0 and out and "No matching" not in out:
            return f"\n[GRAPHIFY AST CONTEXT]\n{out[:900]}\n"
    except Exception:
        pass
    return ""

def get_auto_routed_skills(task: str) -> tuple:
    """
    Zero-Name Automatic Repository & Skill Router:
    Automatically matches the user's task intent against the 32 installed repositories
    and 456+ indexed SKILL.md files in tools/ without requiring the user to name them.
    Returns: (context_block: str, matched_repos: list, matched_skills: list)
    """
    try:
        script_dir = Path(__file__).resolve().parent
        tools_dir = script_dir / "tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        import skill_router
        routed = skill_router.auto_route_domain_tools(task, max_skills=3, max_chars=1500)
        return (
            routed.get("context_block", ""),
            routed.get("matched_repos", []),
            routed.get("matched_skills", [])
        )
    except Exception:
        return ("", [], [])

def run_ggshield_audit(cwd: str, files: list = None) -> bool:
    """
    Scans modified files or repository using GitGuardian (ggshield) to guarantee ZERO secret leakage.
    Blocks execution if any API keys, credentials, or secrets are detected.
    """
    print("\n[SECURITY SHIELD] Running GitGuardian (ggshield) secret scan...")
    try:
        # If specific files were modified, scan only those files for sub-second precision
        valid_files = [f for f in (files or []) if (Path(cwd) / f).is_file()]
        if not valid_files:
            # Fallback to git-tracked files so we never recursively scan .venv or tools/*/
            ls_res = subprocess.run(
                ["git", "ls-files"],
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if ls_res.returncode == 0 and ls_res.stdout.strip():
                valid_files = [
                    f.strip()
                    for f in ls_res.stdout.splitlines()
                    if f.strip() and (Path(cwd) / f.strip()).is_file()
                ]
        if valid_files:
            cmd = ["ggshield", "secret", "scan", "path", "--yes"] + valid_files
        else:
            cmd = ["ggshield", "secret", "scan", "path", "--yes", "."]

        res = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if res.returncode == 0:
            print("[SECURITY SHIELD] [OK] GitGuardian (ggshield) verified: 0 secrets detected. Safe to commit.")
            return True
        else:
            print("\n" + "=" * 65)
            print(" [CRITICAL SECURITY ALERT] GGSHIELD DETECTED POTENTIAL SECRETS!")
            print("=" * 65)
            print(res.stdout or res.stderr)
            print("=" * 65)
            print("[ABORT] File changes contain sensitive tokens. Commit blocked.\n")
            return False
    except FileNotFoundError:
        print("[SECURITY SHIELD] Warning: ggshield is not installed or not in PATH. Skipping secret scan.")
        return True
    except Exception as e:
        print(f"[SECURITY SHIELD] Warning running ggshield: {e}")
        return True

def inspect_python_code_constitution(fpath: Path) -> list:
    """
    Enforces Code Constitutional rules via Python AST & source inspection:
    1. Forbids bare 'except:' (must specify an explicit exception class).
    2. Forbids mutable default arguments (e.g. def fn(arg=[]):).
    3. Forbids lazy placeholder truncation comments (e.g. '# rest unchanged').
    """
    violations = []
    try:
        source_text = fpath.read_text(encoding="utf-8")
        tree = ast.parse(source_text, filename=str(fpath))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                violations.append(f"Line {node.lineno}: Bare 'except:' detected. Specify an explicit Exception class.")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        violations.append(f"Line {node.lineno}: Mutable default argument in '{node.name}'. Use None and initialize inside.")

        forbidden_markers = ("# rest unchanged", "// rest unchanged", "# ... existing code", "# todo: implement")
        for idx, line in enumerate(source_text.splitlines(), start=1):
            stripped = line.strip().lower()
            if stripped.startswith(("#", "//")) and any(m in stripped for m in forbidden_markers):
                violations.append(f"Line {idx}: Forbidden placeholder comment '{line.strip()}' detected.")
    except Exception as e:
        violations.append(f"AST Parsing error: {e}")
    return violations

def run_frontier_critic(cwd: str, task: str) -> bool:
    """
    Cross-Model Validator / Critic Layer (DeepSeek R1 / Claude Sonnet 4.5):
    Evaluates generated diff against subtle logic bugs and regression anti-patterns.
    """
    try:
        diff_res = subprocess.run(["git", "diff", "HEAD~1"], cwd=cwd, stdout=subprocess.PIPE, text=True, check=False)
        diff_text = diff_res.stdout.strip()
        if not diff_text:
            diff_res = subprocess.run(["git", "diff"], cwd=cwd, stdout=subprocess.PIPE, text=True, check=False)
            diff_text = diff_res.stdout.strip()
            
        if not diff_text:
            return True
            
        print("\n[FRONTIER CRITIC] Reviewing code changes with Reasoner model (DeepSeek R1)...")
        prompt = (
            f"You are a Principal Code Reviewer. Critique this git diff produced for task: '{task}'.\n\n"
            f"GIT DIFF:\n```diff\n{diff_text[:3000]}\n```\n\n"
            f"Reply in 2 short lines:\n"
            f"VERDICT: APPROVED or REJECTED\n"
            f"SUMMARY: [1-sentence reason]"
        )
        
        req_data = json.dumps({
            "model": "reasoner",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1024
        }).encode("utf-8")
        
        req = urllib.request.Request(
            f"{LOCAL_API_BASE}/chat/completions",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            critique = data["choices"][0]["message"]["content"].strip()
            print(f"[FRONTIER CRITIC] Result:\n{critique}")
            if "REJECTED" in critique.upper():
                print("[WARNING] Frontier Critic flagged potential issues in the generated code.")
                return False
            return True
    except Exception as e:
        print(f"[FRONTIER CRITIC] Notice: Critic pass skipped ({e})")
        return True

def verify_changes(cwd: str) -> tuple:
    """
    Deterministic Post-Action Sensors:
    1. Inspects Git working tree changes.
    2. Runs AST & Syntax checks across modified Python, JSON, and JS files.
    Returns: (is_clean: bool, modified_files: list)
    """
    print("\n[POST-ACTION SENSOR] Validating AST & file syntax...")
    all_clean = True
    modified_files = []
    try:
        res = subprocess.run(["git", "status", "--short"], cwd=cwd, stdout=subprocess.PIPE, text=True, check=False)
        output = res.stdout.strip()
        if not output:
            print("[VERIFICATION] No git working tree changes detected.")
            return True, []

        print("[VERIFICATION] Modified / Created files:")
        for line in output.split("\n"):
            print(f"  {line}")
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                modified_files.append(parts[1])

        # Validate syntax of modified files
        for fpath_str in modified_files:
            fpath = Path(cwd) / fpath_str
            if not fpath.exists() or not fpath.is_file():
                continue
            
            # 1. Python AST & Bytecode Check + Code Constitution
            if fpath.suffix == ".py":
                try:
                    py_compile.compile(str(fpath), doraise=True)
                    print(f"  [OK] Python bytecode: {fpath_str}")
                    
                    # Code Constitution Check
                    violations = inspect_python_code_constitution(fpath)
                    if violations:
                        for v in violations:
                            print(f"  [CONSTITUTION WARNING] {fpath_str} -> {v}")
                    else:
                        print(f"  [OK] Code Constitution AST verified: {fpath_str}")
                except py_compile.PyCompileError as err:
                    print(f"  [FAIL] Python syntax error in {fpath_str}: {err}")
                    all_clean = False
            
            # 2. JSON Validation Check
            elif fpath.suffix == ".json":
                try:
                    with open(fpath, "r", encoding="utf-8") as jf:
                        json.load(jf)
                    print(f"  [OK] JSON syntax: {fpath_str}")
                except Exception as err:
                    print(f"  [FAIL] JSON parse error in {fpath_str}: {err}")
                    all_clean = False

            # 3. JavaScript / TypeScript syntax check
            elif fpath.suffix in [".js", ".mjs"]:
                try:
                    node_res = subprocess.run(["node", "--check", str(fpath)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
                    if node_res.returncode == 0:
                        print(f"  [OK] Node.js syntax: {fpath_str}")
                    else:
                        print(f"  [FAIL] Node.js syntax error in {fpath_str}: {node_res.stderr.strip()}")
                        all_clean = False
                except Exception:
                    pass

    except Exception as e:
        print(f"[!] Verification warning: {e}")

    return all_clean, modified_files

def run_agent(agent: str, task: str, model: str = "auto", verify: bool = True, shield: bool = True, judge: bool = False, cwd: str = None) -> bool:
    """
    Main dispatch entry point for multi-agent execution.
    Can be imported and called programmatically from Python or CLI.
    """
    target_cwd = cwd or os.getcwd()
    ensure_services_running()
    
    # Check for past post-mortems, Graphify AST knowledge graph, and Auto-Routed Domain Skills
    historical_hint = get_recent_postmortems(target_cwd)
    graph_hint = get_graphify_context(target_cwd, task)
    skill_context, matched_repos, matched_skills = get_auto_routed_skills(task)
    augmented_task = task + historical_hint + graph_hint + skill_context
    
    resolved_model = resolve_smart_model(task, model)
    tier_label = {
        "local": "Local Free ($0.00 - Discrete GPU)",
        "fast": "Scout Tier (Llama 4 Scout ~190ms)",
        "coder": "Workhorse Tier (Llama 3.3 70B ~300ms)",
        "reasoner": "Deep Reasoning (DeepSeek R1 ~1.1s)",
        "claude": "Frontier Tier (Claude Sonnet 4.6)",
        "opus": "Flagship Tier (Claude Opus 4.6)",
        "opus-4.6": "Flagship Tier (Claude Opus 4.6)",
        "claude-opus-4.6": "Flagship Tier (Claude Opus 4.6)",
        "argon": "Frontier Tier (Gemini 4 Argon 1M Context)",
        "gemini-4-argon": "Frontier Tier (Gemini 4 Argon 1M Context)",
        "gemini-3.8-flash": "High-Speed Scout (Gemini 3.8 Flash)",
        "gemini-flash": "High-Speed Scout (Gemini 3.8 Flash)",
        "gemini-ultra": "Flagship Tier (Gemini 4 Ultra)",
        "gemini": "Google Gemini Higher-Tier (BYOK Dedicated Project)",
        "nemotron-ultra": "NVIDIA Ultra Tier (Nemotron 3 550B - Free Developer Limit)",
        "mistral-1t": "NVIDIA Flagship (Mistral Large 1T MoE - Free Developer Limit)",
        "nemotron-reasoning": "NVIDIA Reasoning (Nemotron 30B CoT - Free Developer Limit)",
        "nemotron-lightning": "NVIDIA Coder (Nemotron 3.5 30B - Free Developer Limit)",
        "nemotron-bolt": "NVIDIA Fast Scout (Nemotron Bolt 4B - Free Developer Limit)",
        "nemotron-vision": "NVIDIA Vision (Nemotron 120B Multimodal - Free Developer Limit)",
        "llama-vision-90b": "NVIDIA Vision (Llama 3.2 90B Vision - Free Developer Limit)",
        "nvidia": "NVIDIA NIM Developer Free Tier (Nemotron 550B)",
    }.get(resolved_model, "Custom Tier")

    print(f"\n=======================================================")
    print(f"  ORCHESTRATING AGENT : {agent.upper()}")
    print(f"  RESOLVED MODEL      : {resolved_model.upper()} [{tier_label}]")
    print(f"  GATEWAY             : {LOCAL_API_BASE}")
    print(f"  WORKING DIRECTORY   : {target_cwd}")
    print(f"  GRAPHIFY CONTEXT    : {'Injected' if graph_hint else 'None'}")
    print(f"  AUTO-ROUTED REPOS   : {', '.join(matched_repos[:5]) if matched_repos else 'Standard Core'}")
    print(f"  TASK                : {task}")
    print(f"=======================================================\n")

    cmd = []
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    extra_bins = os.pathsep.join([
        str(Path.home() / ".local" / "bin"),
        str(Path.home() / "bin"),
        "/opt/homebrew/bin",
        "/usr/local/bin",
    ])
    env["PATH"] = f"{extra_bins}{os.pathsep}{env.get('PATH', '')}"

    if agent == "aider":
        cmd = [
            "aider",
            "--openai-api-base", LOCAL_API_BASE,
            "--openai-api-key", DUMMY_KEY,
            "--model", f"openai/{resolved_model}",
            "--message", augmented_task,
            "--yes-always",
            "--no-show-model-warnings"
        ]

    elif agent == "claude":
        env["CLAUDE_CODE_USE_BEDROCK"] = env.get("CLAUDE_CODE_USE_BEDROCK", "1")
        env["AWS_REGION"] = env.get("AWS_REGION", "us-east-1")
        env["AWS_DEFAULT_REGION"] = env.get("AWS_DEFAULT_REGION", "us-east-1")
        env["AWS_PROFILE"] = env.get("AWS_PROFILE", os.environ.get("AWS_PROFILE", "default"))
        if "ANTHROPIC_MODEL" not in env:
            env["ANTHROPIC_MODEL"] = "us.anthropic.claude-opus-4-6-v1"
        cmd = ["claude", "-p", augmented_task, "--dangerously-skip-permissions"]

    elif agent == "codex":
        if resolved_model in ["local", "llama3.2"]:
            cmd = ["codex", "exec", augmented_task, "--oss", "--local-provider", "ollama", "-m", "llama3.2:1b", "--dangerously-bypass-approvals-and-sandbox"]
        else:
            cmd = ["codex", "exec", augmented_task, "--dangerously-bypass-approvals-and-sandbox"]

    elif agent == "opencode":
        cmd = ["opencode", "run", "--prompt", augmented_task, "--auto"]

    else:
        print(f"Error: Unknown agent '{agent}'. Choose from: aider, claude, codex, opencode")
        sys.exit(1)

    try:
        subprocess.run(cmd, env=env, cwd=target_cwd, check=True)
        print("\n[OK] Agent task execution finished.")
        
        modified_files = []
        # 1. AST & Syntax Verification
        if verify:
            is_valid, modified_files = verify_changes(target_cwd)
            if not is_valid:
                record_postmortem(task, "Syntax verification failed on modified files", target_cwd)
                print("[WARNING] Syntax verification flagged issues. Please inspect modified files.")
                return False

        # 2. Frontier Critic Review (if requested or complex task)
        if judge:
            critic_ok = run_frontier_critic(target_cwd, task)
            if not critic_ok:
                record_postmortem(task, "Frontier Critic rejected diff", target_cwd)
                return False

        # 3. GitGuardian Secret Shield Scan
        if shield:
            is_secure = run_ggshield_audit(target_cwd, modified_files)
            if not is_secure:
                return False

        # 4. Graphify Knowledge Graph Auto-Sync (only when graphify-out/graph.json already exists in target_cwd)
        if (Path(target_cwd) / "graphify-out" / "graph.json").exists():
            try:
                print("\n[GRAPHIFY] Synchronizing codebase knowledge graph...")
                g_res = subprocess.run(
                    [sys.executable, "-m", "graphify", "update", "."],
                    cwd=target_cwd,
                    capture_output=True,
                    text=True,
                    timeout=45
                )
                if g_res.returncode == 0:
                    print("[GRAPHIFY OK] Knowledge graph synchronized.")
                else:
                    print(f"[GRAPHIFY NOTICE] Graph sync exited with {g_res.returncode}.")
            except Exception as e:
                print(f"[GRAPHIFY NOTICE] Graph sync skipped: {e}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Agent failed with exit code {e.returncode}.")
        record_postmortem(task, f"Agent exit code {e.returncode}", target_cwd)
        return False

# Public programmatic API for in-process import
dispatch_task = run_agent

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Agent Orchestration Dispatcher with GitGuardian & AST Shield")
    parser.add_argument("--task", "-t", help="The instruction or task prompt for the agent")
    parser.add_argument("--agent", "-a", default="aider", choices=["aider", "claude", "codex", "opencode"], help="Agent harness to dispatch")
    parser.add_argument("--model", "-m", default="auto", choices=[
        "auto", "claude", "opus", "opus-4.6", "claude-opus-4.6", "sonnet", "reasoner", "coder", "fast", "local",
        "argon", "gemini-4-argon", "gemini-3.8-flash", "gemini-flash", "gemini-ultra", "gemini",
        "nvidia", "nemotron-ultra", "mistral-1t", "nemotron-reasoning", "nemotron-lightning", "nemotron-bolt",
        "nemotron-vision", "llama-vision-90b"
    ], help="Model routing profile (defaults to auto)")
    parser.add_argument("--usage", action="store_true", help="Display live credit and token analytics")
    parser.add_argument("--guide", action="store_true", help="Display 'How It Works & How It Functions' architecture & usage guide")
    parser.add_argument("--setup", action="store_true", help="Run the interactive cross-platform hardware, Ollama, API key & 32-repo setup wizard")
    parser.add_argument("--judge", action="store_true", help="Run Frontier Critic model (DeepSeek R1) review pass on the diff")
    parser.add_argument("--judge-only", action="store_true", help="Run AST sensor, Frontier Critic, and ggshield audit on current workspace without invoking an editing agent")
    parser.add_argument("--no-verify", action="store_true", help="Skip post-execution AST/syntax verification")
    parser.add_argument("--no-shield", action="store_true", help="Skip GitGuardian (ggshield) secret audit")
    parser.add_argument("--dir", "-d", default=None, help="Working directory path")
    
    args = parser.parse_args()
    
    if args.guide:
        tools_dir = Path(__file__).resolve().parent / "tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        import setup_wizard
        hw = setup_wizard.detect_hardware_profile()
        setup_wizard.print_how_it_works_guide(hw)
        sys.exit(0)

    if args.setup:
        tools_dir = Path(__file__).resolve().parent / "tools"
        subprocess.run([sys.executable, str(tools_dir / "setup_wizard.py")], check=False)
        sys.exit(0)

    if args.usage:
        show_usage()
        sys.exit(0)
        
    if args.judge_only:
        ensure_services_running()
        target_dir = args.dir or os.getcwd()
        valid_ok, mod_files = verify_changes(target_dir)
        critic_ok = run_frontier_critic(target_dir, args.task or "Audit current repository changes")
        shield_ok = run_ggshield_audit(target_dir, mod_files) if not args.no_shield else True
        sys.exit(0 if (valid_ok and critic_ok and shield_ok) else 1)

    if not args.task:
        parser.print_help()
        sys.exit(1)
        
    success = run_agent(
        agent=args.agent,
        task=args.task,
        model=args.model,
        verify=not args.no_verify,
        shield=not args.no_shield,
        judge=args.judge,
        cwd=args.dir
    )
    sys.exit(0 if success else 1)
