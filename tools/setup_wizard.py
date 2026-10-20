#!/usr/bin/env python3
"""
tools/setup_wizard.py
Intelligent Hardware-Aware Setup Wizard, Ollama Model Selector, API Key Configurator,
32-Repo Auto-Installer, and Interactive Walkthrough for the Antigravity Workstation.

Works across:
  - Windows PCs (NVIDIA CUDA, AMD Radeon Vulkan, Intel/CPU)
  - macOS (Apple Silicon M1/M2/M3/M4 MacBook, iMac, Mac Mini, Mac Studio & Intel)
  - Linux Workstations & Servers
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
HOME_DIR = Path.home()
WORKSTATION_STATE_DIR = HOME_DIR / ".agent_workstation"
WORKSTATION_STATE_DIR.mkdir(parents=True, exist_ok=True)


def detect_hardware_profile() -> Dict[str, Any]:
    """
    Detects OS, CPU architecture, total RAM (GB), GPU vendor/name, and selects
    the optimal local Ollama LLM model(s) for this specific computer.
    """
    os_name = platform.system()
    arch = platform.machine()
    cpu_cores = os.cpu_count() or 4
    ram_gb = 8.0
    gpu_name = "Integrated / CPU"
    gpu_vendor = "cpu"

    try:
        if os_name == "Windows":
            # Total RAM via PowerShell CIM
            ram_cmd = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize"],
                capture_output=True, text=True, timeout=6, check=False
            )
            if ram_cmd.returncode == 0 and ram_cmd.stdout.strip().isdigit():
                ram_gb = round(int(ram_cmd.stdout.strip()) / (1024 * 1024), 1)

            gpu_cmd = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join ' | '"],
                capture_output=True, text=True, timeout=6, check=False
            )
            if gpu_cmd.returncode == 0 and gpu_cmd.stdout.strip():
                gpu_name = gpu_cmd.stdout.strip()
                g_low = gpu_name.lower()
                if "nvidia" in g_low or "rtx" in g_low or "gtx" in g_low:
                    gpu_vendor = "nvidia_cuda"
                elif "radeon" in g_low or "amd" in g_low:
                    gpu_vendor = "amd_vulkan"
                elif "intel" in g_low or "arc" in g_low:
                    gpu_vendor = "intel"

        elif os_name == "Darwin":
            mem_cmd = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=4, check=False)
            if mem_cmd.returncode == 0 and mem_cmd.stdout.strip().isdigit():
                ram_gb = round(int(mem_cmd.stdout.strip()) / (1024 ** 3), 1)
            chip_cmd = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, timeout=4, check=False)
            chip_str = chip_cmd.stdout.strip() if chip_cmd.returncode == 0 else arch
            if "Apple" in chip_str or arch == "arm64":
                gpu_name = f"{chip_str} Unified Metal GPU"
                gpu_vendor = "apple_metal"
            else:
                gpu_name = f"macOS Intel ({chip_str})"
                gpu_vendor = "intel"

        elif os_name == "Linux":
            if Path("/proc/meminfo").exists():
                for line in Path("/proc/meminfo").read_text().splitlines():
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        ram_gb = round(kb / (1024 * 1024), 1)
                        break
            if shutil.which("nvidia-smi"):
                ns = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True, timeout=4, check=False)
                if ns.returncode == 0 and ns.stdout.strip():
                    gpu_name = ns.stdout.strip().splitlines()[0]
                    gpu_vendor = "nvidia_cuda"
    except Exception:
        pass

    # Select optimal local Ollama models based on detected hardware
    recommended_models: List[str] = ["llama3.2:1b"]
    primary_local_model = "llama3.2:1b"
    tier_summary = "Lightweight Fast Tier (Llama 3.2 1B — 1.3GB)"

    if gpu_vendor == "apple_metal":
        if ram_gb >= 58:
            recommended_models = ["llama3.2:1b", "qwen2.5-coder:32b"]
            primary_local_model = "qwen2.5-coder:32b"
            tier_summary = f"Mac Studio / High Unified Memory ({ram_gb}GB) -> Qwen 2.5 Coder 32B + Llama 3.2 1B"
        elif ram_gb >= 22:
            recommended_models = ["llama3.2:1b", "qwen2.5-coder:14b"]
            primary_local_model = "qwen2.5-coder:14b"
            tier_summary = f"Apple Silicon Pro/Max ({ram_gb}GB) -> Qwen 2.5 Coder 14B + Llama 3.2 1B"
        elif ram_gb >= 14:
            recommended_models = ["llama3.2:1b", "qwen2.5-coder:7b"]
            primary_local_model = "qwen2.5-coder:7b"
            tier_summary = f"Apple Silicon ({ram_gb}GB) -> Qwen 2.5 Coder 7B + Llama 3.2 1B"
    elif gpu_vendor in ("nvidia_cuda", "amd_vulkan"):
        if ram_gb >= 28 and "rtx" in gpu_name.lower():
            recommended_models = ["llama3.2:1b", "qwen2.5-coder:14b"]
            primary_local_model = "qwen2.5-coder:14b"
            tier_summary = f"Discrete GPU Workstation ({gpu_name}, {ram_gb}GB RAM) -> Qwen 2.5 Coder 14B + Llama 3.2 1B"
        elif ram_gb >= 14:
            recommended_models = ["llama3.2:1b", "qwen2.5-coder:7b"]
            primary_local_model = "llama3.2:1b"
            tier_summary = f"Discrete GPU Laptop ({gpu_name}, {ram_gb}GB RAM) -> Llama 3.2 1B (Instant) + Qwen 2.5 Coder 7B"

    profile = {
        "os": os_name,
        "arch": arch,
        "cpu_cores": cpu_cores,
        "ram_gb": ram_gb,
        "gpu_name": gpu_name,
        "gpu_vendor": gpu_vendor,
        "primary_local_model": primary_local_model,
        "recommended_models": recommended_models,
        "tier_summary": tier_summary
    }
    try:
        (WORKSTATION_STATE_DIR / "hardware_profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    except Exception:
        pass
    return profile


def ensure_ollama_and_models(hw: Dict[str, Any], pull_secondary: bool = False) -> None:
    """Starts Ollama daemon if installed and pulls hardware-appropriate models."""
    print("\n" + "=" * 68)
    print("  [STEP 1/4] HARDWARE DETECTION & LOCAL OLLAMA GPU MODEL SETUP")
    print("=" * 68)
    print(f"  * Detected OS / Arch : {hw['os']} ({hw['arch']}) | {hw['cpu_cores']} CPU Cores")
    print(f"  * System Memory (RAM): {hw['ram_gb']} GB")
    print(f"  * GPU / Accelerator  : {hw['gpu_name']} [{hw['gpu_vendor'].upper()}]")
    print(f"  * Optimal LLM Profile: {hw['tier_summary']}")
    print("-" * 68)

    ollama_bin = shutil.which("ollama")
    if not ollama_bin and hw["os"] == "Windows":
        candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        if candidate.exists():
            ollama_bin = str(candidate)

    if not ollama_bin:
        print("  [!] Ollama binary not found in PATH yet. Skipping model pull.")
        return

    # Ensure ollama serve is running
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1.5)
    except Exception:
        print("  [*] Starting local Ollama GPU daemon...")
        try:
            if hw["os"] == "Windows":
                subprocess.Popen([ollama_bin, "serve"], creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen([ollama_bin, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import time
            time.sleep(2.5)
        except Exception as e:
            print(f"  [!] Could not auto-start Ollama: {e}")

    models_to_pull = [hw["recommended_models"][0]]
    if pull_secondary and len(hw["recommended_models"]) > 1:
        models_to_pull = hw["recommended_models"]

    for m in models_to_pull:
        print(f"  [+] Ensuring hardware-matched local model '{m}' is available...")
        subprocess.run([ollama_bin, "pull", m], check=False)


def interactive_api_key_wizard(non_interactive: bool = False) -> None:
    """
    Prompts the user on a new PC/Mac to configure their own API keys or AWS Bedrock profile
    and writes a protected local .env file (never committed to git).
    """
    env_file = REPO_ROOT / ".env"
    print("\n" + "=" * 68)
    print("  [STEP 2/4] API KEYS & CLOUD PROVIDER CONFIGURATION (.env)")
    print("=" * 68)

    if env_file.exists():
        print(f"  [OK] Existing .env configuration found at {env_file}. Preserving keys.")
        return

    if non_interactive or not sys.stdin.isatty():
        example = REPO_ROOT / ".env.example"
        if example.exists():
            shutil.copyfile(example, env_file)
            print(f"  [OK] Initialized default .env from .env.example at {env_file}")
        return

    print("  Configure any cloud providers you want to enable alongside your FREE Local GPU.")
    print("  Press [ENTER] on any prompt to skip that provider.\n")

    openrouter_key = input("  1. OpenRouter API Key (sk-or-v1-... for Claude/DeepSeek/Llama) [Enter to skip]: ").strip()
    nvidia_key = input("  2. NVIDIA NIM API Key (nvapi-... for free/cloud NIM models)    [Enter to skip]: ").strip()
    deepseek_key = input("  3. DeepSeek Direct API Key (sk-... for DeepSeek R1/V3)         [Enter to skip]: ").strip()
    groq_key = input("  4. Groq API Key (gsk_... for ultra-fast LPU inference)         [Enter to skip]: ").strip()
    openai_key = input("  5. OpenAI API Key (sk-proj-... for GPT-4o / o3-mini)           [Enter to skip]: ").strip()
    aws_profile = input("  6. AWS CLI Profile Name (if using AWS Bedrock credits)         [Enter to skip]: ").strip()
    aws_region = "us-east-1"
    if aws_profile:
        aws_region = input("     AWS Bedrock Region [default: us-east-1]: ").strip() or "us-east-1"

    lines = [
        "# Antigravity Autonomous Workstation — Local Environment Configuration",
        "# WARNING: This file is git-ignored. Never commit secrets to version control.",
        "",
        f"AWS_PROFILE={aws_profile}",
        f"AWS_DEFAULT_REGION={aws_region}",
        "",
        f"OPENROUTER_API_KEY={openrouter_key}",
        f"NVIDIA_API_KEY={nvidia_key}",
        f"DEEPSEEK_API_KEY={deepseek_key}",
        f"GROQ_API_KEY={groq_key}",
        f"OPENAI_API_KEY={openai_key}",
        "",
        "OLLAMA_HOST=http://127.0.0.1:11434",
    ]
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if platform.system() != "Windows":
        try:
            os.chmod(env_file, 0o600)
        except Exception:
            pass
    print(f"\n  [OK] Saved credentials securely to {env_file} (git-ignored).")


def sync_all_32_repositories_and_index() -> None:
    """Automatically clones all 32 public curated tool repositories and builds the 1,041-skill index."""
    print("\n" + "=" * 68)
    print("  [STEP 3/4] AUTO-INSTALLING ALL 32 CURATED GITHUB REPOS & SKILL INDEX")
    print("=" * 68)
    manage_py = TOOLS_DIR / "manage_tools.py"
    router_py = TOOLS_DIR / "skill_router.py"

    if manage_py.exists():
        subprocess.run([sys.executable, str(manage_py), "sync"], check=False)
    if router_py.exists():
        subprocess.run([sys.executable, str(router_py), "--index"], check=False)


def configure_global_agent_integrations() -> None:
    """
    Configures global Antigravity Plugin (~/.gemini/config/plugins/antigravity-workstation),
    Claude Code (~/.claude/CLAUDE.md), and Aider (~/.aider.conf.yml) using dynamic paths
    for the current user and computer (zero hardcoded usernames).
    """
    print("\n" + "=" * 68)
    print("  [STEP 4/4] WIRING GLOBAL CROSS-PROJECT AGENT INTEGRATIONS")
    print("=" * 68)

    py_exe = str(sys.executable)
    mcp_py = str((REPO_ROOT / "agent_workstation_mcp.py").resolve())
    router_py = str((TOOLS_DIR / "skill_router.py").resolve())
    hook_py = str((TOOLS_DIR / "pre_invocation_hook.py").resolve())
    orchestrate_py = str((REPO_ROOT / "orchestrate.py").resolve())

    # 1. Global Antigravity Plugin
    plugin_root = HOME_DIR / ".gemini" / "config" / "plugins" / "antigravity-workstation"
    (plugin_root / "rules").mkdir(parents=True, exist_ok=True)
    (plugin_root / "skills" / "workstation-auto-router").mkdir(parents=True, exist_ok=True)

    (plugin_root / "plugin.json").write_text(json.dumps({
        "name": "antigravity-workstation",
        "displayName": "Antigravity Autonomous Workstation & 32-Repo Skill Router",
        "version": "3.4.0",
        "description": "Global autonomous orchestration, 5-tier Smart Credit Guard, Graphify AST sync, GitGuardian secret shield, and automatic zero-name routing across 32 installed developer tool repositories."
    }, indent=2), encoding="utf-8")

    (plugin_root / "mcp_config.json").write_text(json.dumps({
        "mcpServers": {
            "agent_workstation_mcp": {
                "command": py_exe,
                "args": [mcp_py]
            }
        }
    }, indent=2), encoding="utf-8")

    # Register PreInvocation hook so every prompt in Antigravity chat is automatically routed
    hook_cmd = f"\"{py_exe}\" \"{hook_py}\""
    hooks_payload = {
        "workstation-auto-router-hook": {
            "enabled": True,
            "PreInvocation": [
                {
                    "type": "command",
                    "command": hook_cmd,
                    "timeout": 8
                }
            ]
        }
    }
    (plugin_root / "hooks.json").write_text(json.dumps(hooks_payload, indent=2), encoding="utf-8")

    rules_md = f"""# Global Antigravity Pro Autonomous Workstation Rules (All Projects)

