#!/usr/bin/env python3
"""
tools/setup_wizard.py
Zero-Friction, Single-Command Hardware-Aware Setup Wizard, Virtualenv Bootstrapper,
Ollama Model Selector, AWS Bedrock + BYOK API Key Configurator, 32-Repo Parallel Installer,
Global Antigravity / Claude / Aider Integrator, and Gateway Daemon Launcher.

Works across:
  - Windows PCs (NVIDIA CUDA, AMD Radeon Vulkan, Intel/CPU)
  - macOS (Apple Silicon M1/M2/M3/M4 MacBook, iMac, Mac Mini, Mac Studio & Intel)
  - Linux Workstations & Servers
"""

import configparser
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
HOME_DIR = Path.home()
WORKSTATION_STATE_DIR = HOME_DIR / ".agent_workstation"
WORKSTATION_STATE_DIR.mkdir(parents=True, exist_ok=True)


def _augment_path() -> None:
    """Ensures standard user, Homebrew, and uv binary directories are on PATH."""
    extra_dirs = [
        str(HOME_DIR / ".local" / "bin"),
        str(HOME_DIR / "bin"),
        "/opt/homebrew/bin",
        "/usr/local/bin",
    ]
    current_path = os.environ.get("PATH", "")
    missing = [d for d in extra_dirs if d not in current_path and Path(d).exists()]
    if missing:
        os.environ["PATH"] = os.pathsep.join(missing) + os.pathsep + current_path


_augment_path()


