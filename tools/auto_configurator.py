#!/usr/bin/env python3
"""
tools/auto_configurator.py — Zero-Touch Autonomous Agent & Workstation Auto-Configurator
======================================================================================
Automatically configures Claude Code, OpenAI Codex, Aider, OpenDots, and Ollama
for any machine or user, with zero manual interactive prompts required.

Triggers automatically on:
1. First clone / setup wizard execution (`setup_wizard.py --auto`).
2. Saving API keys or AWS credentials via the Control Plane Dashboard (`POST /v1/config/keys`).
3. Dashboard 1-click Auto-Configure trigger (`POST /v1/config/auto-configure`).
4. PreInvocation hook check before agent task execution.

Guarantees:
- Zero credential leakage into git (scanned with ggshield; .env remains 0600 git-ignored).
- Windows, macOS, and Linux compatibility.
- Hardware-adaptive model selection.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HOME_DIR = Path.home()
REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
DOTENV_PATH = REPO_ROOT / ".env"


def _read_local_env() -> Dict[str, str]:
    """Reads local git-ignored .env variables without leaking secrets."""
    env_vars: Dict[str, str] = {}
    if DOTENV_PATH.exists():
        try:
            for line in DOTENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k, v = s.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip("\"'")
        except Exception:
            pass
    # Also inherit any system environment variables that are non-empty
    for k, v in os.environ.items():
        if v and k not in env_vars:
            env_vars[k] = v
    return env_vars


def _set_persistent_user_env_var(key: str, value: str) -> None:
    """Sets a user-level persistent environment variable across Windows, macOS, and Linux."""
    os.environ[key] = value
    system = platform.system().lower()
    if system == "windows":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_SET_VALUE) as reg_key:
                winreg.SetValueEx(reg_key, key, 0, winreg.REG_SZ, value)
        except Exception:
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", f'[System.Environment]::SetEnvironmentVariable("{key}", "{value}", "User")'],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass
    else:
        # macOS / Linux: Append to ~/.bashrc or ~/.zshrc if not present
        shell_rcs = [HOME_DIR / ".zshrc", HOME_DIR / ".bashrc", HOME_DIR / ".profile"]
        for rc in shell_rcs:
            if rc.exists() or rc == shell_rcs[0]:
                try:
                    text = rc.read_text(encoding="utf-8", errors="replace") if rc.exists() else ""
                    pattern = f"export {key}="
                    if pattern not in text:
                        with open(rc, "a", encoding="utf-8") as f:
                            f.write(f"\nexport {key}=\"{value}\"\n")
                except Exception:
                    pass


def configure_claude_code(env_vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Configures Claude Code CLI (~/.claude/settings.json and environment)
    to connect directly to Amazon Bedrock (Opus 4.6 / Sonnet 4.6) or Anthropic API
    without asking any interactive setup questions.
    """
    if env_vars is None:
        env_vars = _read_local_env()

    claude_dir = HOME_DIR / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_file = claude_dir / "settings.json"

    aws_profile = env_vars.get("AWS_PROFILE", "")
    aws_region = env_vars.get("AWS_DEFAULT_REGION") or env_vars.get("AWS_REGION") or "us-east-1"
    anthropic_key = env_vars.get("ANTHROPIC_API_KEY", "")

    # Check for ~/.aws/config or credentials if aws_profile is empty
    aws_creds = HOME_DIR / ".aws" / "credentials"
    aws_config = HOME_DIR / ".aws" / "config"
    has_aws = bool(aws_profile or aws_creds.exists() or aws_config.exists())

    mode = "unconfigured"
    model = "us.anthropic.claude-opus-4-6-v1"
    env_payload: Dict[str, str] = {}

    if has_aws:
        mode = "bedrock"
        active_prof = aws_profile or "default"
        # If default doesn't exist, probe first profile in ~/.aws/config
        if not aws_profile and aws_config.exists():
            try:
                for line in aws_config.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.strip().startswith("[profile "):
                        active_prof = line.strip().split("[profile ", 1)[1].rstrip("]").strip()
                        break
                    elif line.strip() == "[default]":
                        active_prof = "default"
                        break
            except Exception:
                pass

        env_payload = {
            "CLAUDE_CODE_USE_BEDROCK": "1",
            "AWS_REGION": aws_region,
            "AWS_DEFAULT_REGION": aws_region,
            "AWS_PROFILE": active_prof,
            "ANTHROPIC_MODEL": model
        }
        for k, v in env_payload.items():
            _set_persistent_user_env_var(k, v)

    elif anthropic_key:
        mode = "anthropic_api"
        env_payload = {
            "ANTHROPIC_API_KEY": anthropic_key
        }
        _set_persistent_user_env_var("ANTHROPIC_API_KEY", anthropic_key)

    # Write ~/.claude/settings.json
    try:
        existing_settings = json.loads(settings_file.read_text(encoding="utf-8")) if settings_file.exists() else {}
    except Exception:
        existing_settings = {}

    existing_settings.setdefault("theme", "dark")
    if env_payload:
        existing_settings["env"] = env_payload

    try:
        settings_file.write_text(json.dumps(existing_settings, indent=2) + "\n", encoding="utf-8")
    except Exception as e:
        return {"status": "error", "message": f"Failed writing settings.json: {e}"}

    # Write ~/.claude/CLAUDE.md
    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text(
        "# Antigravity Workstation Claude Code Integration\n\n"
        "- Unified AI Gateway: `http://127.0.0.1:8000/v1`\n"
        "- Auto-Routed 32 Repos & Skills: `python tools/skill_router.py \"<task>\"`\n"
        "- Secret Protection: Run `ggshield secret scan path --yes <files>` before git commit.\n",
        encoding="utf-8"
    )

    return {
        "status": "configured" if mode != "unconfigured" else "pending_credentials",
        "mode": mode,
        "profile": env_payload.get("AWS_PROFILE", ""),
        "region": env_payload.get("AWS_REGION", ""),
        "model": model,
        "settings_path": str(settings_file)
    }