These rules apply globally across **EVERY project and workspace** on this machine.

## 1. Mandatory Step 0: Automatic Request Routing & Telemetry Banner
- On **EVERY** prompt in this chat, automatic 5-Tier Model Routing and 32-Repo Skill Routing are active via `PreInvocation` hook and `{router_py}`.
- Always begin your response with a concise 1-line routing status banner:
  `> ⚡ **Auto-Router**: Tier = <tier> (<model>) | Activated Repos = <matched_repos> | Graphify AST = Synced`
- Enforce Principal Engineer standards: **zero placeholders** (`# rest unchanged` / `// TODO` are forbidden), explicit type annotations, defensive error handling, and closed-loop verification (`py_compile` / `tsc` / tests) before completion.

## 2. Zero-Name Automatic Repository & Skill Routing (32 Installed Repos)
- All 32 curated repositories and **456+ indexed `SKILL.md` runbooks** are installed centrally at `{TOOLS_DIR}`.
- **The user NEVER needs to call out repository or skill names in any project.**
- The workstation never installs its files into the user's personal or private project repositories.

## 3. Graphify AST Knowledge Graph & Zero Secret Leakage (`ggshield`)
- When `graphify-out/graph.json` exists in the current workspace, run `graphify query "<question>"` before wide file searches, and `graphify update .` after code edits.
- Never expose or commit API keys, AWS credentials, or tokens. Always scan modified files with `ggshield secret scan path --yes <files>` before `git commit` or `git push`.
"""
    (plugin_root / "rules" / "AGENTS.md").write_text(rules_md, encoding="utf-8")

    skill_md = f"""---