def ensure_python_venv_and_deps() -> None:
    """
    Zero-Friction Step 0:
    1. If running on macOS from an external/exFAT volume (/Volumes/...), automatically mirrors
       the engine into ~/.agent-workstation/repo so macOS launchd and .venv symlinks work cleanly.
    2. Ensures a dedicated .venv exists with fastapi, uvicorn, boto3, pydantic, requests,
       mcp<2, graphifyy, and ggshield installed, and re-executes inside .venv if needed.
    """
    global REPO_ROOT, TOOLS_DIR

    if platform.system() == "Darwin" and str(REPO_ROOT).startswith("/Volumes/"):
        central_repo = HOME_DIR / ".agent-workstation" / "repo"
        central_repo.mkdir(parents=True, exist_ok=True)
        for item in REPO_ROOT.iterdir():
            if item.name.startswith("._") or item.name in (".venv", "graphify-out"):
                continue
            dest = central_repo / item.name
            if item.is_dir():
                if item.name == "tools":
                    dest.mkdir(parents=True, exist_ok=True)
                    for tf in item.glob("*.py"):
                        if not tf.name.startswith("._"):
                            shutil.copy2(tf, dest / tf.name)
                elif not dest.exists():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
        REPO_ROOT = central_repo
        TOOLS_DIR = REPO_ROOT / "tools"

    venv_dir = REPO_ROOT / ".venv"
    venv_py = (
        venv_dir / "Scripts" / "python.exe"
        if platform.system() == "Windows"
        else venv_dir / "bin" / "python"
    )

    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
        import boto3  # noqa: F401
        from mcp.server.fastmcp import FastMCP  # noqa: F401
        if venv_py.exists() and Path(sys.executable).resolve() == venv_py.resolve():
            return
    except Exception:
        pass

    if os.environ.get("ANTIGRAVITY_VENV_BOOTSTRAPPED") == "1":
        return

    print("\n" + "=" * 68)
    print("  [STEP 0/5] AUTO-BOOTSTRAPPING PYTHON .VENV & CORE DEPENDENCIES")
    print("=" * 68)

    uv_bin = shutil.which("uv")
    if not venv_py.exists():
        print(f"  [*] Creating virtual environment at {venv_dir} ...")
        if uv_bin:
            subprocess.run([uv_bin, "venv", str(venv_dir)], cwd=str(REPO_ROOT), check=False)
        else:
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], cwd=str(REPO_ROOT), check=False)

    if venv_py.exists():
        pkgs = [
            "fastapi", "uvicorn", "boto3", "pydantic", "requests",
            "mcp<2", "graphifyy", "ggshield"
        ]
        print("  [*] Installing Gateway, FastMCP (<2), Graphify AST, and GitGuardian ggshield...")
        if uv_bin:
            subprocess.run([uv_bin, "pip", "install", "--python", str(venv_py)] + pkgs, cwd=str(REPO_ROOT), check=False)
        else:
            subprocess.run([str(venv_py), "-m", "pip", "install", "--quiet", "--upgrade"] + pkgs, cwd=str(REPO_ROOT), check=False)

        if uv_bin:
            subprocess.run([uv_bin, "tool", "install", "ggshield"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([uv_bin, "tool", "install", "aider-chat"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        env = os.environ.copy()
        env["ANTIGRAVITY_VENV_BOOTSTRAPPED"] = "1"
        res = subprocess.run([str(venv_py), str(TOOLS_DIR / "setup_wizard.py")] + sys.argv[1:], env=env, cwd=str(REPO_ROOT))
        sys.exit(res.returncode)


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
    print("  [STEP 1/5] HARDWARE DETECTION & LOCAL OLLAMA GPU MODEL SETUP")
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
        print("  [!] Ollama binary not found in PATH yet. Skipping local model pull.")
        return

    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1.5)
    except Exception:
        print("  [*] Starting local Ollama GPU daemon...")
        try:
            if hw["os"] == "Windows":
                subprocess.Popen([ollama_bin, "serve"], creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen([ollama_bin, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2.5)
        except Exception as e:
            print(f"  [!] Could not auto-start Ollama: {e}")

    models_to_pull = [hw["recommended_models"][0]]
    if pull_secondary and len(hw["recommended_models"]) > 1:
        models_to_pull = hw["recommended_models"]

    for m in models_to_pull:
        print(f"  [+] Ensuring hardware-matched local model '{m}' is available...")
        subprocess.run([ollama_bin, "pull", m], check=False)


def _open_interactive_tty_stream():
    """
    Opens /dev/tty (macOS/Linux) or CONIN$ (Windows) so interactive API key prompts work
    even when the installer was piped via `curl -fsSL ... | bash`.
    Returns None if no interactive terminal is attached (e.g. headless CI or background hook).
    """
    if sys.stdin and sys.stdin.isatty():
        return sys.stdin
    try:
        if platform.system() == "Windows":
            return open("CONIN$", "r", encoding="utf-8")
        return open("/dev/tty", "r", encoding="utf-8")
    except Exception:
        return None


def _prompt_line(tty_stream, message: str) -> str:
    """Prompts the user using the attached TTY stream and cleans accidental markdown escapes."""
    if tty_stream is None:
        return ""
    try:
        sys.stdout.write(message)
        sys.stdout.flush()
        line = tty_stream.readline()
        if not line:
            return ""
        return line.strip().replace("\\_", "_").strip("\"'")
    except Exception:
        return ""


def auto_detect_and_configure_aws(tty_stream=None, non_interactive: bool = False) -> Tuple[str, str]:
    """
    Checks if the user has AWS credentials in ~/.aws/credentials.
    If found, verifies which Bedrock models are active and optionally creates a dedicated
    least-privilege IAM profile for this workstation (`antigravity-workstation`) so root keys
    aren't used directly.
    Returns (aws_profile, aws_region).
    """
    aws_creds_file = HOME_DIR / ".aws" / "credentials"
    if not aws_creds_file.exists():
        return ("", "us-east-1")

    try:
        import boto3
        session = boto3.Session()
        profiles = session.available_profiles
        if not profiles:
            return ("", "us-east-1")

        # Prefer an existing antigravity* profile if already created
        for p in profiles:
            if p.startswith("antigravity"):
                print(f"  [OK] Auto-detected dedicated AWS Bedrock profile: [{p}] (us-east-1)")
                return (p, "us-east-1")

        base_profile = "default" if "default" in profiles else profiles[0]
        s = boto3.Session(profile_name=base_profile, region_name="us-east-1")
        sts = s.client("sts")
        ident = sts.get_caller_identity()
        arn = ident.get("Arn", "")
        print(f"  [OK] Auto-detected existing AWS login (Profile: [{base_profile}] | Identity: {arn.split(':')[-1]})")

        # If running interactively and logged in as root/admin, offer to create a dedicated workstation IAM profile
        if not non_interactive and tty_stream is not None:
            ans = _prompt_line(
                tty_stream,
                "  * Create a dedicated least-privilege AWS Bedrock IAM key for this computer? [Y/n]: "
            ).lower()
            if ans in ("", "y", "yes"):
                try:
                    iam = s.client("iam")
                    user_name = f"antigravity-{platform.system().lower()}-agent"
                    try:
                        iam.get_user(UserName=user_name)
                    except Exception:
                        iam.create_user(UserName=user_name)
                    iam.attach_user_policy(
                        UserName=user_name,
                        PolicyArn="arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
                    )
                    keys = iam.list_access_keys(UserName=user_name).get("AccessKeyMetadata", [])
                    if len(keys) >= 2:
                        iam.delete_access_key(UserName=user_name, AccessKeyId=keys[0]["AccessKeyId"])
                    new_key = iam.create_access_key(UserName=user_name)["AccessKey"]

                    creds = configparser.RawConfigParser()
                    creds.read(aws_creds_file)
                    prof_name = "antigravity-workstation"
                    if not creds.has_section(prof_name):
                        creds.add_section(prof_name)
                    creds.set(prof_name, "aws_access_key_id", new_key["AccessKeyId"])
                    creds.set(prof_name, "aws_secret_access_key", new_key["SecretAccessKey"])
                    with open(aws_creds_file, "w", encoding="utf-8") as cf:
                        creds.write(cf)
                    if platform.system() != "Windows":
                        os.chmod(aws_creds_file, 0o600)

                    cfg_file = HOME_DIR / ".aws" / "config"
                    cfg = configparser.RawConfigParser()
                    if cfg_file.exists():
                        cfg.read(cfg_file)
                    sec = f"profile {prof_name}"
                    if not cfg.has_section(sec):
                        cfg.add_section(sec)
                    cfg.set(sec, "region", "us-east-1")
                    cfg.set(sec, "output", "json")
                    with open(cfg_file, "w", encoding="utf-8") as cff:
                        cfg.write(cff)

                    print(f"  [OK] Provisioned dedicated IAM profile [{prof_name}] ({new_key['AccessKeyId'][:8]}...****)")
                    return (prof_name, "us-east-1")
                except Exception as exc:
                    print(f"  [!] Using existing profile [{base_profile}] (IAM auto-key skipped: {exc})")

        return (base_profile, "us-east-1")
    except Exception:
        return ("", "us-east-1")


def interactive_api_key_wizard(non_interactive: bool = False, force_reconfigure: bool = False) -> None:
    """
    Prompts the user on a new PC/Mac to configure their own API keys or AWS Bedrock profile
    and writes a protected local .env file (never committed to git).
    Works even when piped via `curl ... | bash` by attaching to /dev/tty or CONIN$.
    """
    env_file = REPO_ROOT / ".env"
    print("\n" + "=" * 68)
    print("  [STEP 2/5] PERSONAL API KEYS & CLOUD PROVIDER SETUP (.env)")
    print("=" * 68)

    # Check if existing .env already has real keys configured
    existing_vals: Dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                existing_vals[k.strip()] = v.strip().strip("\"'")

    has_any_configured_key = any(
        bool(existing_vals.get(k))
        for k in ("AWS_PROFILE", "NVIDIA_API_KEY", "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY")
    )

    if env_file.exists() and has_any_configured_key and not force_reconfigure:
        print(f"  [OK] Active credentials found in {env_file} (protected & git-ignored).")
        print("       Run `python tools/setup_wizard.py --keys` or open http://127.0.0.1:8000/dashboard to update keys anytime.")
        return

    tty_stream = None if non_interactive else _open_interactive_tty_stream()
    detected_aws_profile, detected_aws_region = auto_detect_and_configure_aws(
        tty_stream=tty_stream, non_interactive=(non_interactive or tty_stream is None)
    )

    if non_interactive or tty_stream is None:
        lines = [
            "# Antigravity Autonomous Workstation — Local Environment Configuration",
            "# WARNING: This file is git-ignored. Never commit secrets to version control.",
            "",
            f"AWS_PROFILE={existing_vals.get('AWS_PROFILE') or detected_aws_profile}",
            f"AWS_DEFAULT_REGION={existing_vals.get('AWS_DEFAULT_REGION') or detected_aws_region}",
            "",
            f"OPENROUTER_API_KEY={existing_vals.get('OPENROUTER_API_KEY', '')}",
            f"NVIDIA_API_KEY={existing_vals.get('NVIDIA_API_KEY', '')}",
            f"DEEPSEEK_API_KEY={existing_vals.get('DEEPSEEK_API_KEY', '')}",
            f"GROQ_API_KEY={existing_vals.get('GROQ_API_KEY', '')}",
            f"OPENAI_API_KEY={existing_vals.get('OPENAI_API_KEY', '')}",
            "",
            "OLLAMA_HOST=http://127.0.0.1:11434",
        ]
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        if platform.system() != "Windows":
            try:
                os.chmod(env_file, 0o600)
            except Exception:
                pass
        print(f"  [OK] Initialized local .env at {env_file} (AWS Profile: {detected_aws_profile or 'none'}).")
        print("  [TIP] You can add or change your personal API keys anytime via:")
        print("        1) Web UI : http://127.0.0.1:8000/dashboard (Click 'API Keys & Cloud Setup')")
        print("        2) CLI    : python tools/setup_wizard.py --keys")
        return

    print("  Enter your personal API keys below (stored ONLY in local git-ignored .env).")
    print("  Press [ENTER] on any prompt to skip or keep existing value.\n")

    nvidia_key = _prompt_line(
        tty_stream,
        "  1. NVIDIA NIM API Key (nvapi-... for Nemotron 550B / Llama 3.2) [Enter to skip]: "
    ) or existing_vals.get("NVIDIA_API_KEY", "")
    openrouter_key = _prompt_line(
        tty_stream,
        "  2. OpenRouter API Key (sk-or-v1-... for Claude/DeepSeek/Llama)  [Enter to skip]: "
    ) or existing_vals.get("OPENROUTER_API_KEY", "")
    deepseek_key = _prompt_line(
        tty_stream,
        "  3. DeepSeek Direct API Key (sk-... for DeepSeek R1/V3)          [Enter to skip]: "
    ) or existing_vals.get("DEEPSEEK_API_KEY", "")
    groq_key = _prompt_line(
        tty_stream,
        "  4. Groq API Key (gsk_... for ultra-fast LPU inference)          [Enter to skip]: "
    ) or existing_vals.get("GROQ_API_KEY", "")
    openai_key = _prompt_line(
        tty_stream,
        "  5. OpenAI API Key (sk-proj-... for GPT-4o / o3-mini)            [Enter to skip]: "
    ) or existing_vals.get("OPENAI_API_KEY", "")

    aws_default_hint = detected_aws_profile or existing_vals.get("AWS_PROFILE", "")
    aws_profile = _prompt_line(
        tty_stream,
        f"  6. AWS CLI Profile Name [default: {aws_default_hint or 'skip'}]: "
    ) or aws_default_hint
    aws_region = detected_aws_region or "us-east-1"
    if aws_profile and not detected_aws_profile:
        aws_region = _prompt_line(
            tty_stream,
            "     AWS Bedrock Region [default: us-east-1]: "
        ) or "us-east-1"

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
    print(f"\n  [OK] Saved credentials securely to {env_file} (0600 permissions, git-ignored).")


def sync_all_32_repositories_and_index() -> None:
    """Automatically clones all 32 public curated tool repositories, builds the skill index, and updates Graphify AST."""
    print("\n" + "=" * 68)
    print("  [STEP 3/5] AUTO-INSTALLING ALL 32 CURATED GITHUB REPOS & SKILL INDEX")
    print("=" * 68)
    manage_py = TOOLS_DIR / "manage_tools.py"
    router_py = TOOLS_DIR / "skill_router.py"

    if manage_py.exists():
        subprocess.run([sys.executable, str(manage_py), "sync"], check=False)
    if router_py.exists():
        subprocess.run([sys.executable, str(router_py), "--index"], check=False)

    # Build initial Graphify AST knowledge graph for the workstation repository
    subprocess.run([sys.executable, "-m", "graphify", "antigravity", "install"], cwd=str(REPO_ROOT), check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([sys.executable, "-m", "graphify", "update", "."], cwd=str(REPO_ROOT), check=False)


def configure_global_agent_integrations() -> None:
    """
    Configures global Antigravity Plugin (~/.gemini/config/plugins/antigravity-workstation),
    all 5 bundled skills, global MCP config (~/.gemini/config/mcp_config.json),
    Claude Code (~/.claude/CLAUDE.md), and Aider (~/.aider.conf.yml) using dynamic paths
    for the current user and computer (zero hardcoded usernames).
    """
    print("\n" + "=" * 68)
    print("  [STEP 4/5] WIRING GLOBAL ANTIGRAVITY, MCP, CLAUDE CODE & AIDER")
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
    global_skills_dir = HOME_DIR / ".gemini" / "config" / "skills"
    global_skills_dir.mkdir(parents=True, exist_ok=True)

    (plugin_root / "plugin.json").write_text(json.dumps({
        "name": "antigravity-workstation",
        "displayName": "Antigravity Autonomous Workstation & 32-Repo Skill Router",
        "version": "3.5.0",
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

    # Also merge agent_workstation_mcp into global ~/.gemini/config/mcp_config.json
    global_mcp_cfg = HOME_DIR / ".gemini" / "config" / "mcp_config.json"
    try:
        mcp_data = json.loads(global_mcp_cfg.read_text(encoding="utf-8")) if global_mcp_cfg.exists() else {}
    except Exception:
        mcp_data = {}
    mcp_data.setdefault("mcpServers", {})["agent_workstation_mcp"] = {
        "command": py_exe,
        "args": [mcp_py]
    }
    try:
        global_mcp_cfg.parent.mkdir(parents=True, exist_ok=True)
        global_mcp_cfg.write_text(json.dumps(mcp_data, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass

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
- All 32 curated repositories and **537+ indexed `SKILL.md` runbooks** are installed centrally at `{TOOLS_DIR}`.
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
  workstation repositories and 537+ indexed SKILL.md runbooks without requiring the
  user to name the repository or skill.
---

# Workstation Zero-Name Skill & Repository Auto-Router

1. Query the Zero-Name Skill Router:
   `"{py_exe}" "{router_py}" "<user prompt>"`
2. Or dispatch via Autonomous Orchestrator:
   `"{py_exe}" "{orchestrate_py}" --task "<user prompt>"`
"""
    (plugin_root / "skills" / "workstation-auto-router" / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # Bundle all repository skills into both the global plugin and ~/.gemini/config/skills
    repo_skills_dir = REPO_ROOT / "skills"
    if repo_skills_dir.exists():
        for sdir in repo_skills_dir.iterdir():
            if sdir.is_dir() and not sdir.name.startswith((".", "_")):
                shutil.copytree(sdir, plugin_root / "skills" / sdir.name, dirs_exist_ok=True)
                shutil.copytree(sdir, global_skills_dir / sdir.name, dirs_exist_ok=True)
    shutil.copytree(
        plugin_root / "skills" / "workstation-auto-router",
        global_skills_dir / "workstation-auto-router",
        dirs_exist_ok=True
    )

    # Enable plugin in ~/.gemini/config/config.json
    cfg_path = HOME_DIR / ".gemini" / "config" / "config.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
        cfg.setdefault("plugins", {})["antigravity-workstation"] = {"enabled": True}
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
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

    # 4. Install Git post-merge hook so `git pull` automatically syncs new tools & skills in 1 step
    git_hooks_dir = REPO_ROOT / ".git" / "hooks"
    if git_hooks_dir.exists():
        post_merge = git_hooks_dir / "post-merge"
        post_merge_content = (
            "#!/bin/sh\n"
            "# Auto-triggered after `git pull` to sync tools, skills, and gateway\n"
            f'"{py_exe}" "{REPO_ROOT / "tools" / "setup_wizard.py"}" --auto\n'
        )
        try:
            post_merge.write_text(post_merge_content, encoding="utf-8")
            os.chmod(post_merge, 0o755)
        except Exception:
            pass

    print(f"  [OK] Global Antigravity Plugin + 5 Skills + MCP + PreInvocation Hook installed at: {plugin_root}")
    print(f"  [OK] Global Claude Code & Aider configs linked to http://127.0.0.1:8000/v1")

    # Run Zero-Touch Auto-Configurator for Claude Code, Codex, Aider, OpenDots, and Ollama
    try:
        import auto_configurator
        auto_cfg_res = auto_configurator.run_full_auto_configuration(force=True)
        print("  [OK] Auto-Configurator: Claude Code (Bedrock/Opus 4.6), Codex (ChatGPT), Aider, OpenDots & Ollama configured.")
    except Exception as e:
        print(f"  [Notice] Auto-Configurator status: {e}")


def ensure_gateway_daemon_running() -> None:
    """
    Step 5: Registers and starts the Unified 5-Tier AI Gateway on Port 8000 across
    macOS (launchd), Windows (Startup VBS + background process), and Linux (nohup daemon).
    """
    print("\n" + "=" * 68)
    print("  [STEP 5/5] STARTING UNIFIED 5-TIER AI GATEWAY ON PORT 8000")
    print("=" * 68)

    py_exe = str(sys.executable)
    srv_py = str((REPO_ROOT / "laptop_api_server.py").resolve())
    os_name = platform.system()

    if os_name == "Darwin":
        launch_dir = HOME_DIR / "Library" / "LaunchAgents"
        launch_dir.mkdir(parents=True, exist_ok=True)
        plist_path = launch_dir / "com.antigravity.agent-workstation.plist"
        path_env = os.environ.get("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin")
        plist_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.antigravity.agent-workstation</string>
    <key>ProgramArguments</key>
    <array>
        <string>{py_exe}</string>
        <string>{srv_py}</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{path_env}</string>
    </dict>
    <key>WorkingDirectory</key>
    <string>{REPO_ROOT}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{WORKSTATION_STATE_DIR / 'server.log'}</string>
    <key>StandardErrorPath</key>
    <string>{WORKSTATION_STATE_DIR / 'server.err'}</string>
</dict>
</plist>
"""
        plist_path.write_text(plist_xml, encoding="utf-8")
        subprocess.run(["launchctl", "unload", str(plist_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        subprocess.run(["launchctl", "load", str(plist_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    elif os_name == "Windows":
        ps_script = REPO_ROOT / "start_laptop_api_silent.ps1"
        if ps_script.exists():
            subprocess.run(
                ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
            )
        else:
            subprocess.Popen([py_exe, srv_py], cwd=str(REPO_ROOT), creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        log_file = WORKSTATION_STATE_DIR / "server.log"
        with open(log_file, "a", encoding="utf-8") as lf:
            subprocess.Popen([py_exe, srv_py], cwd=str(REPO_ROOT), stdout=lf, stderr=lf, start_new_session=True)

    # Create ~/.local/bin/orchestrate symlink on macOS/Linux
    if os_name != "Windows":
        local_bin = HOME_DIR / ".local" / "bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        orch_link = local_bin / "orchestrate"
        try:
            if orch_link.exists() or orch_link.is_symlink():
                orch_link.unlink()
            orch_link.symlink_to(REPO_ROOT / "orchestrate.py")
            os.chmod(REPO_ROOT / "orchestrate.py", 0o755)
        except Exception:
            pass

    # Verify /health endpoint comes online
    for _ in range(8):
        time.sleep(0.8)
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "healthy":
                    print(f"  [OK] Gateway ONLINE at http://127.0.0.1:8000 ({data.get('active_models', 0)} active models)")
                    return
        except Exception:
            continue
    print("  [OK] Gateway service registered on http://127.0.0.1:8000")


def print_how_it_works_guide(hw: Dict[str, Any]) -> None:
    """Prints a clear onboarding walkthrough explaining how the workstation functions."""
    guide = f"""
================================================================================
   ANTIGRAVITY AUTONOMOUS AI WORKSTATION (v3.5) — READY FOR ALL PROJECTS
================================================================================

1. ZERO-STEP AUTOMATIC ROUTING ACROSS EVERY PROJECT:
   [User Prompt in Any Project]
        │
        ├──► (A) PreInvocation Auto-Router Hook (`tools/pre_invocation_hook.py`)
        │        Automatically detects your task domain & matches against the
        │        32 installed tool repositories (537+ SKILL.md files) without
        │        you ever needing to type a repo or skill name.
        │
        ├──► (B) 5-Tier Smart Credit Guard (`http://127.0.0.1:8000/v1`)
        │        • Tier 1 (`local`    - $0.00) : {hw['primary_local_model']} on {hw['gpu_name']}
        │        • Tier 2 (`fast`     - $0.08) : Llama 4 Scout / Llama 3.2 Vision
        │        • Tier 3 (`coder`    - $0.72) : Llama 3.3 70B / Nemotron 3.5
        │        • Tier 4 (`reasoner` - $1.35) : DeepSeek R1 / Nemotron Reasoning
        │        • Tier 5 (`claude`   - $3.00) : Claude Sonnet 4.6 / Opus 4.5 / Nemotron 550B
        │
        └──► (C) Post-Action Deterministic Verification Gate (`orchestrate.py`)
                 • Compiles bytecode (`py_compile` / `node --check`)
                 • Audits Python AST Code Constitution (zero placeholders, no bare except)
                 • Scans modified files with GitGuardian (`ggshield`) so 0 secrets leak

2. LIVE CONTROL PLANE, 1-CLICK API KEY SETUP & GRAPHIFY VIEWER:
   • Web Control Plane Dashboard : http://127.0.0.1:8000/dashboard
   • 1-Click API Keys & AWS Setup: Click "🔑 API Keys & Cloud" on /dashboard
   • Interactive Graphify Viewer : http://127.0.0.1:8000/graphify

3. COMMON COMMANDS (FROM ANY PROJECT FOLDER):
   • Update API Keys via CLI     : python "{TOOLS_DIR / 'setup_wizard.py'}" --keys
   • Auto-Orchestrate a Task     : python "{REPO_ROOT / 'orchestrate.py'}" -t "Your task"
   • Test 32-Repo Skill Router   : python "{TOOLS_DIR / 'skill_router.py'}" "Your task"
   • Check Token Spend & Savings : python "{REPO_ROOT / 'orchestrate.py'}" --usage
================================================================================
"""
    print(guide)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]

    if "--hardware-json" in args:
        hw_profile = detect_hardware_profile()
        print(json.dumps(hw_profile, indent=2))
        sys.exit(0)

    if "--guide" in args or "--help-guide" in args:
        hw_profile = detect_hardware_profile()
        print_how_it_works_guide(hw_profile)
        sys.exit(0)

    ensure_python_venv_and_deps()
    hw_profile = detect_hardware_profile()

    if "--keys" in args:
        interactive_api_key_wizard(non_interactive=False, force_reconfigure=True)
        ensure_gateway_daemon_running()
        sys.exit(0)

    non_interactive = "--non-interactive" in args or "--auto" in args
    ensure_ollama_and_models(hw_profile, pull_secondary=("--pull-all-models" in args))
    interactive_api_key_wizard(non_interactive=non_interactive, force_reconfigure=False)
    sync_all_32_repositories_and_index()
    configure_global_agent_integrations()
    ensure_gateway_daemon_running()
    print_how_it_works_guide(hw_profile)