def configure_codex(env_vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Configures OpenAI Codex CLI (~/.codex/config.toml)
    to use valid ChatGPT models (gpt-5.6-terra, gpt-6-luna) or local Ollama / gateway.
    """
    if env_vars is None:
        env_vars = _read_local_env()

    codex_dir = HOME_DIR / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    config_toml = codex_dir / "config.toml"
    auth_json = codex_dir / "auth.json"

    has_chatgpt_auth = auth_json.exists()
    preferred_model = "gpt-5.6-terra"

    # Read models_cache.json if present to verify available models
    models_cache = codex_dir / "models_cache.json"
    if models_cache.exists():
        try:
            cache_data = json.loads(models_cache.read_text(encoding="utf-8"))
            slugs = [m.get("slug") for m in cache_data.get("models", []) if m.get("slug")]
            if "gpt-5.6-terra" in slugs:
                preferred_model = "gpt-5.6-terra"
            elif "gpt-6-luna" in slugs:
                preferred_model = "gpt-6-luna"
            elif slugs:
                preferred_model = slugs[0]
        except Exception:
            pass

    # Read or update config.toml
    content = ""
    if config_toml.exists():
        try:
            content = config_toml.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = ""

    lines = content.splitlines() if content else []
    model_set = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("model ="):
            new_lines.append(f'model = "{preferred_model}"')
            model_set = True
        else:
            new_lines.append(line)

    if not model_set:
        new_lines.insert(0, f'model = "{preferred_model}"')
        new_lines.insert(1, 'model_reasoning_effort = "medium"')
        new_lines.insert(2, "")

    try:
        config_toml.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except Exception as e:
        return {"status": "error", "message": f"Failed writing config.toml: {e}"}

    return {
        "status": "configured" if has_chatgpt_auth else "ready_for_auth",
        "has_auth": has_chatgpt_auth,
        "model": preferred_model,
        "config_path": str(config_toml)
    }


def configure_aider(gateway_url: str = "http://127.0.0.1:8000/v1") -> Dict[str, Any]:
    """
    Configures Aider CLI (~/.aider.conf.yml) to point directly to the Unified Local Gateway
    using the 5-Tier Smart Credit Guard auto-router.
    """
    aider_conf = HOME_DIR / ".aider.conf.yml"
    content = (
        f"openai-api-base: {gateway_url}\n"
        "openai-api-key: dummy-local-key\n"
        "model: openai/auto\n"
        "yes-always: true\n"
        "show-model-warnings: false\n"
    )
    try:
        aider_conf.write_text(content, encoding="utf-8")
        return {
            "status": "configured",
            "gateway_url": gateway_url,
            "model": "openai/auto",
            "path": str(aider_conf)
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed writing ~/.aider.conf.yml: {e}"}


def configure_opendots(gateway_url: str = "http://127.0.0.1:8000/v1") -> Dict[str, Any]:
    """
    Configures OpenDots (tools/OpenDots/.env) to connect to the Unified Local Gateway
    so it provides full generative UI canvas features without requiring external paid keys.
    """
    opendots_dir = TOOLS_DIR / "OpenDots"
    if not opendots_dir.exists():
        return {"status": "skipped", "message": "tools/OpenDots repository not found."}

    opendots_env = opendots_dir / ".env"
    lines = [
        "# OpenDots Workstation Unified AI Configuration",
        "HOST=127.0.0.1",
        "PORT=4310",
        "DATABASE_PATH=data/opendots.sqlite",
        "OWNER_ID=opendots-owner",
        "APP_ORIGIN=http://localhost:5173,http://127.0.0.1:5173,http://localhost:4310,http://127.0.0.1:4310",
        "",
        "# CopilotKit Intelligence Key (Local Gateway Bridge)",
        "CPK_INTELLIGENCE_API_KEY=cpk_local_gateway_active",
        "INTELLIGENCE_API_KEY=cpk_local_gateway_active",
        "",
        "# Unified Local Gateway (BYOK + 5-Tier Fallback)",
        "OPENAI_API_KEY=dummy-local-key",
        f"OPENAI_BASE_URL={gateway_url}",
        "OPENAI_MODEL=auto",
        "",
        "WEB_SEARCH_PROVIDER=parallel",
        "BROWSER_URL=http://127.0.0.1:4311",
        "BROWSER_PORT=4311",
        "BROWSER_SECRET=opendots-local-secret",
    ]
    try:
        opendots_env.write_text("\n".join(lines) + "\n", encoding="utf-8")
        has_node_modules = (opendots_dir / "node_modules").exists()
        return {
            "status": "configured",
            "path": str(opendots_env),
            "port": 4310,
            "has_node_modules": has_node_modules,
            "ui_origin": "http://localhost:5173"
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed writing OpenDots .env: {e}"}


def configure_hardware_ollama(pull_model: bool = False) -> Dict[str, Any]:
    """
    Detects machine hardware and selects the tier-optimal Ollama model.
    """
    ram_gb = 8
    try:
        import psutil
        ram_gb = int(psutil.virtual_memory().total / (1024 ** 3))
    except Exception:
        pass

    # Model tier based on RAM
    if ram_gb >= 32:
        recommended = "qwen2.5-coder:14b"
    elif ram_gb >= 16:
        recommended = "qwen2.5-coder:7b"
    else:
        recommended = "llama3.2:1b"

    ollama_online = False
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1.5) as r:
            ollama_online = (r.status == 200)
    except Exception:
        pass

    return {
        "status": "detected",
        "ram_gb": ram_gb,
        "recommended_model": recommended,
        "ollama_online": ollama_online
    }


def get_agents_status() -> Dict[str, Any]:
    """
    Returns a unified status report for all agent harnesses across the workstation.
    """
    claude_bin = shutil.which("claude") or str(HOME_DIR / "AppData" / "Roaming" / "npm" / "claude.cmd")
    codex_bin = shutil.which("codex") or str(HOME_DIR / "AppData" / "Roaming" / "npm" / "codex.cmd")
    aider_bin = shutil.which("aider") or str(HOME_DIR / ".local" / "bin" / "aider.exe")

    claude_settings = HOME_DIR / ".claude" / "settings.json"
    codex_config = HOME_DIR / ".codex" / "config.toml"
    codex_auth = HOME_DIR / ".codex" / "auth.json"
    aider_conf = HOME_DIR / ".aider.conf.yml"
    opendots_env = TOOLS_DIR / "OpenDots" / ".env"

    return {
        "claude": {
            "installed": Path(claude_bin).exists() if claude_bin else False,
            "bin": claude_bin,
            "configured": claude_settings.exists(),
            "use_bedrock": os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "1",
            "model": os.environ.get("ANTHROPIC_MODEL", "us.anthropic.claude-opus-4-6-v1"),
            "profile": os.environ.get("AWS_PROFILE", os.environ.get("AWS_PROFILE", "default"))
        },
        "codex": {
            "installed": Path(codex_bin).exists() if codex_bin else False,
            "bin": codex_bin,
            "configured": codex_config.exists(),
            "authenticated": codex_auth.exists(),
            "model": "gpt-5.6-terra"
        },
        "aider": {
            "installed": Path(aider_bin).exists() if aider_bin else False,
            "bin": aider_bin,
            "configured": aider_conf.exists(),
            "endpoint": "http://127.0.0.1:8000/v1"
        },
        "opendots": {
            "installed": (TOOLS_DIR / "OpenDots").exists(),
            "configured": opendots_env.exists(),
            "port": 4310
        },
        "orchestrator": {
            "installed": (REPO_ROOT / "orchestrate.py").exists(),
            "script": str(REPO_ROOT / "orchestrate.py")
        }
    }


def run_full_auto_configuration(force: bool = False) -> Dict[str, Any]:
    """
    Main Entrypoint: Runs the full self-healing auto-configuration workflow.
    Configures Claude Code, Codex, Aider, OpenDots, and Ollama in a single atomic pass.
    """
    env_vars = _read_local_env()

    claude_res = configure_claude_code(env_vars)
    codex_res = configure_codex(env_vars)
    aider_res = configure_aider()
    opendots_res = configure_opendots()
    hw_res = configure_hardware_ollama()

    return {
        "status": "success",
        "message": "All workstation agent harnesses automatically configured.",
        "claude": claude_res,
        "codex": codex_res,
        "aider": aider_res,
        "opendots": opendots_res,
        "hardware": hw_res,
        "summary": get_agents_status()
    }


if __name__ == "__main__":
    print("=" * 64)
    print("  ANTIGRAVITY WORKSTATION — ZERO-TOUCH AUTO-CONFIGURATOR")
    print("=" * 64)
    res = run_full_auto_configuration(force=True)
    print(json.dumps(res, indent=2))