name: workstation-auto-router
description: >-
  Automatically routes any coding, UI/UX, Apple HIG design, web animation, Go (Golang),
  SEO/copywriting, security pentesting, architecture simplification, memory recall,
  time-series forecasting, video/avatar, or multi-agent task to the 32 installed
  workstation repositories and 456+ indexed SKILL.md runbooks without requiring the
  user to name the repository or skill.
---

# Workstation Zero-Name Skill & Repository Auto-Router

1. Query the Zero-Name Skill Router:
   `"{py_exe}" "{router_py}" "<user prompt>"`
2. Or dispatch via Autonomous Orchestrator:
   `"{py_exe}" "{orchestrate_py}" --task "<user prompt>"`
"""
    (plugin_root / "skills" / "workstation-auto-router" / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # Enable plugin in ~/.gemini/config/config.json if present
    cfg_path = HOME_DIR / ".gemini" / "config" / "config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg.setdefault("plugins", {})["antigravity-workstation"] = {"enabled": True}
            cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        except Exception:
            pass

    # 2. Global Claude Code (~/.claude/CLAUDE.md)
    claude_dir = HOME_DIR / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "CLAUDE.md").write_text(
        f"# Global Claude Code Autonomous Workstation Instructions\n\n"
        f"- Unified AI Gateway: `http://127.0.0.1:8000/v1` (5-tier Smart Auto-Router).\n"
        f"- Zero-Name 32-Repo Skill Auto-Router: `\"{py_exe}\" \"{router_py}\" \"<task>\"`\n"
        f"- Always run `ggshield secret scan path --yes <files>` before committing.\n",
        encoding="utf-8"
    )

    # 3. Global Aider (~/.aider.conf.yml)
    (HOME_DIR / ".aider.conf.yml").write_text(
        "openai-api-base: http://127.0.0.1:8000/v1\n"
        "openai-api-key: dummy-local-key\n"
        "model: openai/auto\n"
        "yes-always: true\n"
        "show-model-warnings: false\n",
        encoding="utf-8"
    )
    # 4. Install Git post-merge hook so `git pull` explains how the workstation works & syncs tools
    git_hooks_dir = REPO_ROOT / ".git" / "hooks"
    if git_hooks_dir.exists():
        post_merge = git_hooks_dir / "post-merge"
        post_merge_content = (
            "#!/bin/sh\n"
            "# Auto-triggered after `git pull` to display How It Works guide and sync tools\n"
            f'"{py_exe}" "{REPO_ROOT / "tools" / "setup_wizard.py"}" --guide\n'
        )
        try:
            post_merge.write_text(post_merge_content, encoding="utf-8")
            os.chmod(post_merge, 0o755)
        except Exception:
            pass

    print(f"  [OK] Global Antigravity Plugin + PreInvocation Hook installed at: {plugin_root}")
    print(f"  [OK] Global Claude Code & Aider configs linked to http://127.0.0.1:8000/v1")


def print_how_it_works_guide(hw: Dict[str, Any]) -> None:
    """Prints a clear onboarding walkthrough explaining how the workstation functions."""
    guide = f"""
================================================================================
   ANTIGRAVITY AUTONOMOUS AI WORKSTATION (v3.4) — HOW IT WORKS & QUICK GUIDE
================================================================================

1. HOW THE SYSTEM FUNCTIONS AUTOMATICALLY:
   [User Prompt in Any Project]
        │
        ├──► (A) PreInvocation Auto-Router Hook (`tools/pre_invocation_hook.py`)
        │        Automatically detects your task domain & matches against the
        │        32 installed tool repositories (1,041 SKILL.md files) without
        │        you ever needing to type a repo or skill name.
        │
        ├──► (B) 5-Tier Smart Credit Guard (`http://127.0.0.1:8000/v1`)
        │        • Tier 1 (`local`    - $0.00) : {hw['primary_local_model']} on {hw['gpu_name']}
        │        • Tier 2 (`fast`     - $0.08) : Llama 4 Scout (tests, configs, HTML/CSS)
        │        • Tier 3 (`coder`    - $0.72) : Llama 3.3 70B (full-stack features & APIs)
        │        • Tier 4 (`reasoner` - $1.35) : DeepSeek R1 (debugging & --judge review)
        │        • Tier 5 (`claude`   - $3.00) : Claude Sonnet/Opus 4.5 (architecture)
        │
        └──► (C) Post-Action Deterministic Verification Gate (`orchestrate.py`)
                 • Compiles bytecode (`py_compile` / `node --check`)
                 • Audits Python AST Code Constitution (zero placeholders, no bare except)
                 • Scans modified files with GitGuardian (`ggshield`) so 0 secrets leak

2. LIVE CONTROL PLANE & INTERACTIVE GRAPHIFY VIEWER:
   • Web Control Plane Dashboard : http://127.0.0.1:8000/dashboard
   • Interactive Graphify Viewer : http://127.0.0.1:8000/graphify   (or tap Graphify card!)
   • Graphify Architecture Report: http://127.0.0.1:8000/graphify/report
   • Hardware & Ollama Telemetry : http://127.0.0.1:8000/v1/hardware

3. COMMON COMMANDS (FROM ANY PROJECT FOLDER):
   • Auto-Orchestrate a Task     : python "{REPO_ROOT / 'orchestrate.py'}" -t "Your task"
   • Test 32-Repo Skill Router   : python "{TOOLS_DIR / 'skill_router.py'}" "Your task"
   • Check Token Spend & Savings : python "{REPO_ROOT / 'orchestrate.py'}" --usage
   • Re-run Setup / Change Keys  : python "{TOOLS_DIR / 'setup_wizard.py'}"
================================================================================
"""
    print(guide)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    hw_profile = detect_hardware_profile()

    if "--guide" in args or "--help-guide" in args:
        print_how_it_works_guide(hw_profile)
        sys.exit(0)

    if "--hardware-json" in args:
        print(json.dumps(hw_profile, indent=2))
        sys.exit(0)

    non_interactive = "--non-interactive" in args or "--auto" in args
    ensure_ollama_and_models(hw_profile, pull_secondary=("--pull-all-models" in args))
    interactive_api_key_wizard(non_interactive=non_interactive)
    sync_all_32_repositories_and_index()
    configure_global_agent_integrations()
    print_how_it_works_guide(hw_profile)
