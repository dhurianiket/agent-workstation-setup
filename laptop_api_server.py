"""
Laptop Unified AI Agent & Model API Server (v2.1 - Multi-Provider BYOK Edition)
Advanced features:
- Multi-Provider Support (Bring Your Own Key):
    * AWS Bedrock (Claude 4.5, DeepSeek R1, Llama 3.3 via AWS Startup credits or IAM)
    * OpenRouter (OPENROUTER_API_KEY - 100+ models with 1 key)
    * NVIDIA NIM (NVIDIA_API_KEY - Llama 3.3 70B, DeepSeek R1)
    * DeepSeek Direct (DEEPSEEK_API_KEY - deepseek-reasoner, deepseek-chat)
    * Groq Direct (GROQ_API_KEY - ultra-fast Llama 3.3, DeepSeek R1 distill)
    * OpenAI Direct (OPENAI_API_KEY - o3-mini, gpt-4o, gpt-4o-mini)
    * Local Ollama GPU Engine (AMD Radeon / NVIDIA / Apple Metal - 100% Free & Offline)
- Multi-tier Cost Protection & Zero-Downtime Auto-Fallback:
    * Automatically cascades down models and providers if credits deplete or limits hit.
- Built-in High-Craft Engineering Directives:
    * Enforces complete implementations, zero placeholders, strict typing, and defensive coding.
- Real-Time Credit & Usage Analytics:
    * Persists token usage and estimated spend in ~/.agent_workstation/usage_stats.json.
- Full OpenAI-compatible /v1/chat/completions (with SSE streaming) and /v1/models endpoints.
"""

import os
import re
import sys
import time
import json
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
from botocore.exceptions import ClientError
import urllib.request
from dotenv import load_dotenv

# Load .env immediately
load_dotenv()
_env_path = Path(__file__).resolve().parent / '.env'
if _env_path.exists():
    load_dotenv(_env_path)

app = FastAPI(title="Laptop Unified AI API - Multi-Provider BYOK", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Usage & Config Directory
STATS_DIR = Path.home() / ".agent_workstation"
STATS_DIR.mkdir(parents=True, exist_ok=True)
STATS_FILE = STATS_DIR / "usage_stats.json"

# Load auto_configurator from tools
TOOLS_DIR = Path(__file__).resolve().parent / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
try:
    import auto_configurator
except Exception:
    auto_configurator = None


# Load local .env if present (Zero-leakage local configuration)
def load_local_env(override: bool = False):
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("\"'")
                    if k and (override or k not in os.environ):
                        os.environ[k] = v

load_local_env(override=True)

# Pricing per 1,000,000 tokens (USD)
PRICING_PER_M = {
    "us.anthropic.claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "us.anthropic.claude-opus-4-6-v1": {"input": 15.00, "output": 75.00},
    "us.anthropic.claude-opus-4-6-v1:0": {"input": 15.00, "output": 75.00},
    "us.anthropic.claude-opus-4-5-20251101-v1:0": {"input": 15.00, "output": 75.00},
    "us.anthropic.claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0": {"input": 3.00, "output": 15.00},
    "us.anthropic.claude-haiku-4-5-20251001-v1:0": {"input": 0.80, "output": 4.00},
    "us.deepseek.r1-v1:0": {"input": 1.35, "output": 2.19},
    "us.meta.llama3-3-70b-instruct-v1:0": {"input": 0.72, "output": 0.72},
    "us.meta.llama4-maverick-17b-instruct-v1:0": {"input": 0.20, "output": 0.60},
    "us.meta.llama4-scout-17b-instruct-v1:0": {"input": 0.08, "output": 0.30},
    "us.mistral.pixtral-large-2502-v1:0": {"input": 2.00, "output": 6.00},
    "us.amazon.nova-pro-v1:0": {"input": 0.80, "output": 3.20},
    "us.amazon.nova-2-lite-v1:0": {"input": 0.06, "output": 0.24},
    "us.amazon.nova-lite-v1:0": {"input": 0.06, "output": 0.24},
    "us.amazon.nova-micro-v1:0": {"input": 0.035, "output": 0.14},
    "openrouter": {"input": 1.00, "output": 3.00},
    "nvidia": {"input": 0.50, "output": 1.00},
    "deepseek": {"input": 0.27, "output": 1.10},
    "groq": {"input": 0.59, "output": 0.79},
    "openai": {"input": 2.50, "output": 10.00},
    "llama3.2:1b": {"input": 0.00, "output": 0.00},
}

# Auto-fallback chain: If a model fails or credits deplete, cascade down gracefully
FALLBACK_CHAINS = {
    "opus": ["claude", "reasoner", "coder", "fast", "local"],
    "claude-opus": ["claude", "reasoner", "coder", "fast", "local"],
    "claude": ["reasoner", "coder", "fast", "local"],
    "sonnet": ["reasoner", "coder", "fast", "local"],
    "reasoner": ["coder", "fast", "local"],
    "deepseek-r1": ["coder", "fast", "local"],
    "coder": ["fast", "local"],
    "llama-3.3-70b": ["fast", "local"],
    "fast": ["local"],
    "llama-4-scout": ["local"],
}

# Production Engineering Quality Directive injected into system prompt
QUALITY_DIRECTIVE = (
    "You are a Principal Software Engineer. Follow these strict rules for all code:\n"
    "1. Complete Implementation: Deliver 100% complete, drop-in replacement code. NEVER use placeholders "
    "like '// rest of code unchanged' or '// TODO'.\n"
    "2. Robust & Defensive: Handle all edge cases (null, empty, network timeouts). Add explicit types and error boundaries.\n"
    "3. Clean Architecture: Modular design, pure functions where possible, and zero security vulnerabilities.\n"
    "4. Concise Explanations: Be ultra-concise in text, prioritizing working code and exact diffs."
)

# Initialize AWS Bedrock client with profile & region flexibility
aws_profile = os.environ.get("AWS_PROFILE") or os.environ.get("AWS_DEFAULT_PROFILE")
aws_region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

try:
    if aws_profile:
        session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    else:
        session = boto3.Session(region_name=aws_region)
    if session.get_credentials() is not None:
        bedrock = session.client("bedrock-runtime")
    else:
        bedrock = None
except Exception as e:
    print(f"Notice: Bedrock not initialized ({e}). Server will route to BYOK providers or local Ollama.")
    bedrock = None

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

# BYOK Provider Definitions
BYOK_PROVIDERS = {
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key": os.environ.get("OPENROUTER_API_KEY"),
        "headers": {"HTTP-Referer": "http://localhost:8000", "X-Title": "Agent Workstation"},
        "models": {
            "claude": "anthropic/claude-3.5-sonnet",
            "claude-sonnet": "anthropic/claude-3.5-sonnet",
            "opus": "anthropic/claude-3-opus",
            "reasoner": "deepseek/deepseek-r1",
            "deepseek-r1": "deepseek/deepseek-r1",
            "coder": "meta-llama/llama-3.3-70b-instruct",
            "llama-3.3-70b": "meta-llama/llama-3.3-70b-instruct",
            "fast": "meta-llama/llama-3.1-8b-instruct",
            "llama-4-scout": "meta-llama/llama-3.1-8b-instruct",
        }
    },
    "nvidia": {
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "key": os.environ.get("NVIDIA_API_KEY"),
        "headers": {},
        "models": {
            "opus": "nvidia/nemotron-3-ultra-550b-a55b",
            "claude": "nvidia/nemotron-3-ultra-550b-a55b",
            "sonnet": "nvidia/nemotron-3-ultra-550b-a55b",
            "reasoner": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            "deepseek-r1": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            "coder": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "llama-3.3-70b": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "fast": "meta/llama-3.2-11b-vision-instruct",
            "llama-4-scout": "meta/llama-3.2-11b-vision-instruct",
            "nvidia-default": "meta/llama-3.2-11b-vision-instruct",
            "nemotron-ultra": "nvidia/nemotron-3-ultra-550b-a55b",
            "nemotron-super": "nvidia/nemotron-3-super-120b-a12b",
            "nemotron-reasoning": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            "nemotron-lightning": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "llama-3.2-vision": "meta/llama-3.2-11b-vision-instruct",
            "gemma-4-31b": "google/gemma-4-31b-it",
            "meta/llama-3.2-11b-vision-instruct": "meta/llama-3.2-11b-vision-instruct",
            "nvidia/nemotron-3-ultra-550b-a55b": "nvidia/nemotron-3-ultra-550b-a55b",
            "nvidia/nemotron-3-super-120b-a12b": "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            "nvidia/nemotron-3.5-lightning-30b-a3b": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "google/gemma-4-31b-it": "google/gemma-4-31b-it",
            "nvidia/nemotron-parse-2.0": "nvidia/nemotron-parse-2.0",
            "nvidia/riva-translate-4b-instruct-v2": "nvidia/riva-translate-4b-instruct-v2",
            "nvidia/llama-3.1-nemotron-safety-guard-8b-v3": "nvidia/llama-3.1-nemotron-safety-guard-8b-v3",
        }
    },
    "deepseek": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "key": os.environ.get("DEEPSEEK_API_KEY"),
        "headers": {},
        "models": {
            "reasoner": "deepseek-reasoner",
            "deepseek-r1": "deepseek-reasoner",
            "coder": "deepseek-chat",
            "fast": "deepseek-chat"
        }
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": os.environ.get("GROQ_API_KEY"),
        "headers": {},
        "models": {
            "coder": "llama-3.3-70b-versatile",
            "reasoner": "deepseek-r1-distill-llama-70b",
            "fast": "llama-3.1-8b-instant"
        }
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "key": os.environ.get("OPENAI_API_KEY"),
        "headers": {},
        "models": {
            "reasoner": "o3-mini",
            "coder": "gpt-4o",
            "fast": "gpt-4o-mini"
        }
    }
}

MODEL_MAP = {
    # Smart 5-Tier Auto Router
    "auto": {"provider": "router", "id": "smart-5-tier-router", "tier": "auto_router"},
    # Frontier Claude (Bedrock)
    "claude": {"provider": "bedrock", "id": "us.anthropic.claude-sonnet-4-6", "tier": "frontier"},
    "claude-sonnet": {"provider": "bedrock", "id": "us.anthropic.claude-sonnet-4-6", "tier": "frontier"},
    "claude-sonnet-4.6": {"provider": "bedrock", "id": "us.anthropic.claude-sonnet-4-6", "tier": "frontier"},
    "claude-sonnet-4.5": {"provider": "bedrock", "id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0", "tier": "frontier"},
    "sonnet": {"provider": "bedrock", "id": "us.anthropic.claude-sonnet-4-6", "tier": "frontier"},
    "opus": {"provider": "bedrock", "id": "us.anthropic.claude-opus-4-6-v1", "tier": "frontier"},
    "claude-opus": {"provider": "bedrock", "id": "us.anthropic.claude-opus-4-6-v1", "tier": "frontier"},
    "claude-opus-4.6": {"provider": "bedrock", "id": "us.anthropic.claude-opus-4-6-v1", "tier": "frontier"},
    "claude-opus-4.5": {"provider": "bedrock", "id": "us.anthropic.claude-opus-4-5-20251101-v1:0", "tier": "frontier"},
    "haiku": {"provider": "bedrock", "id": "us.anthropic.claude-haiku-4-5-20251001-v1:0", "tier": "scout"},
    "claude-haiku-4.5": {"provider": "bedrock", "id": "us.anthropic.claude-haiku-4-5-20251001-v1:0", "tier": "scout"},
    # Deep Reasoning
    "reasoner": {"provider": "bedrock", "id": "us.deepseek.r1-v1:0", "tier": "reasoning"},
    "deepseek-r1": {"provider": "bedrock", "id": "us.deepseek.r1-v1:0", "tier": "reasoning"},
    # Standard Full-Stack Coding (Cost Efficient)
    "coder": {"provider": "bedrock", "id": "us.meta.llama3-3-70b-instruct-v1:0", "tier": "coding"},
    "llama-3.3-70b": {"provider": "bedrock", "id": "us.meta.llama3-3-70b-instruct-v1:0", "tier": "coding"},
    "llama-4-maverick": {"provider": "bedrock", "id": "us.meta.llama4-maverick-17b-instruct-v1:0", "tier": "coding"},
    # Ultra-Fast / Budget Scout
    "fast": {"provider": "bedrock", "id": "us.meta.llama4-scout-17b-instruct-v1:0", "tier": "scout"},
    "llama-4-scout": {"provider": "bedrock", "id": "us.meta.llama4-scout-17b-instruct-v1:0", "tier": "scout"},
    # Multimodal & Vision
    "pixtral": {"provider": "bedrock", "id": "us.mistral.pixtral-large-2502-v1:0", "tier": "multimodal"},
    "multimodal": {"provider": "bedrock", "id": "us.amazon.nova-pro-v1:0", "tier": "multimodal"},
    "nova-pro": {"provider": "bedrock", "id": "us.amazon.nova-pro-v1:0", "tier": "general"},
    "nova-2-lite": {"provider": "bedrock", "id": "us.amazon.nova-2-lite-v1:0", "tier": "scout"},
    "nova-lite": {"provider": "bedrock", "id": "us.amazon.nova-lite-v1:0", "tier": "scout"},
    "nova-micro": {"provider": "bedrock", "id": "us.amazon.nova-micro-v1:0", "tier": "micro"},
    # NVIDIA NIM Direct Models (Aegis AI Verified)
    "nvidia-default": {"provider": "nvidia", "id": "meta/llama-3.2-11b-vision-instruct", "tier": "nvidia_nim"},
    "nemotron-ultra": {"provider": "nvidia", "id": "nvidia/nemotron-3-ultra-550b-a55b", "tier": "nvidia_nim"},
    "nemotron-super": {"provider": "nvidia", "id": "nvidia/nemotron-3-super-120b-a12b", "tier": "nvidia_nim"},
    "nemotron-reasoning": {"provider": "nvidia", "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "tier": "nvidia_nim"},
    "nemotron-lightning": {"provider": "nvidia", "id": "nvidia/nemotron-3.5-lightning-30b-a3b", "tier": "nvidia_nim"},
    "llama-3.2-vision": {"provider": "nvidia", "id": "meta/llama-3.2-11b-vision-instruct", "tier": "nvidia_nim"},
    "gemma-4-31b": {"provider": "nvidia", "id": "google/gemma-4-31b-it", "tier": "nvidia_nim"},
    "meta/llama-3.2-11b-vision-instruct": {"provider": "nvidia", "id": "meta/llama-3.2-11b-vision-instruct", "tier": "nvidia_nim"},
    "nvidia/nemotron-3-ultra-550b-a55b": {"provider": "nvidia", "id": "nvidia/nemotron-3-ultra-550b-a55b", "tier": "nvidia_nim"},
    "nvidia/nemotron-3-super-120b-a12b": {"provider": "nvidia", "id": "nvidia/nemotron-3-super-120b-a12b", "tier": "nvidia_nim"},
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning": {"provider": "nvidia", "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "tier": "nvidia_nim"},
    "nvidia/nemotron-3.5-lightning-30b-a3b": {"provider": "nvidia", "id": "nvidia/nemotron-3.5-lightning-30b-a3b", "tier": "nvidia_nim"},
    "google/gemma-4-31b-it": {"provider": "nvidia", "id": "google/gemma-4-31b-it", "tier": "nvidia_nim"},
    "nvidia/nemotron-parse-2.0": {"provider": "nvidia", "id": "nvidia/nemotron-parse-2.0", "tier": "nvidia_nim"},
    "nvidia/riva-translate-4b-instruct-v2": {"provider": "nvidia", "id": "nvidia/riva-translate-4b-instruct-v2", "tier": "nvidia_nim"},
    "nvidia/llama-3.1-nemotron-safety-guard-8b-v3": {"provider": "nvidia", "id": "nvidia/llama-3.1-nemotron-safety-guard-8b-v3", "tier": "nvidia_nim"},
    # Local GPU Models (Ollama - Free)
    "local": {"provider": "ollama", "id": "llama3.2:1b", "tier": "local_free"},
    "llama3.2:1b": {"provider": "ollama", "id": "llama3.2:1b", "tier": "local_free"},
    "llama3.2": {"provider": "ollama", "id": "llama3.2:1b", "tier": "local_free"},
}

def record_usage(model_id: str, prompt_tokens: int, completion_tokens: int):
    """Logs token consumption and estimates cost to track credit expenditure."""
    try:
        data = {}
        if STATS_FILE.exists():
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        totals = data.get("totals", {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "estimated_usd": 0.0})
        by_model = data.get("by_model", {})
        
        rates = PRICING_PER_M.get(model_id, {"input": 1.0, "output": 2.0})
        cost = (prompt_tokens * rates["input"] / 1_000_000) + (completion_tokens * rates["output"] / 1_000_000)
        
        totals["requests"] += 1
        totals["prompt_tokens"] += prompt_tokens
        totals["completion_tokens"] += completion_tokens
        totals["estimated_usd"] = round(totals["estimated_usd"] + cost, 5)
        
        m_entry = by_model.get(model_id, {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "estimated_usd": 0.0})
        m_entry["requests"] += 1
        m_entry["prompt_tokens"] += prompt_tokens
        m_entry["completion_tokens"] += completion_tokens
        m_entry["estimated_usd"] = round(m_entry["estimated_usd"] + cost, 5)
        by_model[model_id] = m_entry
        
        data["totals"] = totals
        data["by_model"] = by_model
        data["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Usage logging error: {e}")

class ChatMessage(BaseModel):
    role: str
    content: Any

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    stream: Optional[bool] = False
    enhance_quality: Optional[bool] = True

class AgentChatRequest(BaseModel):
    agent: str  # claude, codex, aider, opendots, orchestrator
    message: str
    model: Optional[str] = "auto"
    mode: Optional[str] = "design"  # design, code, cli
    working_dir: Optional[str] = None

class OrchestrationRequest(BaseModel):
    task: str
    agent: Optional[str] = "aider"  # aider, codex, claude, opencode
    model: Optional[str] = "auto"   # auto, fast, coder, reasoner, claude, local
    working_dir: Optional[str] = None
    verify: Optional[bool] = True


class ApiKeysUpdateRequest(BaseModel):
    nvidia_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_region: Optional[str] = None


def reload_runtime_credentials() -> None:
    """Hot-reloads .env into os.environ, BYOK_PROVIDERS, and AWS Bedrock client without restarting."""
    global bedrock, aws_profile, aws_region
    load_local_env(override=True)
    aws_profile = os.environ.get("AWS_PROFILE", "").strip()
    aws_region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1").strip() or "us-east-1"
    try:
        if aws_profile:
            sess = boto3.Session(profile_name=aws_profile, region_name=aws_region)
        else:
            sess = boto3.Session(region_name=aws_region)
        # Only mark bedrock active if credentials exist in the session
        if sess.get_credentials() is not None:
            bedrock = sess.client("bedrock-runtime")
        else:
            bedrock = None
    except Exception:
        bedrock = None

    BYOK_PROVIDERS["openrouter"]["key"] = os.environ.get("OPENROUTER_API_KEY", "").strip() or None
    BYOK_PROVIDERS["nvidia"]["key"] = os.environ.get("NVIDIA_API_KEY", "").strip() or None
    BYOK_PROVIDERS["deepseek"]["key"] = os.environ.get("DEEPSEEK_API_KEY", "").strip() or None
    BYOK_PROVIDERS["groq"]["key"] = os.environ.get("GROQ_API_KEY", "").strip() or None
    BYOK_PROVIDERS["openai"]["key"] = os.environ.get("OPENAI_API_KEY", "").strip() or None


def _mask_secret(val: Optional[str]) -> str:
    if not val:
        return ""
    s = val.strip()
    if len(s) <= 10:
        return "****"
    return f"{s[:8]}...****"

@app.get("/")
def root(req: Request):
    accept = req.headers.get("accept", "")
    if "text/html" in accept:
        return dashboard()
    return {
        "status": "online",
        "version": "2.2.0",
        "description": "Antigravity Autonomous Workstation Unified AI Gateway (BYOK + 5-Tier Fallback)",
        "endpoints": ["/dashboard", "/health", "/v1/models", "/v1/chat/completions", "/v1/usage", "/v1/orchestrate"]
    }

@app.get("/status", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Antigravity Autonomous Workstation — Control Plane</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
:root {
      --bg: #090d16;
      --bg-mesh: radial-gradient(ellipse 80% 50% at 50% -20%, rgba(56, 189, 248, 0.14), transparent),
                 radial-gradient(ellipse 60% 40% at 90% 10%, rgba(139, 92, 246, 0.10), transparent);
      --surface: #111827;
      --surface-elevated: #182234;
      --surface-inset: #0b101b;
      --border: rgba(148, 163, 184, 0.14);
      --border-strong: rgba(148, 163, 184, 0.28);
      --text: #f8fafc;
      --text-secondary: #cbd5e1;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --accent-soft: rgba(56, 189, 248, 0.12);
      --success: #22c55e;
      --success-soft: rgba(34, 197, 94, 0.12);
      --purple: #a78bfa;
      --purple-soft: rgba(167, 139, 250, 0.12);
      --warning: #f59e0b;
      --warning-soft: rgba(245, 158, 11, 0.12);
      --pink: #f472b6;
      --pink-soft: rgba(244, 114, 182, 0.12);
      --danger: #ef4444;
      --ring: #38bdf8;
      --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
      --ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
      --radius-lg: 14px;
      --radius-md: 10px;
      --radius-sm: 6px;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg);
      background-image: var(--bg-mesh);
      background-attachment: fixed;
      color: var(--text);
      font-family: "Fira Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
      min-height: 100vh;
      -webkit-font-smoothing: antialiased;
    }

    .mono, .tabular {
      font-family: "Fira Code", ui-monospace, SFMono-Regular, Menlo, monospace;
      font-variant-numeric: tabular-nums;
    }

    
    /* Multi-Agent Studio & Live Console (Apple HIG Liquid-Glass) */
    .agent-studio-section {
      margin-top: 24px;
      margin-bottom: 30px;
    }
    .agent-selector-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .agent-card {
      background: var(--surface-elevated);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 14px;
      cursor: pointer;
      transition: all 0.2s var(--ease-out);
      position: relative;
    }
    .agent-card:hover {
      border-color: var(--accent);
      transform: translateY(-2px);
    }
    .agent-card.active {
      border-color: var(--accent);
      background: rgba(56, 189, 248, 0.08);
      box-shadow: 0 0 20px rgba(56, 189, 248, 0.15);
    }
    .agent-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }
    .agent-name {
      font-weight: 700;
      font-size: 0.95rem;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .agent-status-pill {
      font-size: 0.68rem;
      font-weight: 600;
      padding: 2px 7px;
      border-radius: 999px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .status-online {
      background: var(--success-soft);
      color: var(--success);
      border: 1px solid rgba(34, 197, 94, 0.25);
    }
    .status-pending {
      background: var(--warning-soft);
      color: var(--warning);
      border: 1px solid rgba(245, 158, 11, 0.25);
    }
    .agent-desc {
      font-size: 0.76rem;
      color: var(--text-muted);
      line-height: 1.4;
      margin-bottom: 8px;
    }
    .agent-meta-badge {
      font-size: 0.70rem;
      font-family: "Fira Code", monospace;
      color: var(--text-secondary);
      background: var(--surface-inset);
      padding: 2px 6px;
      border-radius: 4px;
      display: inline-block;
    }
    .agent-console-box {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 18px;
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
    }
    @media (min-width: 900px) {
      .agent-console-box {
        grid-template-columns: 340px 1fr;
      }
    }

/* Sticky Liquid-Glass Functional Top Bar (Apple HIG liquid-glass.md) */
    .topbar {
      position: sticky;
      top: 0;
      z-index: 50;
      background: rgba(9, 13, 22, 0.78);
      backdrop-filter: blur(18px) saturate(180%);
      -webkit-backdrop-filter: blur(18px) saturate(180%);
      border-bottom: 1px solid var(--border);
      padding: 14px 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-icon {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(167, 139, 250, 0.2));
      border: 1px solid rgba(56, 189, 248, 0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--accent);
      box-shadow: 0 0 20px rgba(56, 189, 248, 0.15);
    }

    .brand-title {
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.01em;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .version-pill {
      font-size: 0.7rem;
      font-weight: 600;
      padding: 2px 7px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.28);
    }

    .brand-sub {
      font-size: 0.78rem;
      color: var(--text-muted);
    }

    .topbar-controls {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .provider-pills {
      display: flex;
      gap: 6px;
      align-items: center;
    }

    .prov-pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 0.72rem;
      font-weight: 600;
      padding: 4px 9px;
      border-radius: 999px;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text-muted);
    }

    .prov-pill.active {
      color: var(--text);
      border-color: rgba(34, 197, 94, 0.35);
      background: rgba(34, 197, 94, 0.08);
    }

    .dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--text-muted);
    }

    .prov-pill.active .dot, .status-pill .dot {
      background: var(--success);
      box-shadow: 0 0 8px var(--success);
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      background: var(--success-soft);
      color: var(--success);
      border: 1px solid rgba(34, 197, 94, 0.35);
      padding: 5px 12px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.03em;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      background: var(--accent);
      color: #06101e;
      font-weight: 600;
      font-size: 0.84rem;
      padding: 8px 14px;
      border-radius: var(--radius-sm);
      border: 1px solid transparent;
      cursor: pointer;
      min-height: 36px;
      transition: transform 140ms var(--ease-out), background-color 160ms var(--ease-out), border-color 160ms var(--ease-out);
      user-select: none;
    }

    .btn:hover {
      background: #7dd3fc;
    }

    .btn:active {
      transform: scale(0.97);
    }

    .btn:focus-visible, select:focus-visible, textarea:focus-visible, input:focus-visible, .tier-card:focus-visible, .chip:focus-visible {
      outline: 2px solid var(--ring);
      outline-offset: 2px;
    }

    .btn-ghost {
      background: var(--surface);
      color: var(--text-secondary);
      border: 1px solid var(--border);
    }

    .btn-ghost:hover {
      background: var(--surface-elevated);
      border-color: var(--border-strong);
      color: var(--text);
    }

    .container {
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px 28px 48px;
    }

    /* Bento KPI Grid */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 14px;
      margin-bottom: 24px;
    }

    @media (max-width: 1200px) {
      .kpi-grid { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 720px) {
      .kpi-grid { grid-template-columns: 1fr; }
    }

    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 18px 20px;
      position: relative;
      overflow: hidden;
      transition: border-color 180ms var(--ease-out), transform 180ms var(--ease-out);
    }

    .kpi-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }

    .kpi-title {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .kpi-icon {
      width: 30px;
      height: 30px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .kpi-val {
      font-size: 1.75rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--text);
      line-height: 1.2;
    }

    .kpi-sub {
      font-size: 0.76rem;
      color: var(--text-muted);
      margin-top: 6px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .meter-track {
      width: 100%;
      height: 5px;
      background: var(--surface-inset);
      border-radius: 999px;
      margin-top: 10px;
      overflow: hidden;
    }

    .meter-fill {
      height: 100%;
      border-radius: 999px;
      transition: width 300ms var(--ease-out);
    }

    /* Section Headers */
    .section-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }

    .section-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 8px;
      letter-spacing: -0.01em;
    }

    .section-hint {
      font-size: 0.76rem;
      color: var(--text-muted);
    }

    /* Interactive 5-Tier Pipeline Grid */
    .tiers-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 12px;
      margin-bottom: 24px;
    }

    @media (max-width: 1200px) {
      .tiers-grid { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 720px) {
      .tiers-grid { grid-template-columns: 1fr; }
    }

    .tier-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 15px 16px;
      cursor: pointer;
      text-align: left;
      transition: transform 160ms var(--ease-out), border-color 160ms var(--ease-out), background-color 160ms var(--ease-out);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .tier-card:hover {
      border-color: var(--border-strong);
      background: var(--surface-elevated);
      transform: translateY(-2px);
    }

    .tier-card:active {
      transform: scale(0.98);
    }

    .tier-card.selected {
      border-color: var(--accent);
      box-shadow: 0 0 0 1px var(--accent), 0 8px 24px -8px rgba(56, 189, 248, 0.25);
    }

    .tier-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      margin-bottom: 10px;
      width: fit-content;
    }

    .tier-name {
      font-weight: 700;
      font-size: 0.94rem;
      color: var(--text);
      margin-bottom: 4px;
    }

    .tier-desc {
      font-size: 0.76rem;
      color: var(--text-muted);
      margin-bottom: 12px;
      line-height: 1.4;
    }

    .tier-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 8px;
      border-top: 1px solid var(--border);
      font-size: 0.72rem;
    }

    /* Main Operations Deck (3-Column Responsive Grid) */
    .ops-grid {
      display: grid;
      grid-template-columns: 1.15fr 1fr 1.25fr;
      gap: 16px;
    }

    @media (max-width: 1280px) {
      .ops-grid { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 860px) {
      .ops-grid { grid-template-columns: 1fr; }
    }

    .field-label {
      font-size: 0.74rem;
      font-weight: 600;
      color: var(--text-secondary);
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }

    select, textarea, input[type="text"] {
      width: 100%;
      background: var(--surface-inset);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 9px 12px;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      margin-bottom: 12px;
      font-family: inherit;
      transition: border-color 150ms var(--ease-out);
    }

    select:hover, textarea:hover, input[type="text"]:hover {
      border-color: var(--border-strong);
    }

    .chips-row {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }

    .chip {
      background: var(--surface-inset);
      border: 1px solid var(--border);
      color: var(--text-muted);
      font-size: 0.71rem;
      padding: 4px 9px;
      border-radius: 999px;
      cursor: pointer;
      transition: transform 120ms var(--ease-out), border-color 150ms var(--ease-out), color 150ms var(--ease-out);
    }

    .chip:hover {
      color: var(--text);
      border-color: var(--accent);
    }

    .chip:active {
      transform: scale(0.96);
    }

    .output-box {
      background: var(--surface-inset);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 12px;
      font-size: 0.78rem;
      height: 210px;
      overflow-y: auto;
      white-space: pre-wrap;
      color: var(--text-secondary);
      margin-top: 10px;
    }

    .route-box {
      background: var(--surface-inset);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 12px;
      height: 255px;
      overflow-y: auto;
      margin-top: 10px;
    }

    .repo-tag {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: var(--purple-soft);
      color: var(--purple);
      border: 1px solid rgba(167, 139, 250, 0.3);
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.72rem;
      font-weight: 600;
      margin: 0 5px 5px 0;
    }

    .skill-tag {
      display: block;
      background: rgba(56, 189, 248, 0.07);
      border-left: 3px solid var(--accent);
      padding: 6px 10px;
      border-radius: 0 6px 6px 0;
      font-size: 0.74rem;
      color: var(--text-secondary);
      margin-bottom: 6px;
    }

    /* Tabs & Spend Table */
    .tab-group {
      display: inline-flex;
      background: var(--surface-inset);
      padding: 3px;
      border-radius: 8px;
      border: 1px solid var(--border);
    }

    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.74rem;
      font-weight: 600;
      padding: 5px 10px;
      border-radius: 6px;
      cursor: pointer;
      transition: background-color 150ms var(--ease-out), color 150ms var(--ease-out);
    }

    .tab-btn.active {
      background: var(--surface-elevated);
      color: var(--text);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8rem;
    }

    th, td {
      padding: 9px 10px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }

    th {
      color: var(--text-muted);
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.69rem;
      letter-spacing: 0.05em;
    }

    tr:hover td {
      background: rgba(255, 255, 255, 0.015);
    }

    .card-interactive {
      cursor: pointer;
      transition: transform 160ms var(--ease-out), border-color 160ms var(--ease-out), box-shadow 160ms var(--ease-out);
    }

    .card-interactive:hover {
      transform: translateY(-2px);
      border-color: var(--purple);
      box-shadow: 0 8px 24px -6px rgba(168, 85, 247, 0.25);
    }

    .hw-banner {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-bottom: 16px;
    }

    @media (max-width: 980px) {
      .hw-banner { grid-template-columns: 1fr; }
    }

    .hw-strip {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 11px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-size: 0.78rem;
    }

    .modal-backdrop {
      position: fixed;
      inset: 0;
      z-index: 200;
      background: rgba(4, 7, 13, 0.82);
      backdrop-filter: blur(8px);
      display: none;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }

    .modal-backdrop.open {
      display: flex;
    }

    .modal-panel {
      background: var(--surface);
      border: 1px solid var(--border-strong);
      border-radius: var(--radius-lg);
      max-width: 960px;
      width: 100%;
      max-height: 86vh;
      overflow-y: auto;
      padding: 24px;
      box-shadow: 0 24px 64px rgba(0, 0, 0, 0.65);
    }

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
      }
    }
/* Multi-Agent Design Studio & OpenDots Canvas */
    .agent-studio-section {
      margin-top: 28px;
      margin-bottom: 34px;
    }
    .studio-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 22px;
      box-shadow: 0 16px 40px -10px rgba(0, 0, 0, 0.5);
    }
    .studio-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
      gap: 12px;
    }
    .studio-title-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .studio-icon-glow {
      width: 42px;
      height: 42px;
      border-radius: 12px;
      background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(168, 85, 247, 0.25));
      border: 1px solid rgba(56, 189, 248, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--accent);
      box-shadow: 0 0 20px rgba(56, 189, 248, 0.25);
    }
    .studio-title {
      font-size: 1.18rem;
      font-weight: 700;
      color: var(--text);
      letter-spacing: -0.015em;
    }
    .studio-sub {
      font-size: 0.78rem;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .agent-selector-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 10px;
      margin-bottom: 18px;
    }
    .agent-card {
      background: var(--surface-elevated);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 12px 14px;
      cursor: pointer;
      transition: all 0.22s var(--ease-out);
      position: relative;
    }
    .agent-card:hover {
      border-color: var(--accent);
      transform: translateY(-2px);
    }
    .agent-card.active {
      border-color: var(--accent);
      background: rgba(56, 189, 248, 0.08);
      box-shadow: 0 0 0 1px var(--accent), 0 0 24px rgba(56, 189, 248, 0.2);
    }
    .agent-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 4px;
    }
    .agent-name {
      font-weight: 700;
      font-size: 0.90rem;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .agent-status-pill {
      font-size: 0.64rem;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 999px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .agent-desc {
      font-size: 0.74rem;
      color: var(--text-muted);
      line-height: 1.38;
      margin-bottom: 8px;
      min-height: 30px;
    }
    .agent-meta-badge {
      font-size: 0.65rem;
      padding: 2px 6px;
      border-radius: 4px;
      background: var(--surface-inset);
      color: var(--text-secondary);
      border: 1px solid var(--border);
      font-family: var(--font-mono, monospace);
    }
    .studio-split-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
    }
    @media (min-width: 960px) {
      .studio-split-grid {
        grid-template-columns: 370px 1fr;
      }
    }
    .studio-controls-pane {
      display: flex;
      flex-direction: column;
      gap: 14px;
      background: var(--surface-inset);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 16px;
    }
    .studio-canvas-pane {
      display: flex;
      flex-direction: column;
      background: #060910;
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      overflow: hidden;
      min-height: 500px;
      box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.6);
    }
    .canvas-nav-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 9px 12px;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
      gap: 8px;
    }
    .mac-traffic-lights {
      display: flex;
      gap: 6px;
      align-items: center;
      margin-right: 4px;
    }
    .traffic-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
    .traffic-red { background: #ef4444; }
    .traffic-yellow { background: #f59e0b; }
    .traffic-green { background: #10b981; }
    .canvas-tabs {
      display: flex;
      gap: 4px;
      background: var(--surface-inset);
      padding: 3px;
      border-radius: 8px;
    }
    .canvas-tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.72rem;
      font-weight: 600;
      padding: 5px 10px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s var(--ease-out);
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .canvas-tab-btn:hover { color: var(--text); }
    .canvas-tab-btn.active {
      background: var(--accent-soft);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.35);
    }
    .canvas-viewport-wrap {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #060910;
      position: relative;
      overflow: hidden;
      min-height: 460px;
    }
    .canvas-iframe {
      width: 100%;
      height: 100%;
      min-height: 460px;
      border: none;
      background: transparent;
      transition: width 0.3s cubic-bezier(0.23, 1, 0.32, 1);
    }
    .canvas-iframe.mobile-view {
      width: 375px;
      box-shadow: 0 0 0 10px #1e293b, 0 20px 50px rgba(0, 0, 0, 0.8);
      border-radius: 32px;
      margin: 18px auto;
      height: 90%;
    }
    .mode-pills-row {
      display: flex;
      gap: 4px;
      background: var(--surface-elevated);
      padding: 3px;
      border-radius: 8px;
    }
    .mode-pill {
      flex: 1;
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.71rem;
      font-weight: 600;
      padding: 5px 6px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s var(--ease-out);
      text-align: center;
    }
    .mode-pill.active {
      background: var(--accent-soft);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.35);
    }
  </style>
</head>
<body>
  <!-- Sticky Liquid-Glass Functional Header -->
  <header class="topbar" role="banner">
    <div class="brand">
      <div class="brand-icon" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
      </div>
      <div>
        <div class="brand-title">
          Antigravity Autonomous Workstation
          <span class="version-pill mono">v3.4 OS</span>
        </div>
        <div class="brand-sub">Unified 5-Tier AI Gateway • Graphify AST Engine • Hardware-Adaptive Ollama • 32-Repo Auto-Router</div>
      </div>
    </div>

    <div class="topbar-controls">
      <div class="provider-pills" id="provider-pills" aria-label="Active AI Providers">
        <span class="prov-pill active" id="pill-bedrock"><span class="dot"></span>Bedrock</span>
        <span class="prov-pill active" id="pill-ollama"><span class="dot"></span>Ollama GPU</span>
        <span class="prov-pill" id="pill-byok"><span class="dot"></span>BYOK Cloud</span>
      </div>
      <div class="status-pill mono" id="status-badge" role="status" aria-live="polite">
        <span class="dot"></span>
        <span id="status-text">ONLINE • 127.0.0.1:8000</span>
      </div>
            <button class="btn btn-ghost" onclick="triggerAutoConfig()" title="Auto-configure Claude Code, Codex, Aider, OpenDots & Ollama">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2.2" aria-hidden="true"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
        ⚡ Auto-Configure
      </button>
      <a class="btn btn-ghost" href="#agent-studio-section" title="Jump to Multi-Agent Studio & Live Chat">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--pink)" stroke-width="2.2" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><path d="M8 14s1.5 2 4 2 4-2 4-2"></path><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="15" y1="9" x2="15.01" y2="9"></line></svg>
        Agent Studio
      </a>
<button class="btn btn-ghost" onclick="openKeysModal()" title="Configure Personal API Keys & Auto-Setup AWS Bedrock">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--warning)" stroke-width="2.2" aria-hidden="true"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path></svg>
        API Keys &amp; Cloud
      </button>
      <button class="btn btn-ghost" onclick="window.open('/graphify', '_blank')" title="Open Interactive Graphify AST Graph (graphify-out/graph.html)">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--purple)" stroke-width="2.2" aria-hidden="true"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
        Graphify AST ↗
      </button>
      <button class="btn btn-ghost" onclick="openGuideModal()" title="How It Works & Cross-PC Setup Guide">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.2" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
        How It Works
      </button>
      <button class="btn btn-ghost" onclick="togglePolling()" id="pause-btn" title="Pause or resume 5s live telemetry polling">
        <span id="pause-label">Live: 5s</span>
      </button>
      <button class="btn" onclick="fetchStats()" title="Refresh all gateway telemetry now">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
        Refresh
      </button>
    </div>
  </header>

  <main class="container">
    <!-- Hardware Profile & Live Chat Auto-Router Strip -->
    <section class="hw-banner" aria-label="Hardware Profile and Live Chat Auto-Router">
      <div class="hw-strip">
        <div style="display: flex; align-items: center; gap: 10px;">
          <span class="kpi-icon" style="background: var(--success-soft); color: var(--success); width: 28px; height: 28px;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="4" y="4" width="16" height="16" rx="2"></rect><rect x="9" y="9" width="6" height="6"></rect></svg>
          </span>
          <div>
            <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Detected Host Hardware & Local Ollama Profile</div>
            <div id="hw-summary" style="color: var(--text); font-weight: 600; margin-top: 1px;">Detecting PC/Mac GPU & RAM profile...</div>
          </div>
        </div>
        <span class="mono" id="hw-model-pill" style="background: var(--success-soft); color: var(--success); padding: 3px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600;">llama3.2:1b</span>
      </div>

      <div class="hw-strip">
        <div style="display: flex; align-items: center; gap: 10px; min-width: 0;">
          <span class="kpi-icon" style="background: var(--purple-soft); color: var(--purple); width: 28px; height: 28px; flex-shrink: 0;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
          </span>
          <div style="min-width: 0;">
            <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Live Chat PreInvocation Auto-Router</div>
            <div id="live-route-summary" style="color: var(--text); font-weight: 600; margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Active on every prompt • Zero manual repo names needed</div>
          </div>
        </div>
        <span class="mono" id="live-route-tier" style="background: var(--purple-soft); color: var(--purple); padding: 3px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; flex-shrink: 0;">AUTO ACTIVE</span>
      </div>
    </section>

    <!-- 5-Card Bento Telemetry Row -->
    <section class="kpi-grid" aria-label="Key Performance Telemetry">
      <div class="card">
        <div class="kpi-header">
          <span class="kpi-title">Actual Spend (USD)</span>
          <span class="kpi-icon" style="background: var(--accent-soft); color: var(--accent);" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
          </span>
        </div>
        <div class="kpi-val tabular" id="total-usd">$0.0000</div>
        <div class="kpi-sub">
          <span id="requests-count" class="tabular">0 requests</span>
          <span class="mono" style="color: var(--accent);" id="avg-cost">$0.000/req</span>
        </div>
        <div class="meter-track"><div class="meter-fill" id="spend-bar" style="width: 12%; background: var(--accent);"></div></div>
      </div>

      <div class="card">
        <div class="kpi-header">
          <span class="kpi-title">Smart-Tier Savings</span>
          <span class="kpi-icon" style="background: var(--success-soft); color: var(--success);" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>
          </span>
        </div>
        <div class="kpi-val tabular" style="color: var(--success);" id="saved-usd">$0.0000</div>
        <div class="kpi-sub">
          <span>vs. Opus Frontier</span>
          <span class="mono" style="color: var(--success); font-weight: 600;" id="savings-pct">97.8% saved</span>
        </div>
        <div class="meter-track"><div class="meter-fill" id="savings-bar" style="width: 97.8%; background: var(--success);"></div></div>
      </div>

      <div class="card">
        <div class="kpi-header">
          <span class="kpi-title">Token Throughput</span>
          <span class="kpi-icon" style="background: var(--warning-soft); color: var(--warning);" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg>
          </span>
        </div>
        <div class="kpi-val tabular" id="total-tokens">0</div>
        <div class="kpi-sub">
          <span id="tokens-sub" class="tabular">0 in / 0 out</span>
        </div>
        <div class="meter-track"><div class="meter-fill" id="token-bar" style="width: 85%; background: var(--warning);"></div></div>
      </div>

      <div class="card card-interactive" id="graphify-card" role="button" tabindex="0" onclick="window.open('/graphify', '_blank')" onkeydown="if(event.key==='Enter'||event.key===' ') window.open('/graphify', '_blank')" title="Click to open interactive Graphify AST Graph (graphify-out/graph.html)">
        <div class="kpi-header">
          <span class="kpi-title" style="color: var(--purple);">Graphify AST Graph ↗</span>
          <span class="kpi-icon" style="background: var(--purple-soft); color: var(--purple);" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
          </span>
        </div>
        <div class="kpi-val tabular" style="color: var(--purple);" id="graph-nodes">2,397 Nodes</div>
        <div class="kpi-sub">
          <span id="graph-sub" class="tabular">4,445 edges • Tap to open</span>
          <span class="mono" style="color: var(--purple); font-weight: 600; text-decoration: underline;" onclick="event.stopPropagation(); window.open('/graphify/report', '_blank')" title="Open GRAPH_REPORT.md">Report ↗</span>
        </div>
        <div class="meter-track"><div class="meter-fill" style="width: 100%; background: var(--purple);"></div></div>
      </div>

      <div class="card">
        <div class="kpi-header">
          <span class="kpi-title">32-Repo Skill Router</span>
          <span class="kpi-icon" style="background: var(--pink-soft); color: var(--pink);" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>
          </span>
        </div>
        <div class="kpi-val tabular" style="color: var(--pink);" id="skills-count">456 Skills</div>
        <div class="kpi-sub">
          <span>32 / 32 Repos Ready</span>
          <span class="mono" id="latency-ms" style="color: var(--success);">-- ms</span>
        </div>
        <div class="meter-track"><div class="meter-fill" style="width: 100%; background: var(--pink);"></div></div>
      </div>
    </section>

    <!-- Interactive 5-Tier Smart Auto-Routing Pipeline -->
    <div class="section-bar">
      <div class="section-title">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.2" aria-hidden="true"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
        5-Tier Smart Auto-Routing Hierarchy
      </div>
      <div class="section-hint">Click any tier card to target it in the Live Gateway Playground</div>
    </div>

    <section class="tiers-grid" aria-label="Model Routing Tiers">
      <button type="button" class="tier-card" onclick="selectTier('local', this)">
        <div>
          <span class="tier-badge" style="color: var(--success); background: var(--success-soft);">TIER 1 • LOCAL GPU</span>
          <div class="tier-name">Ollama Radeon GPU</div>
          <div class="tier-desc">Llama 3.2 1B on discrete GPU. 100% offline, sub-150ms response, zero cloud credit cost.</div>
        </div>
        <div class="tier-meta mono">
          <span style="color: var(--success);">$0.00 / 1M</span>
          <span style="color: var(--text-muted);">~148ms</span>
        </div>
      </button>

      <button type="button" class="tier-card" onclick="selectTier('fast', this)">
        <div>
          <span class="tier-badge" style="color: var(--accent); background: var(--accent-soft);">TIER 2 • FAST SCOUT</span>
          <div class="tier-name">Llama 4 Scout 17B</div>
          <div class="tier-desc">High-speed unit test generation, config updates, HTML/CSS layout tweaks, and commit messages.</div>
        </div>
        <div class="tier-meta mono">
          <span style="color: var(--accent);">$0.08 / 1M</span>
          <span style="color: var(--text-muted);">~190ms</span>
        </div>
      </button>

      <button type="button" class="tier-card" onclick="selectTier('coder', this)">
        <div>
          <span class="tier-badge" style="color: var(--purple); background: var(--purple-soft);">TIER 3 • WORKHORSE</span>
          <div class="tier-name">Llama 3.3 70B Instruct</div>
          <div class="tier-desc">Default full-stack coding engine for APIs, React components, state logic, and refactoring.</div>
        </div>
        <div class="tier-meta mono">
          <span style="color: var(--purple);">$0.72 / 1M</span>
          <span style="color: var(--text-muted);">~300ms</span>
        </div>
      </button>

      <button type="button" class="tier-card" onclick="selectTier('reasoner', this)">
        <div>
          <span class="tier-badge" style="color: var(--warning); background: var(--warning-soft);">TIER 4 • REASONER</span>
          <div class="tier-name">DeepSeek R1 Critic</div>
          <div class="tier-desc">Chain-of-thought root-cause debugging, race conditions, and Frontier Critic (--judge) review.</div>
        </div>
        <div class="tier-meta mono">
          <span style="color: var(--warning);">$1.35 / 1M</span>
          <span style="color: var(--text-muted);">~1.1s</span>
        </div>
      </button>

      <button type="button" class="tier-card" onclick="selectTier('claude', this)">
        <div>
          <span class="tier-badge" style="color: var(--pink); background: var(--pink-soft);">TIER 5 • FRONTIER</span>
          <div class="tier-name">Claude Sonnet 4.6 & Opus 4.6</div>
          <div class="tier-desc">High-stakes system architecture, cryptography, security overhauls, and multi-repo synthesis.</div>
        </div>
        <div class="tier-meta mono">
          <span style="color: var(--pink);">$3.00 / 1M</span>
          <span style="color: var(--text-muted);">~2.0s</span>
        </div>
      </button>
    </section>

    <!-- 3-Column Interactive Operations Deck -->
    <!-- ==========================================================================
         INTERACTIVE MULTI-AGENT DESIGN STUDIO & OPENDOTS CANVAS
         ========================================================================== -->
    <section class="agent-studio-section" id="agent-studio-section" aria-label="Interactive Multi-Agent Design Studio and OpenDots Canvas">
      <div class="studio-card">
        <div class="studio-header">
          <div class="studio-title-group">
            <div class="studio-icon-glow">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"></path><path d="M2 12h20"></path></svg>
            </div>
            <div>
              <div class="studio-title">Interactive Design Studio &amp; OpenDots Canvas</div>
              <div class="studio-sub">Generate, render, and interact with live UI components, visual state dots, and CopilotKit agent workspaces in real time.</div>
            </div>
          </div>
          <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
            <button type="button" class="btn btn-ghost" style="font-size: 0.74rem; padding: 5px 11px;" onclick="window.open('http://localhost:5173', '_blank')" id="btn-opendots-open" title="Open standalone OpenDots web application">
              🌐 OpenDots App ↗
            </button>
            <button type="button" class="btn" style="background: linear-gradient(135deg, #10b981, #059669); font-size: 0.74rem; padding: 6px 13px;" onclick="triggerAutoConfig()" id="btn-auto-config" title="Auto-configures Claude Code, Codex, Aider, OpenDots, and Ollama in 1 click">
              ⚡ Auto-Configure
            </button>
          </div>
        </div>

        <!-- 5 Agent Cards Grid -->
        <div class="agent-selector-grid">
          <!-- Claude Code -->
          <div class="agent-card active" id="agent-card-claude" onclick="selectAgent('claude')">
            <div class="agent-card-header">
              <span class="agent-name"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#a78bfa;box-shadow:0 0 8px #a78bfa;"></span>Claude Code</span>
              <span class="agent-status-pill status-online" id="status-pill-claude">ONLINE</span>
            </div>
            <div class="agent-desc">Architectural lead &amp; high-craft UI component designer on Bedrock Opus 4.6 &amp; Sonnet 4.6.</div>
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              <span class="agent-meta-badge" id="badge-claude-model">Sonnet 4.6</span>
              <span class="agent-meta-badge" id="badge-claude-prof">Bedrock</span>
            </div>
          </div>

          <!-- OpenAI Codex -->
          <div class="agent-card" id="agent-card-codex" onclick="selectAgent('codex')">
            <div class="agent-card-header">
              <span class="agent-name"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#34d399;box-shadow:0 0 8px #34d399;"></span>OpenAI Codex</span>
              <span class="agent-status-pill status-online" id="status-pill-codex">ONLINE</span>
            </div>
            <div class="agent-desc">Rapid component generation and elevated sandbox coding engine.</div>
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              <span class="agent-meta-badge" id="badge-codex-model">gpt-5.6-terra</span>
              <span class="agent-meta-badge">ChatGPT</span>
            </div>
          </div>

          <!-- Aider -->
          <div class="agent-card" id="agent-card-aider" onclick="selectAgent('aider')">
            <div class="agent-card-header">
              <span class="agent-name"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#38bdf8;box-shadow:0 0 8px #38bdf8;"></span>Aider</span>
              <span class="agent-status-pill status-online" id="status-pill-aider">ONLINE</span>
            </div>
            <div class="agent-desc">Automated pair-programming engine wired to the Unified 5-Tier auto-router.</div>
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              <span class="agent-meta-badge">openai/auto</span>
              <span class="agent-meta-badge">:8000/v1</span>
            </div>
          </div>

          <!-- OpenDots Canvas -->
          <div class="agent-card" id="agent-card-opendots" onclick="selectAgent('opendots')">
            <div class="agent-card-header">
              <span class="agent-name"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#fb923c;box-shadow:0 0 8px #fb923c;"></span>OpenDots</span>
              <span class="agent-status-pill status-ready" id="status-pill-opendots">READY</span>
            </div>
            <div class="agent-desc">CopilotKit Generative UI canvas, visual state dots, and agent coworker spaces.</div>
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              <span class="agent-meta-badge">Port 5173</span>
              <span class="agent-meta-badge">Canvas</span>
            </div>
          </div>

          <!-- Workstation Orchestrator -->
          <div class="agent-card" id="agent-card-orchestrator" onclick="selectAgent('orchestrator')">
            <div class="agent-card-header">
              <span class="agent-name"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#f472b6;box-shadow:0 0 8px #f472b6;"></span>Orchestrator</span>
              <span class="agent-status-pill status-ready" id="status-pill-orchestrator">READY</span>
            </div>
            <div class="agent-desc">Multi-agent controller with Tree-sitter AST sensor and GitGuardian shield.</div>
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              <span class="agent-meta-badge">AST Sensor</span>
              <span class="agent-meta-badge">ggshield</span>
            </div>
          </div>
        </div>

        <!-- Split-Screen Studio Grid -->
        <div class="studio-split-grid">
          <!-- Left: Controls & Prompts -->
          <div class="studio-controls-pane">
            <div>
              <label class="field-label">Studio Mode</label>
              <div class="mode-pills-row">
                <button type="button" class="mode-pill active" id="mode-design-btn" onclick="setStudioMode('design')">🎨 UI Design</button>
                <button type="button" class="mode-pill" id="mode-dots-btn" onclick="setStudioMode('dots')">🔮 State Dots</button>
                <button type="button" class="mode-pill" id="mode-code-btn" onclick="setStudioMode('code')">💻 Full Code</button>
                <button type="button" class="mode-pill" id="mode-cli-btn" onclick="setStudioMode('cli')">⚡ CLI Dispatch</button>
              </div>
            </div>

            <div>
              <label class="field-label" for="studio-model-select">Model Profile</label>
              <select id="studio-model-select" style="margin-bottom: 0;">
                <option value="sonnet" selected>Claude Sonnet 4.6 (Fast Bedrock)</option>
                <option value="opus">Claude Opus 4.6 (Frontier Bedrock)</option>
                <option value="auto">Auto 5-Tier Fallback Router</option>
                <option value="gpt-5.6-terra">ChatGPT gpt-5.6-terra (Codex)</option>
                <option value="gpt-6-luna">ChatGPT gpt-6-luna (Codex)</option>
                <option value="local">Local Ollama ($0.00)</option>
              </select>
            </div>

            <div>
              <label class="field-label">1-Click Design Starters</label>
              <div class="chips-row" style="margin-top: 2px;">
                <button type="button" class="chip" onclick="setPresetPrompt('Design a modern Apple HIG liquid-glass music player card with working play/pause, volume slider, album art, and spring physics', 'design')">✨ Apple HIG Music Player</button>
                <button type="button" class="chip" onclick="setPresetPrompt('Create an OpenDots interactive visual state canvas with 5 glowing agent dots, connecting bezier arcs, and state channel inspect cards', 'dots')">🔮 OpenDots State Nodes</button>
                <button type="button" class="chip" onclick="setPresetPrompt('Design an Apple HIG dark glassmorphism telemetry card with circular SVG gauges and spring animations', 'design')">📊 Glassmorphism Gauges</button>
                <button type="button" class="chip" onclick="setPresetPrompt('Design an iOS 18 dynamic island audio pill component with smooth spring hover and expanding controls', 'design')">📱 iOS 18 Audio Pill</button>
                <button type="button" class="chip" onclick="setPresetPrompt('Design a high-contrast responsive SaaS pricing matrix bento grid with gradient borders', 'design')">💎 SaaS Pricing Bento</button>
              </div>
            </div>

            <div style="flex: 1; display: flex; flex-direction: column;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <label class="field-label" id="studio-prompt-label" for="studio-prompt-input" style="margin-bottom: 0;">Design or Chat Instruction</label>
                <span class="mono" style="font-size: 0.68rem; color: var(--text-muted);">Ctrl + Enter to run</span>
              </div>
              <textarea id="studio-prompt-input" rows="4" style="flex: 1; min-height: 90px;" placeholder="Describe a component, layout, or visual design to build and preview live in the canvas..."></textarea>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
              <span id="studio-exec-status" style="font-size: 0.72rem; color: var(--text-muted);">Ready to design</span>
              <div style="display: flex; gap: 8px;">
                <button type="button" class="btn btn-ghost" style="font-size: 0.74rem; padding: 6px 10px;" onclick="resetShowcaseDesign()">Reset Showcase</button>
                <button type="button" class="btn" style="background: linear-gradient(135deg, #38bdf8, #818cf8); font-size: 0.76rem; padding: 7px 14px; box-shadow: 0 4px 14px rgba(56, 189, 248, 0.35);" id="btn-studio-generate" onclick="generateDesign()">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                  Generate &amp; Render Design
                </button>
              </div>
            </div>
          </div>

          <!-- Right: Interactive Live Canvas & Inspector -->
          <div class="studio-canvas-pane">
            <div class="canvas-nav-bar">
              <div style="display: flex; align-items: center; gap: 10px;">
                <div class="mac-traffic-lights" aria-hidden="true">
                  <div class="traffic-dot traffic-red"></div>
                  <div class="traffic-dot traffic-yellow"></div>
                  <div class="traffic-dot traffic-green"></div>
                </div>
                <div class="canvas-tabs">
                  <button type="button" class="canvas-tab-btn active" id="tab-canvas-preview-btn" onclick="switchStudioTab('preview')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                    Visual Preview
                  </button>
                  <button type="button" class="canvas-tab-btn" id="tab-canvas-dots-btn" onclick="switchStudioTab('dots')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="3"></circle><circle cx="19" cy="6" r="2"></circle><circle cx="5" cy="6" r="2"></circle><circle cx="19" cy="18" r="2"></circle><circle cx="5" cy="18" r="2"></circle></svg>
                    OpenDots State Dots
                  </button>
                  <button type="button" class="canvas-tab-btn" id="tab-canvas-code-btn" onclick="switchStudioTab('code')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
                    Code Inspector
                  </button>
                  <button type="button" class="canvas-tab-btn" id="tab-canvas-logs-btn" onclick="switchStudioTab('logs')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
                    Diagnostics
                  </button>
                  <button type="button" class="canvas-tab-btn" id="tab-canvas-app-btn" onclick="switchStudioTab('app')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>
                    OpenDots App (5173)
                  </button>
                </div>
              </div>

              <!-- Viewport & Actions Toolbar -->
              <div style="display: flex; gap: 6px; align-items: center;">
                <button type="button" class="btn btn-ghost" style="padding: 4px 8px; font-size: 0.72rem;" onclick="setCanvasViewport('desktop')" id="vp-desktop-btn" title="Desktop width (100%)">💻 Desktop</button>
                <button type="button" class="btn btn-ghost" style="padding: 4px 8px; font-size: 0.72rem;" onclick="setCanvasViewport('mobile')" id="vp-mobile-btn" title="Mobile width (375px)">📱 Mobile</button>
                <button type="button" class="btn btn-ghost" style="padding: 4px 8px; font-size: 0.72rem;" onclick="copyCanvasCode()" title="Copy active component code">📋 Copy</button>
                <button type="button" class="btn btn-ghost" style="padding: 4px 8px; font-size: 0.72rem;" onclick="downloadCanvasHtml()" title="Download as HTML file">💾 Download</button>
                <button type="button" class="btn btn-ghost" style="padding: 4px 8px; font-size: 0.72rem;" onclick="openCanvasNewTab()" title="Open live component in new tab">🚀 Popout ↗</button>
              </div>
            </div>

            <!-- View 1: Visual Sandbox Canvas -->
            <div class="canvas-viewport-wrap" id="view-canvas-preview">
              <iframe id="studio-live-iframe" class="canvas-iframe" sandbox="allow-scripts allow-modals allow-forms allow-same-origin" title="Live Visual Component Sandbox"></iframe>
            </div>

            <!-- View 2: OpenDots State Dots Canvas -->
            <div id="view-canvas-dots" style="display: none; padding: 18px; flex: 1; background: #080c14; overflow-y: auto;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div>
                  <div style="font-weight: 700; font-size: 0.92rem; color: #fb923c;">OpenDots CopilotKit State Dots Engine</div>
                  <div style="font-size: 0.74rem; color: var(--text-muted);">Active agent coworker state dots, persistent thread channels, and reactive intelligence.</div>
                </div>
                <button type="button" class="btn" style="background: #ea580c; font-size: 0.74rem; padding: 4px 10px;" onclick="startOpenDotsServer()">▶ Start OpenDots Server</button>
              </div>

              <!-- Interactive SVG Dots Graph -->
              <svg viewBox="0 0 760 320" style="width: 100%; max-height: 320px; background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 14px;">
                <defs>
                  <linearGradient id="grad-curve" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.6"/>
                    <stop offset="50%" stop-color="#a855f7" stop-opacity="0.6"/>
                    <stop offset="100%" stop-color="#fb923c" stop-opacity="0.8"/>
                  </linearGradient>
                  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="6" result="blur"/>
                    <feComposite in="SourceGraphic" in2="blur" operator="over"/>
                  </filter>
                </defs>

                <!-- Connecting Arcs -->
                <path d="M 120 160 C 260 80, 260 160, 380 160" fill="none" stroke="url(#grad-curve)" stroke-width="2.5" stroke-dasharray="6,4"/>
                <path d="M 380 160 C 500 160, 500 80, 640 160" fill="none" stroke="url(#grad-curve)" stroke-width="2.5"/>
                <path d="M 380 160 C 380 260, 260 260, 240 250" fill="none" stroke="rgba(56, 189, 248, 0.4)" stroke-width="2"/>
                <path d="M 380 160 C 380 260, 500 260, 520 250" fill="none" stroke="rgba(244, 114, 182, 0.4)" stroke-width="2"/>

                <!-- Node 1: Research Dot -->
                <g class="dot-node" onclick="selectDot('research')" style="cursor: pointer;">
                  <circle cx="120" cy="160" r="32" fill="rgba(56, 189, 248, 0.15)" stroke="#38bdf8" stroke-width="2" filter="url(#glow)"/>
                  <circle cx="120" cy="160" r="12" fill="#38bdf8"/>
                  <text x="120" y="210" text-anchor="middle" fill="#f8fafc" font-size="12" font-weight="700">Research</text>
                  <text x="120" y="226" text-anchor="middle" fill="#94a3b8" font-size="10">agent-reach</text>
                </g>

                <!-- Node 2: UI Architect Dot (Center) -->
                <g class="dot-node" onclick="selectDot('architect')" style="cursor: pointer;">
                  <circle cx="380" cy="160" r="44" fill="rgba(168, 85, 247, 0.2)" stroke="#a855f7" stroke-width="2.5" filter="url(#glow)"/>
                  <circle cx="380" cy="160" r="16" fill="#a855f7"/>
                  <text x="380" y="222" text-anchor="middle" fill="#ffffff" font-size="13" font-weight="700">UI Architect</text>
                  <text x="380" y="238" text-anchor="middle" fill="#cbd5e1" font-size="10">Apple HIG Core</text>
                </g>

                <!-- Node 3: Generative Canvas Dot -->
                <g class="dot-node" onclick="selectDot('canvas')" style="cursor: pointer;">
                  <circle cx="640" cy="160" r="34" fill="rgba(251, 146, 60, 0.2)" stroke="#fb923c" stroke-width="2" filter="url(#glow)"/>
                  <circle cx="640" cy="160" r="13" fill="#fb923c"/>
                  <text x="640" y="212" text-anchor="middle" fill="#f8fafc" font-size="12" font-weight="700">Canvas</text>
                  <text x="640" y="228" text-anchor="middle" fill="#94a3b8" font-size="10">CopilotKit :5173</text>
                </g>

                <!-- Node 4: Security Shield Dot -->
                <g class="dot-node" onclick="selectDot('security')" style="cursor: pointer;">
                  <circle cx="240" cy="250" r="24" fill="rgba(34, 197, 94, 0.2)" stroke="#22c55e" stroke-width="1.8"/>
                  <circle cx="240" cy="250" r="9" fill="#22c55e"/>
                  <text x="240" y="288" text-anchor="middle" fill="#cbd5e1" font-size="11" font-weight="600">Security</text>
                </g>

                <!-- Node 5: Motion & Spring Physics Dot -->
                <g class="dot-node" onclick="selectDot('motion')" style="cursor: pointer;">
                  <circle cx="520" cy="250" r="24" fill="rgba(244, 114, 182, 0.2)" stroke="#f472b6" stroke-width="1.8"/>
                  <circle cx="520" cy="250" r="9" fill="#f472b6"/>
                  <text x="520" y="288" text-anchor="middle" fill="#cbd5e1" font-size="11" font-weight="600">Spring Motion</text>
                </g>
              </svg>

              <!-- Node Detail Inspector Card -->
              <div id="dot-inspector-card" style="background: var(--surface-elevated); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 12px;">
                <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Selected OpenDot</div>
                <div id="dot-inspector-title" style="font-size: 0.92rem; font-weight: 700; color: var(--text); margin-top: 2px;">UI Architect Dot (Core)</div>
                <div id="dot-inspector-desc" style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 4px;">Generates Apple HIG compliant glassmorphism layouts, Cupertino typography, and responsive Bento grids. Click any dot above to inspect.</div>
              </div>
            </div>

            <!-- View 3: Code Inspector -->
            <div id="view-canvas-code" style="display: none; padding: 16px; flex: 1; background: #070a12; overflow-y: auto;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span class="mono" style="font-size: 0.72rem; color: var(--accent);">Active HTML/CSS Component Source</span>
                <button type="button" class="btn btn-ghost" style="padding: 3px 8px; font-size: 0.70rem;" onclick="copyCanvasCode()">Copy to Clipboard</button>
              </div>
              <pre id="studio-code-viewer" class="mono" style="font-size: 0.74rem; color: #cbd5e1; line-height: 1.5; white-space: pre-wrap; word-break: break-all; margin: 0;"></pre>
            </div>

            <!-- View 4: Diagnostics Log -->
            <div id="view-canvas-logs" style="display: none; padding: 16px; flex: 1; background: #070a12; overflow-y: auto;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span class="mono" style="font-size: 0.72rem; color: #a78bfa;">Execution Trace &amp; Hardware Sensor</span>
                <button type="button" class="btn btn-ghost" style="padding: 3px 8px; font-size: 0.70rem;" onclick="document.getElementById('studio-diagnostics-text').innerText=''">Clear Logs</button>
              </div>
              <pre id="studio-diagnostics-text" class="mono" style="font-size: 0.72rem; color: #94a3b8; line-height: 1.5; white-space: pre-wrap; margin: 0;">Ready to execute. Tap Generate &amp; Render Design to dispatch prompt.</pre>
            </div>

            <!-- View 5: OpenDots Standalone App -->
            <div id="view-canvas-app" style="display: none; flex: 1; background: #080c14; position: relative;">
              <iframe id="opendots-app-iframe" src="http://localhost:5173" style="width: 100%; height: 100%; min-height: 480px; border: none;" title="OpenDots Standalone Web App"></iframe>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="ops-grid" aria-label="Interactive Gateway Tools and Telemetry">
      <!-- Column 1: Live Gateway Playground -->
      <div class="card">
        <div class="section-bar">
          <div class="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.2" aria-hidden="true"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
            Live Gateway Playground
          </div>
          <span class="mono" style="font-size: 0.7rem; color: var(--text-muted);">Ctrl+Enter</span>
        </div>

        <label class="field-label" for="test-model">
          <span>Target Model Tier</span>
          <span class="mono" id="routed-badge" style="color: var(--accent);">auto-router ready</span>
        </label>
        <select id="test-model">
          <option value="auto">auto — 5-Tier Smart Auto-Router</option>
          <option value="local">local — Ollama GPU ($0.00)</option>
          <option value="fast">fast — Llama 4 Scout ($0.08/M)</option>
          <option value="coder">coder — Llama 3.3 70B ($0.72/M)</option>
          <option value="reasoner">reasoner — DeepSeek R1 ($1.35/M)</option>
          <option value="claude">claude — Claude Sonnet 4.5 ($3.00/M)</option>
          <option value="opus">opus — Claude Opus 4.5 ($15.00/M)</option>
        </select>

        <div class="chips-row" aria-label="Quick Prompt Presets">
          <button type="button" class="chip" onclick="setPrompt('auto', 'Fix a typo in docstring: reply in 1 sentence')">Tier 1: Docstring ($0)</button>
          <button type="button" class="chip" onclick="setPrompt('auto', 'Write a unit test assertion for HTTP 200 in 2 lines')">Tier 2: Unit Test</button>
          <button type="button" class="chip" onclick="setPrompt('auto', 'Debug why a mutex lock causes a race condition in 2 sentences')">Tier 4: Race Condition</button>
        </div>

        <label class="field-label" for="test-prompt">Prompt Instruction</label>
        <textarea id="test-prompt" rows="2">Explain in 1 sentence how the 5-tier router conserves credits.</textarea>

        <button type="button" class="btn" style="width: 100%;" onclick="runTestPrompt()" id="run-btn">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          <span id="run-btn-label">Execute on Gateway</span>
        </button>

        <div class="output-box mono" id="test-output" role="region" aria-live="polite">Ready. Select a model tier or use "auto" to test live routing.</div>
      </div>

      <!-- Column 2: Zero-Name 32-Repo Skill Router Inspector -->
      <div class="card">
        <div class="section-bar">
          <div class="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--purple)" stroke-width="2.2" aria-hidden="true"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            Zero-Name 32-Repo Skill Router
          </div>
          <span class="mono" style="font-size: 0.7rem; color: var(--purple);">1,041 SKILL.md</span>
        </div>

        <label class="field-label" for="skill-query">Test Natural-Language Task (No Repo Names Needed)</label>
        <input type="text" id="skill-query" value="Design a macOS dashboard card with smooth spring animations" placeholder="Describe any coding, UI, Go, security, or SEO task...">

        <div class="chips-row">
          <button type="button" class="chip" onclick="testSkillRoute('Design a macOS dashboard card with smooth spring animations')">Apple HIG + Motion</button>
          <button type="button" class="chip" onclick="testSkillRoute('Write a Golang HTTP API server and audit XSS vulnerabilities')">Go + Strix Pentest</button>
          <button type="button" class="chip" onclick="testSkillRoute('Audit landing page SEO and deslop marketing copy')">SEO + Deslop</button>
        </div>

        <button type="button" class="btn btn-ghost" style="width: 100%;" onclick="testSkillRoute()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>
          Inspect Auto-Activated Repos & Skills
        </button>

        <div class="route-box" id="skill-output" role="region" aria-live="polite">
          <div style="color: var(--text-muted); font-size: 0.78rem;">Evaluating task intent...</div>
        </div>
      </div>

      <!-- Column 3: Spend Breakdown, Post-Mortems & Graphify AST Explorer -->
      <div class="card">
        <div class="section-bar">
          <div class="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2.2" aria-hidden="true"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
            Telemetry, Memory & AST
          </div>
          <div class="tab-group" role="tablist">
            <button type="button" class="tab-btn active" id="tab-spend-btn" onclick="switchTab('spend')">Spend</button>
            <button type="button" class="tab-btn" id="tab-pm-btn" onclick="switchTab('pm')">Post-Mortems</button>
            <button type="button" class="tab-btn" id="tab-ast-btn" onclick="switchTab('ast')">Graphify AST</button>
          </div>
        </div>

        <div id="tab-spend-view" style="overflow-x: auto; max-height: 365px;">
          <table id="spend-table">
            <thead>
              <tr>
                <th>Model Engine</th>
                <th>Reqs</th>
                <th>Tokens</th>
                <th>Cost (USD)</th>
              </tr>
            </thead>
            <tbody id="spend-tbody">
              <tr><td colspan="4" style="color: var(--text-muted);">Loading spend telemetry...</td></tr>
            </tbody>
          </table>
        </div>

        <div id="tab-pm-view" style="display: none; max-height: 365px; overflow-y: auto;">
          <div id="pm-list" style="font-size: 0.78rem; color: var(--text-secondary);">No post-mortem regressions recorded.</div>
        </div>

        <div id="tab-ast-view" style="display: none; max-height: 365px; overflow-y: auto;">
          <div style="display: flex; gap: 8px; margin-bottom: 10px;">
            <button type="button" class="btn" style="flex: 1; font-size: 0.76rem; padding: 6px 10px;" onclick="window.open('/graphify', '_blank')">
              Open Interactive Graph.html ↗
            </button>
            <button type="button" class="btn btn-ghost" style="flex: 1; font-size: 0.76rem; padding: 6px 10px;" onclick="window.open('/graphify/report', '_blank')">
              Open GRAPH_REPORT.md ↗
            </button>
          </div>
          <label class="field-label" for="ast-query-input">Query Graphify AST Knowledge Graph</label>
          <div style="display: flex; gap: 8px; margin-bottom: 8px;">
            <input type="text" id="ast-query-input" value="invoke_model_with_fallback" placeholder="Search symbol, function, or module..." style="margin-bottom: 0;">
            <button type="button" class="btn btn-ghost" onclick="runAstQuery()">Query</button>
          </div>
          <div class="route-box mono" id="ast-query-output" style="font-size: 0.73rem; min-height: 150px; white-space: pre-wrap;">Tap "Query" or click "Open Interactive Graph.html ↗" above to explore the full 2,397-node AST graph.</div>
        </div>
      </div>
    </section>
  </main>

  <!-- How It Works & Cross-Platform Setup Guide Modal -->
  <div class="modal-backdrop" id="guide-modal" role="dialog" aria-modal="true" aria-labelledby="guide-modal-title" onclick="if(event.target===this) closeGuideModal()">
    <div class="modal-panel">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">
        <div>
          <h2 id="guide-modal-title" style="font-size: 1.15rem; font-weight: 700; color: var(--text);">How the Antigravity Autonomous Workstation Works</h2>
          <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 2px;">Architecture, Automatic Chat Routing, Hardware-Adaptive Ollama & Personal Repo Isolation</div>
        </div>
        <button class="btn btn-ghost" onclick="closeGuideModal()">Close ✕</button>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; font-size: 0.82rem; color: var(--text-secondary); line-height: 1.55;">
        <div style="background: var(--surface-inset); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 14px;">
          <div style="color: var(--accent); font-weight: 700; margin-bottom: 6px;">1. Zero-Name Automatic Request Routing</div>
          Every prompt you type in Antigravity, Claude Code, Cursor, or Aider is intercepted by <code>tools/pre_invocation_hook.py</code> and <code>tools/skill_router.py</code>. It automatically classifies task complexity across <strong>5 Model Tiers</strong> and injects the top matching <code>SKILL.md</code> runbooks from all <strong>32 installed repositories (456+ skills)</strong> without you ever typing a repo name.
        </div>

        <div style="background: var(--surface-inset); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 14px;">
          <div style="color: var(--success); font-weight: 700; margin-bottom: 6px;">2. Hardware-Adaptive Ollama LLM Installer</div>
          When installed on any PC or Mac via <code>.\\install.ps1</code> or <code>./install.sh</code>, <code>tools/setup_wizard.py</code> inspects your OS, CPU cores, RAM, and GPU (Apple Metal, NVIDIA CUDA, AMD Vulkan) and automatically pulls the optimal local Ollama model (<code>llama3.2:1b</code>, <code>qwen2.5-coder:7b</code>, <code>14b</code>, or <code>32b</code>).
        </div>

        <div style="background: var(--surface-inset); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 14px;">
          <div style="color: var(--purple); font-weight: 700; margin-bottom: 6px;">3. 1-Click Graphify AST Knowledge Graph</div>
          Clicking the <strong>Graphify AST Graph</strong> card opens the interactive 2,397-node AST visualization (<code>/graphify</code> &rarr; <code>graphify-out/graph.html</code>) or the architecture report (<code>/graphify/report</code> &rarr; <code>GRAPH_REPORT.md</code>).
        </div>

        <div style="background: var(--surface-inset); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 14px;">
          <div style="color: var(--warning); font-weight: 700; margin-bottom: 6px;">4. Strict Personal & Private Repo Isolation</div>
          All 32 curated repositories live strictly inside the workstation's <code>tools/</code> folder. The workstation never clones or writes <code>graphify-out/</code> files into your personal or private repositories, and <code>ggshield</code> blocks any secret leakage before <code>git commit</code>.
        </div>
      </div>

      <div style="margin-top: 14px; background: var(--surface-inset); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 12px 14px;">
        <div style="font-size: 0.74rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 6px;">Quick Commands (Any Terminal)</div>
        <div class="mono" style="font-size: 0.76rem; color: var(--text); display: grid; gap: 4px;">
          <div><span style="color: var(--accent);">python tools/setup_wizard.py</span> — Interactive Hardware + Ollama + API Key + 32-Repo Setup Wizard</div>
          <div><span style="color: var(--success);">python orchestrate.py --guide</span> — Print full architectural guide in terminal</div>
          <div><span style="color: var(--purple);">python tools/skill_router.py "your task"</span> — Test Zero-Name 32-Repo Skill Router</div>
          <div><span style="color: var(--warning);">python tools/manage_tools.py sync</span> — Clone or update all 32 GitHub repositories</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Personal API Keys & 1-Click AWS Auto-Setup Modal -->
  <div class="modal-backdrop" id="keys-modal" role="dialog" aria-modal="true" aria-labelledby="keys-modal-title" onclick="if(event.target===this) closeKeysModal()">
    <div class="modal-panel" style="max-width: 680px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">
        <div>
          <h2 id="keys-modal-title" style="font-size: 1.12rem; font-weight: 700; color: var(--text);">Personal API Keys &amp; Cloud Auto-Setup</h2>
          <div style="font-size: 0.76rem; color: var(--text-muted); margin-top: 2px;">Stored exclusively in your local git-ignored <code>.env</code> (<code>0600</code> permissions) • Hot-reloads instantly</div>
        </div>
        <button class="btn btn-ghost" onclick="closeKeysModal()">Close ✕</button>
      </div>

      <div style="background: var(--surface-inset); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 12px 14px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;">
        <div>
          <div style="font-size: 0.82rem; font-weight: 700; color: var(--accent);">AWS CLI Login Auto-Detector &amp; Key Creator</div>
          <div style="font-size: 0.74rem; color: var(--text-secondary);" id="aws-status-line">Detects local ~/.aws login, creates a dedicated workstation IAM profile, and enables Claude Sonnet 4.6 / Opus 4.5 / DeepSeek R1.</div>
        </div>
        <button type="button" class="btn" onclick="autoConfigureAws()" id="aws-auto-btn">Auto-Setup AWS Bedrock</button>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div>
          <label class="field-label" for="cfg-nvidia">NVIDIA NIM API Key (<span class="mono" id="mask-nvidia">not set</span>)</label>
          <input type="password" id="cfg-nvidia" placeholder="nvapi-... (Leave blank to keep current)">
        </div>
        <div>
          <label class="field-label" for="cfg-openrouter">OpenRouter API Key (<span class="mono" id="mask-openrouter">not set</span>)</label>
          <input type="password" id="cfg-openrouter" placeholder="sk-or-v1-... (Leave blank to keep current)">
        </div>
        <div>
          <label class="field-label" for="cfg-deepseek">DeepSeek API Key (<span class="mono" id="mask-deepseek">not set</span>)</label>
          <input type="password" id="cfg-deepseek" placeholder="sk-... (Leave blank to keep current)">
        </div>
        <div>
          <label class="field-label" for="cfg-groq">Groq API Key (<span class="mono" id="mask-groq">not set</span>)</label>
          <input type="password" id="cfg-groq" placeholder="gsk_... (Leave blank to keep current)">
        </div>
        <div>
          <label class="field-label" for="cfg-openai">OpenAI API Key (<span class="mono" id="mask-openai">not set</span>)</label>
          <input type="password" id="cfg-openai" placeholder="sk-proj-... (Leave blank to keep current)">
        </div>
        <div>
          <label class="field-label" for="cfg-aws-profile">AWS Profile (<span class="mono" id="mask-aws">not set</span>)</label>
          <input type="text" id="cfg-aws-profile" placeholder="e.g. antigravity-workstation or default">
        </div>
      </div>

      <div id="keys-save-msg" class="mono" style="font-size: 0.76rem; color: var(--success); margin-top: 6px; min-height: 18px;"></div>

      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px;">
        <button type="button" class="btn btn-ghost" onclick="closeKeysModal()">Cancel</button>
        <button type="button" class="btn" onclick="saveApiKeys()">Save to Local .env &amp; Hot-Reload</button>
      </div>
    </div>
  </div>

  <script>
    let pollingActive = true;
    let pollTimer = null;

    function openGuideModal() {
      document.getElementById('guide-modal').classList.add('open');
    }

    function closeGuideModal() {
      document.getElementById('guide-modal').classList.remove('open');
    }

    async function openKeysModal() {
      document.getElementById('keys-modal').classList.add('open');
      document.getElementById('keys-save-msg').innerText = '';
      try {
        const r = await fetch('/v1/config/status');
        const d = await r.json();
        document.getElementById('mask-nvidia').innerText = d.nvidia || 'not set';
        document.getElementById('mask-openrouter').innerText = d.openrouter || 'not set';
        document.getElementById('mask-deepseek').innerText = d.deepseek || 'not set';
        document.getElementById('mask-groq').innerText = d.groq || 'not set';
        document.getElementById('mask-openai').innerText = d.openai || 'not set';
        document.getElementById('mask-aws').innerText = d.aws_profile || 'not set';
        if (d.aws_profile) document.getElementById('cfg-aws-profile').value = d.aws_profile;
      } catch (e) {}
    }

    function closeKeysModal() {
      document.getElementById('keys-modal').classList.remove('open');
    }

    async function saveApiKeys() {
      const msg = document.getElementById('keys-save-msg');
      msg.style.color = 'var(--accent)';
      msg.innerText = 'Saving credentials to local .env and hot-reloading gateway...';
      try {
        const payload = {
          nvidia_api_key: document.getElementById('cfg-nvidia').value.trim(),
          openrouter_api_key: document.getElementById('cfg-openrouter').value.trim(),
          deepseek_api_key: document.getElementById('cfg-deepseek').value.trim(),
          groq_api_key: document.getElementById('cfg-groq').value.trim(),
          openai_api_key: document.getElementById('cfg-openai').value.trim(),
          aws_profile: document.getElementById('cfg-aws-profile').value.trim()
        };
        const r = await fetch('/v1/config/keys', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const d = await r.json();
        msg.style.color = 'var(--success)';
        msg.innerText = d.message || 'Saved & hot-reloaded!';
        ['cfg-nvidia','cfg-openrouter','cfg-deepseek','cfg-groq','cfg-openai'].forEach(id => {
          document.getElementById(id).value = '';
        });
        await openKeysModal();
        fetchStats();
      } catch (e) {
        msg.style.color = 'var(--danger)';
        msg.innerText = 'Error saving keys: ' + e.message;
      }
    }

    async function autoConfigureAws() {
      const msg = document.getElementById('keys-save-msg');
      const btn = document.getElementById('aws-auto-btn');
      btn.disabled = true;
      msg.style.color = 'var(--accent)';
      msg.innerText = 'Detecting local AWS CLI login & provisioning workstation Bedrock profile...';
      try {
        const r = await fetch('/v1/config/aws-auto', {method: 'POST'});
        const d = await r.json();
        msg.style.color = d.status === 'ok' ? 'var(--success)' : 'var(--warning)';
        msg.innerText = d.message || 'Completed';
        await openKeysModal();
        fetchStats();
      } catch (e) {
        msg.style.color = 'var(--danger)';
        msg.innerText = 'AWS auto-setup error: ' + e.message;
      } finally {
        btn.disabled = false;
      }
    }

    function togglePolling() {
      pollingActive = !pollingActive;
      const lbl = document.getElementById('pause-label');
      lbl.innerText = pollingActive ? 'Live: 5s' : 'Paused';
    }

    function selectTier(tier, btnEl) {
      document.getElementById('test-model').value = tier;
      document.querySelectorAll('.tier-card').forEach(el => el.classList.remove('selected'));
      if (btnEl) btnEl.classList.add('selected');
      document.getElementById('routed-badge').innerText = `target: ${tier}`;
    }

    function setPrompt(model, text) {
      document.getElementById('test-model').value = model;
      document.getElementById('test-prompt').value = text;
      document.querySelectorAll('.tier-card').forEach(el => el.classList.remove('selected'));
    }

    function switchTab(tab) {
      document.getElementById('tab-spend-view').style.display = tab === 'spend' ? 'block' : 'none';
      document.getElementById('tab-pm-view').style.display = tab === 'pm' ? 'block' : 'none';
      document.getElementById('tab-ast-view').style.display = tab === 'ast' ? 'block' : 'none';
      document.getElementById('tab-spend-btn').classList.toggle('active', tab === 'spend');
      document.getElementById('tab-pm-btn').classList.toggle('active', tab === 'pm');
      document.getElementById('tab-ast-btn').classList.toggle('active', tab === 'ast');
      if (tab === 'ast') runAstQuery();
    }

    async function runAstQuery() {
      const q = document.getElementById('ast-query-input').value.trim();
      const out = document.getElementById('ast-query-output');
      out.innerText = 'Querying Graphify AST...';
      try {
        const r = await fetch('/v1/graphify/query?q=' + encodeURIComponent(q));
        const d = await r.json();
        out.innerText = d.output || 'No matching AST nodes found.';
      } catch (e) {
        out.innerText = 'Error querying Graphify AST: ' + e.message;
      }
    }

    async function testSkillRoute(presetQuery) {
      const inputEl = document.getElementById('skill-query');
      if (presetQuery) inputEl.value = presetQuery;
      const q = inputEl.value.trim();
      const box = document.getElementById('skill-output');
      box.innerHTML = '<div class="mono" style="color: var(--text-muted); font-size: 0.76rem;">Routing across 32 repositories...</div>';
      try {
        const resp = await fetch('/v1/skills/route?q=' + encodeURIComponent(q));
        const data = await resp.json();
        const repos = data.matched_repos || [];
        const skills = data.matched_skills || [];
        const domains = data.matched_domains || [];
        if (repos.length === 0 && skills.length === 0) {
          box.innerHTML = '<div style="color: var(--text-muted); font-size: 0.78rem;">No specialized domain match — routes to default Core Coding Engine.</div>';
          return;
        }
        let html = '<div style="margin-bottom: 8px; font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Matched Domains (' + domains.length + ')</div>';
        html += '<div style="margin-bottom: 10px; font-size: 0.78rem; color: var(--text);">' + domains.join(' • ') + '</div>';
        html += '<div style="margin-bottom: 6px; font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Auto-Activated Repos (' + repos.length + ')</div>';
        html += '<div style="margin-bottom: 10px;">' + repos.map(r => `<span class="repo-tag mono">${r}</span>`).join('') + '</div>';
        html += '<div style="margin-bottom: 6px; font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Injected SKILL.md Runbooks</div>';
        html += skills.map(s => `<div class="skill-tag mono">tools/${s}</div>`).join('');
        box.innerHTML = html;
      } catch (e) {
        box.innerHTML = `<div style="color: var(--danger); font-size: 0.78rem;">Router error: ${e.message}</div>`;
      }
    }

    async function fetchStats() {
      const startT = performance.now();
      try {
        const hResp = await fetch('/health');
        const hData = await hResp.json();
        const lat = Math.round(performance.now() - startT);
        document.getElementById('latency-ms').innerText = `${lat}ms ping`;
        document.getElementById('status-text').innerText = `ONLINE • ${lat}ms PING`;
        const prov = hData.providers || {};
        document.getElementById('pill-bedrock').classList.toggle('active', !!prov.bedrock);
        document.getElementById('pill-ollama').classList.toggle('active', !!prov.ollama);
        const anyByok = prov.openrouter || prov.nvidia || prov.deepseek || prov.groq || prov.openai;
        document.getElementById('pill-byok').classList.toggle('active', !!anyByok);
      } catch (e) {
        document.getElementById('status-text').innerText = 'OFFLINE';
      }

      try {
        const uResp = await fetch('/v1/usage');
        const uData = await uResp.json();
        const totals = uData.totals || {};
        const totalUsd = totals.estimated_usd || 0;
        const reqs = totals.requests || 0;
        const pTok = totals.prompt_tokens || 0;
        const cTok = totals.completion_tokens || 0;
        const allTok = pTok + cTok;

        document.getElementById('total-usd').innerText = `$${totalUsd.toFixed(4)}`;
        document.getElementById('requests-count').innerText = `${reqs} requests`;
        document.getElementById('avg-cost').innerText = reqs > 0 ? `$${(totalUsd / reqs).toFixed(4)}/req` : '$0.000/req';
        document.getElementById('total-tokens').innerText = allTok.toLocaleString();
        document.getElementById('tokens-sub').innerText = `${pTok.toLocaleString()} prompt / ${cTok.toLocaleString()} completion`;

        const opusCost = (pTok * 15.0 / 1e6) + (cTok * 75.0 / 1e6);
        const saved = Math.max(0, opusCost - totalUsd);
        const pct = opusCost > 0 ? Math.min(99.9, (saved / opusCost) * 100) : 97.8;
        document.getElementById('saved-usd').innerText = `$${saved.toFixed(4)}`;
        document.getElementById('savings-pct').innerText = `${pct.toFixed(1)}% saved`;
        document.getElementById('savings-bar').style.width = `${pct}%`;

        const tbody = document.getElementById('spend-tbody');
        tbody.innerHTML = '';
        const byModel = uData.by_model || {};
        if (Object.keys(byModel).length === 0) {
          tbody.innerHTML = '<tr><td colspan="4" style="color: var(--text-muted);">No requests logged yet.</td></tr>';
        } else {
          for (const [m, stat] of Object.entries(byModel)) {
            const shortName = m.replace('us.meta.', '').replace('us.anthropic.', '').replace('us.deepseek.', '');
            const mToks = (stat.prompt_tokens || 0) + (stat.completion_tokens || 0);
            const mCost = stat.estimated_usd || 0;
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td class="mono" style="color: var(--accent); font-size: 0.75rem;" title="${m}">${shortName}</td>
              <td class="tabular">${stat.requests}</td>
              <td class="tabular">${mToks.toLocaleString()}</td>
              <td class="tabular" style="color: var(--success); font-weight: 600;">$${mCost.toFixed(4)}</td>
            `;
            tbody.appendChild(tr);
          }
        }
      } catch (e) {}

      try {
        const gResp = await fetch('/v1/graph');
        const gData = await gResp.json();
        if (gData.nodes) {
          document.getElementById('graph-nodes').innerText = `${gData.nodes.toLocaleString()} Nodes`;
          document.getElementById('graph-sub').innerText = `${(gData.edges || 0).toLocaleString()} edges • Tap to open`;
        }
      } catch (e) {}

      try {
        const hwResp = await fetch('/v1/hardware');
        const hw = await hwResp.json();
        if (hw && hw.os) {
          document.getElementById('hw-summary').innerText = `${hw.os} (${hw.arch}) • ${hw.cpu_cores} Cores • ${hw.ram_gb} GB RAM • ${hw.gpu_name}`;
          document.getElementById('hw-model-pill').innerText = (hw.recommended_models || [hw.primary_local_model]).join(' + ');
        }
      } catch (e) {}

      try {
        const lrResp = await fetch('/v1/last-route');
        const lr = await lrResp.json();
        if (lr && lr.tier) {
          const repos = (lr.matched_repos && lr.matched_repos.length > 0) ? lr.matched_repos.slice(0, 4).join(', ') : 'Core Engine';
          document.getElementById('live-route-summary').innerText = `Repos: ${repos} • Prompt: "${(lr.prompt_preview || '').slice(0, 65)}..."`;
          document.getElementById('live-route-tier').innerText = `TIER: ${lr.tier.toUpperCase()}`;
        }
      } catch (e) {}

      try {
        const pmResp = await fetch('/v1/postmortems');
        const pmData = await pmResp.json();
        const pms = pmData.postmortems || [];
        const pmList = document.getElementById('pm-list');
        if (pms.length === 0) {
          pmList.innerHTML = '<div style="color: var(--success);">Zero active regressions recorded. Workspace clean.</div>';
        } else {
          pmList.innerHTML = pms.slice().reverse().slice(0, 8).map(item => `
            <div style="padding: 8px 10px; border-bottom: 1px solid var(--border);">
              <div class="mono" style="font-size: 0.68rem; color: var(--warning);">${item.timestamp || ''}</div>
              <div style="font-weight: 600; color: var(--text); margin-top: 2px;">${item.task || ''}</div>
              <div class="mono" style="font-size: 0.72rem; color: var(--text-muted); margin-top: 2px;">${item.error || ''}</div>
            </div>
          `).join('');
        }
      } catch (e) {}
    }

    
    let currentSelectedAgent = 'claude';

    function selectAgent(agentName) {
      currentSelectedAgent = agentName;
      ['claude', 'codex', 'aider', 'opendots', 'orchestrator'].forEach(a => {
        const el = document.getElementById('agent-card-' + a);
        if (el) el.classList.toggle('active', a === agentName);
      });

      const label = document.getElementById('agent-input-label');
      const input = document.getElementById('agent-chat-prompt');
      const cliCmd = document.getElementById('agent-cli-cmd');
      const opendotsPanel = document.getElementById('opendots-extra-panel');

      if (opendotsPanel) {
        opendotsPanel.style.display = agentName === 'opendots' ? 'block' : 'none';
      }

      const agentMeta = {
        claude: {
          label: 'Chat or Dispatch Task to Claude Code (Bedrock Opus 4.6)',
          placeholder: 'Ask Claude Code to build features, inspect code, or architect solutions...',
          cli: 'claude -p "<task>"'
        },
        codex: {
          label: 'Chat or Dispatch Task to OpenAI Codex (ChatGPT gpt-5.6-terra)',
          placeholder: 'Instruct Codex to write, refactor, or test code in the elevated sandbox...',
          cli: 'codex exec "<task>"'
        },
        aider: {
          label: 'Chat or Dispatch Task to Aider (5-Tier Gateway Router)',
          placeholder: 'Ask Aider to edit files with automatic commit tracking and model routing...',
          cli: 'aider --model openai/auto --message "<task>"'
        },
        opendots: {
          label: 'Interact with OpenDots CopilotKit UI Canvas & Channels',
          placeholder: 'Ask OpenDots to generate UI states, interact with visual canvas dots, or query channels...',
          cli: 'cd tools/OpenDots && npm run dev'
        },
        orchestrator: {
          label: 'Dispatch Task to Autonomous Orchestrator (AST + ggshield Shield)',
          placeholder: 'Describe a multi-agent task to orchestrate across AST, model tiers, and security sensors...',
          cli: 'python orchestrate.py --task "<task>"'
        }
      };

      if (agentMeta[agentName]) {
        if (label) label.innerText = agentMeta[agentName].label;
        if (input) input.placeholder = agentMeta[agentName].placeholder;
        if (cliCmd) cliCmd.innerText = agentMeta[agentName].cli;
      }
    }

    function setAgentChipPrompt(text) {
      const input = document.getElementById('agent-chat-prompt');
      if (input) {
        input.value = text;
        input.focus();
      }
    }

    function clearAgentConsole() {
      const consoleEl = document.getElementById('agent-output-console');
      if (consoleEl) consoleEl.innerText = 'Console cleared. Select an agent and tap "Chat / Dispatch" to start a run.';
      document.getElementById('agent-chat-status').innerText = 'Ready for input';
    }

    function copyAgentConsole() {
      const consoleEl = document.getElementById('agent-output-console');
      if (consoleEl && consoleEl.innerText) {
        navigator.clipboard.writeText(consoleEl.innerText);
        const st = document.getElementById('agent-chat-status');
        if (st) {
          const old = st.innerText;
          st.innerText = '✓ Copied to clipboard!';
          setTimeout(() => st.innerText = old, 2000);
        }
      }
    }

    async function sendAgentMessage() {
      const input = document.getElementById('agent-chat-prompt');
      const msg = input.value.trim();
      if (!msg) {
        alert('Please enter a prompt or instruction for ' + currentSelectedAgent);
        return;
      }

      const model = document.getElementById('agent-model-select').value;
      const statusEl = document.getElementById('agent-chat-status');
      const consoleEl = document.getElementById('agent-output-console');
      const sendBtn = document.getElementById('btn-agent-send');

      sendBtn.disabled = true;
      sendBtn.innerHTML = '<span class="dot" style="display:inline-block;animation:pulse 1s infinite;"></span> Executing...';
      statusEl.innerText = `Dispatching to ${currentSelectedAgent.toUpperCase()}...`;
      consoleEl.innerText = `[${new Date().toLocaleTimeString()}] Dispatching task to ${currentSelectedAgent.toUpperCase()}...
> Prompt: ${msg}

Waiting for response from agent runner...
`;

      const startT = performance.now();
      try {
        const r = await fetch('/v1/agents/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            agent: currentSelectedAgent,
            message: msg,
            model: model
          })
        });
        const data = await r.json();
        const durationSec = ((performance.now() - startT) / 1000).toFixed(2);

        if (r.ok && data.status === 'ok') {
          consoleEl.innerText = `[${new Date().toLocaleTimeString()} • ${durationSec}s • Exit: ${data.exit_code}]

${data.response}`;
          statusEl.innerText = `Completed in ${durationSec}s`;
        } else {
          consoleEl.innerText = `[ERROR • ${durationSec}s]
${data.response || data.detail || JSON.stringify(data, null, 2)}`;
          statusEl.innerText = 'Execution error';
        }
      } catch (err) {
        consoleEl.innerText = `[Network Error]: ${err.message}`;
        statusEl.innerText = 'Request failed';
      } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg> Chat / Dispatch';
      }
    }

    async function triggerAutoConfig() {
      const btn = document.getElementById('btn-auto-config');
      const badge = document.getElementById('auto-config-status-badge');
      if (btn) {
        btn.disabled = true;
        btn.innerText = '⚡ Auto-Configuring...';
      }
      if (badge) badge.innerText = 'Configuring all agents...';

      try {
        const r = await fetch('/v1/config/auto-configure', {method: 'POST'});
        const d = await r.json();
        if (badge) {
          badge.innerText = '✓ All 5 Agents Auto-Configured';
          badge.style.color = 'var(--success)';
        }
        await fetchAgentStatus();
      } catch (err) {
        if (badge) {
          badge.innerText = 'Config notice: ' + err.message;
          badge.style.color = 'var(--warning)';
        }
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerText = '⚡ Auto-Configure All Agents';
        }
      }
    }

    async function configureOpenDots() {
      try {
        const r = await fetch('/v1/opendots/configure', {method: 'POST'});
        const d = await r.json();
        alert('OpenDots configured! Linked to http://127.0.0.1:8000/v1.\n\nTo launch UI canvas: cd tools/OpenDots && npm run dev');
        fetchAgentStatus();
      } catch (err) {
        alert('OpenDots configuration notice: ' + err.message);
      }
    }

    async function fetchAgentStatus() {
      try {
        const r = await fetch('/v1/agents/status');
        if (!r.ok) return;
        const d = await r.json();

        // Claude status
        if (d.claude) {
          const pill = document.getElementById('status-pill-claude');
          if (pill) {
            pill.innerText = d.claude.configured ? 'ONLINE' : 'PENDING';
            pill.className = 'agent-status-pill ' + (d.claude.configured ? 'status-online' : 'status-pending');
          }
          const mod = document.getElementById('badge-claude-model');
          if (mod) mod.innerText = d.claude.model ? d.claude.model.replace('us.anthropic.', '') : 'Opus 4.6';
          const prof = document.getElementById('badge-claude-prof');
          if (prof) prof.innerText = d.claude.profile || 'Bedrock Active';
        }

        // Codex status
        if (d.codex) {
          const pill = document.getElementById('status-pill-codex');
          if (pill) {
            pill.innerText = d.codex.authenticated ? 'ONLINE' : 'READY';
            pill.className = 'agent-status-pill ' + (d.codex.authenticated ? 'status-online' : 'status-pending');
          }
          const mod = document.getElementById('badge-codex-model');
          if (mod) mod.innerText = d.codex.model || 'gpt-5.6-terra';
        }

        // Aider status
        if (d.aider) {
          const pill = document.getElementById('status-pill-aider');
          if (pill) {
            pill.innerText = d.aider.configured ? 'ONLINE' : 'PENDING';
            pill.className = 'agent-status-pill ' + (d.aider.configured ? 'status-online' : 'status-pending');
          }
        }

        // OpenDots status
        if (d.opendots) {
          const pill = document.getElementById('status-pill-opendots');
          if (pill) {
            pill.innerText = d.opendots.configured ? 'READY' : 'PENDING';
            pill.className = 'agent-status-pill ' + (d.opendots.configured ? 'status-online' : 'status-pending');
          }
        }
      } catch (e) {
        console.warn('Agent status fetch:', e);
      }
    }

/* ==========================================================================
       MULTI-AGENT DESIGN STUDIO & OPENDOTS ENGINE JAVASCRIPT
       ========================================================================== */
    let currentAgent = 'claude';
    let currentStudioMode = 'design';
    let activeComponentHtml = '';

    // Base64-encoded Apple HIG Music Player (100% immune to HTML parser tag conflicts)
    const SHOWCASE_B64 = "PCFET0NUWVBFIGh0bWw+CjxodG1sIGxhbmc9ImVuIj4KPGhlYWQ+CiAgPG1ldGEgY2hhcnNldD0iVVRGLTgiPgogIDxtZXRhIG5hbWU9InZpZXdwb3J0IiBjb250ZW50PSJ3aWR0aD1kZXZpY2Utd2lkdGgsIGluaXRpYWwtc2NhbGU9MS4wIj4KICA8dGl0bGU+QXBwbGUgSElHIExpcXVpZC1HbGFzcyBNdXNpYyBQbGF5ZXI8L3RpdGxlPgogIDxsaW5rIHJlbD0icHJlY29ubmVjdCIgaHJlZj0iaHR0cHM6Ly9mb250cy5nb29nbGVhcGlzLmNvbSI+CiAgPGxpbmsgcmVsPSJwcmVjb25uZWN0IiBocmVmPSJodHRwczovL2ZvbnRzLmdzdGF0aWMuY29tIiBjcm9zc29yaWdpbj4KICA8bGluayBocmVmPSJodHRwczovL2ZvbnRzLmdvb2dsZWFwaXMuY29tL2NzczI/ZmFtaWx5PVBsdXMrSmFrYXJ0YStTYW5zOndnaHRANDAwOzUwMDs2MDA7NzAwOzgwMCZmYW1pbHk9SmV0QnJhaW5zK01vbm86d2dodEA0MDA7NTAwJmRpc3BsYXk9c3dhcCIgcmVsPSJzdHlsZXNoZWV0Ij4KICA8c3R5bGU+CiAgICA6cm9vdCB7CiAgICAgIC0tYmc6ICMwOTBkMTY7CiAgICAgIC0tZ2xhc3M6IHJnYmEoMTgsIDI0LCAzOCwgMC43NSk7CiAgICAgIC0tZ2xhc3MtYm9yZGVyOiByZ2JhKDI1NSwgMjU1LCAyNTUsIDAuMTQpOwogICAgICAtLWFjY2VudDogIzM4YmRmODsKICAgICAgLS1hY2NlbnQtZ2xvdzogcmdiYSg1NiwgMTg5LCAyNDgsIDAuMzUpOwogICAgICAtLXBpbms6ICNmNDcyYjY7CiAgICAgIC0tdGV4dDogI2Y4ZmFmYzsKICAgICAgLS10ZXh0LW11dGVkOiAjOTRhM2I4OwogICAgICAtLXNwcmluZzogY3ViaWMtYmV6aWVyKDAuMjMsIDEsIDAuMzIsIDEpOwogICAgfQogICAgKiB7IGJveC1zaXppbmc6IGJvcmRlci1ib3g7IG1hcmdpbjogMDsgcGFkZGluZzogMDsgfQogICAgYm9keSB7CiAgICAgIGJhY2tncm91bmQ6IHJhZGlhbC1ncmFkaWVudChlbGxpcHNlIDkwJSA3MCUgYXQgNTAlIDEwJSwgIzFlMWI0YiAwJSwgIzA5MGQxNiA4MCUpOwogICAgICBjb2xvcjogdmFyKC0tdGV4dCk7CiAgICAgIGZvbnQtZmFtaWx5OiAiUGx1cyBKYWthcnRhIFNhbnMiLCAtYXBwbGUtc3lzdGVtLCBzYW5zLXNlcmlmOwogICAgICBtaW4taGVpZ2h0OiAxMDB2aDsKICAgICAgZGlzcGxheTogZmxleDsKICAgICAgYWxpZ24taXRlbXM6IGNlbnRlcjsKICAgICAganVzdGlmeS1jb250ZW50OiBjZW50ZXI7CiAgICAgIHBhZGRpbmc6IDI0cHg7CiAgICB9CiAgICAucGxheWVyLWNhcmQgewogICAgICBiYWNrZ3JvdW5kOiB2YXIoLS1nbGFzcyk7CiAgICAgIGJhY2tkcm9wLWZpbHRlcjogYmx1cigyOHB4KSBzYXR1cmF0ZSgxOTAlKTsKICAgICAgLXdlYmtpdC1iYWNrZHJvcC1maWx0ZXI6IGJsdXIoMjhweCkgc2F0dXJhdGUoMTkwJSk7CiAgICAgIGJvcmRlcjogMXB4IHNvbGlkIHZhcigtLWdsYXNzLWJvcmRlcik7CiAgICAgIGJvcmRlci1yYWRpdXM6IDI4cHg7CiAgICAgIHBhZGRpbmc6IDI0cHg7CiAgICAgIHdpZHRoOiAxMDAlOwogICAgICBtYXgtd2lkdGg6IDM2MHB4OwogICAgICBib3gtc2hhZG93OiAwIDI0cHggNjBweCAtMTJweCByZ2JhKDAsIDAsIDAsIDAuNzUpLCBpbnNldCAwIDFweCAwIHJnYmEoMjU1LCAyNTUsIDI1NSwgMC4xOCk7CiAgICAgIHRyYW5zaXRpb246IHRyYW5zZm9ybSAwLjRzIHZhcigtLXNwcmluZyksIGJveC1zaGFkb3cgMC40cyB2YXIoLS1zcHJpbmcpOwogICAgfQogICAgLnBsYXllci1jYXJkOmhvdmVyIHsKICAgICAgdHJhbnNmb3JtOiB0cmFuc2xhdGVZKC00cHgpIHNjYWxlKDEuMDEpOwogICAgICBib3gtc2hhZG93OiAwIDMycHggNzBweCAtMTJweCByZ2JhKDU2LCAxODksIDI0OCwgMC4yNSksIGluc2V0IDAgMXB4IDAgcmdiYSgyNTUsIDI1NSwgMjU1LCAwLjI1KTsKICAgIH0KICAgIC5hbGJ1bS1hcnQtd3JhcCB7CiAgICAgIHBvc2l0aW9uOiByZWxhdGl2ZTsKICAgICAgd2lkdGg6IDEwMCU7CiAgICAgIHBhZGRpbmctdG9wOiAxMDAlOwogICAgICBib3JkZXItcmFkaXVzOiAyMHB4OwogICAgICBvdmVyZmxvdzogaGlkZGVuOwogICAgICBtYXJnaW4tYm90dG9tOiAyMHB4OwogICAgICBib3gtc2hhZG93OiAwIDE2cHggMzZweCAtOHB4IHJnYmEoMCwgMCwgMCwgMC41KTsKICAgIH0KICAgIC5hbGJ1bS1hcnQgewogICAgICBwb3NpdGlvbjogYWJzb2x1dGU7CiAgICAgIGluc2V0OiAwOwogICAgICBiYWNrZ3JvdW5kOiBsaW5lYXItZ3JhZGllbnQoMTM1ZGVnLCAjZWM0ODk5LCAjOGI1Y2Y2LCAjM2I4MmY2KTsKICAgICAgZGlzcGxheTogZmxleDsKICAgICAgYWxpZ24taXRlbXM6IGNlbnRlcjsKICAgICAganVzdGlmeS1jb250ZW50OiBjZW50ZXI7CiAgICB9CiAgICAuYWxidW0tYXJ0LnBsYXlpbmcgeyBhbmltYXRpb246IHJvdGF0ZS12aW55bCAxOHMgbGluZWFyIGluZmluaXRlOyB9CiAgICBAa2V5ZnJhbWVzIHJvdGF0ZS12aW55bCB7IGZyb20geyB0cmFuc2Zvcm06IHJvdGF0ZSgwZGVnKTsgfSB0byB7IHRyYW5zZm9ybTogcm90YXRlKDM2MGRlZyk7IH0gfQogICAgLnZpbnlsLWdyb292ZXMgewogICAgICBwb3NpdGlvbjogYWJzb2x1dGU7CiAgICAgIGluc2V0OiAxMnB4OwogICAgICBib3JkZXItcmFkaXVzOiA1MCU7CiAgICAgIGJvcmRlcjogMXB4IHNvbGlkIHJnYmEoMjU1LCAyNTUsIDI1NSwgMC4xNSk7CiAgICAgIGJveC1zaGFkb3c6IGluc2V0IDAgMCAyMHB4IHJnYmEoMCwwLDAsMC40KTsKICAgIH0KICAgIC52aW55bC1jb3JlIHsKICAgICAgd2lkdGg6IDY0cHg7CiAgICAgIGhlaWdodDogNjRweDsKICAgICAgYm9yZGVyLXJhZGl1czogNTAlOwogICAgICBiYWNrZ3JvdW5kOiAjMDkwZDE2OwogICAgICBib3JkZXI6IDNweCBzb2xpZCB2YXIoLS1hY2NlbnQpOwogICAgICBkaXNwbGF5OiBmbGV4OwogICAgICBhbGlnbi1pdGVtczogY2VudGVyOwogICAgICBqdXN0aWZ5LWNvbnRlbnQ6IGNlbnRlcjsKICAgICAgYm94LXNoYWRvdzogMCAwIDE2cHggdmFyKC0tYWNjZW50LWdsb3cpOwogICAgfQogICAgLnRyYWNrLWluZm8gewogICAgICBkaXNwbGF5OiBmbGV4OwogICAgICBqdXN0aWZ5LWNvbnRlbnQ6IHNwYWNlLWJldHdlZW47CiAgICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7CiAgICAgIG1hcmdpbi1ib3R0b206IDE2cHg7CiAgICB9CiAgICAudHJhY2stdGl0bGUgewogICAgICBmb250LXNpemU6IDEuMTVyZW07CiAgICAgIGZvbnQtd2VpZ2h0OiA3MDA7CiAgICAgIGNvbG9yOiB2YXIoLS10ZXh0KTsKICAgICAgbGV0dGVyLXNwYWNpbmc6IC0wLjAxNWVtOwogICAgfQogICAgLnRyYWNrLWFydGlzdCB7IGZvbnQtc2l6ZTogMC44MnJlbTsgY29sb3I6IHZhcigtLXRleHQtbXV0ZWQpOyBtYXJnaW4tdG9wOiAycHg7IH0KICAgIC5waWxsLWJhZGdlIHsKICAgICAgZm9udC1zaXplOiAwLjY1cmVtOwogICAgICBmb250LXdlaWdodDogNzAwOwogICAgICBwYWRkaW5nOiAzcHggOHB4OwogICAgICBib3JkZXItcmFkaXVzOiA5OTlweDsKICAgICAgYmFja2dyb3VuZDogcmdiYSg1NiwgMTg5LCAyNDgsIDAuMTUpOwogICAgICBjb2xvcjogdmFyKC0tYWNjZW50KTsKICAgICAgYm9yZGVyOiAxcHggc29saWQgcmdiYSg1NiwgMTg5LCAyNDgsIDAuMyk7CiAgICAgIHRleHQtdHJhbnNmb3JtOiB1cHBlcmNhc2U7CiAgICB9CiAgICAuc2NydWJiZXIgeyB3aWR0aDogMTAwJTsgbWFyZ2luLWJvdHRvbTogMThweDsgfQogICAgLnNjcnViYmVyLWJhciB7CiAgICAgIGhlaWdodDogNXB4OwogICAgICBiYWNrZ3JvdW5kOiByZ2JhKDI1NSwgMjU1LCAyNTUsIDAuMTIpOwogICAgICBib3JkZXItcmFkaXVzOiA5OTlweDsKICAgICAgcG9zaXRpb246IHJlbGF0aXZlOwogICAgICBjdXJzb3I6IHBvaW50ZXI7CiAgICAgIG92ZXJmbG93OiBoaWRkZW47CiAgICB9CiAgICAuc2NydWJiZXItZmlsbCB7CiAgICAgIGhlaWdodDogMTAwJTsKICAgICAgd2lkdGg6IDQyJTsKICAgICAgYmFja2dyb3VuZDogbGluZWFyLWdyYWRpZW50KDkwZGVnLCB2YXIoLS1hY2NlbnQpLCB2YXIoLS1waW5rKSk7CiAgICAgIGJvcmRlci1yYWRpdXM6IDk5OXB4OwogICAgfQogICAgLnRpbWUtbGFiZWxzIHsKICAgICAgZGlzcGxheTogZmxleDsKICAgICAganVzdGlmeS1jb250ZW50OiBzcGFjZS1iZXR3ZWVuOwogICAgICBmb250LXNpemU6IDAuNzJyZW07CiAgICAgIGNvbG9yOiB2YXIoLS10ZXh0LW11dGVkKTsKICAgICAgbWFyZ2luLXRvcDogNnB4OwogICAgICBmb250LWZhbWlseTogIkpldEJyYWlucyBNb25vIiwgbW9ub3NwYWNlOwogICAgfQogICAgLmNvbnRyb2xzIHsKICAgICAgZGlzcGxheTogZmxleDsKICAgICAgYWxpZ24taXRlbXM6IGNlbnRlcjsKICAgICAganVzdGlmeS1jb250ZW50OiBzcGFjZS1iZXR3ZWVuOwogICAgICBtYXJnaW4tYm90dG9tOiAxOHB4OwogICAgICBwYWRkaW5nOiAwIDEwcHg7CiAgICB9CiAgICAuYnRuLWNvbnRyb2wgewogICAgICBiYWNrZ3JvdW5kOiB0cmFuc3BhcmVudDsKICAgICAgYm9yZGVyOiBub25lOwogICAgICBjb2xvcjogdmFyKC0tdGV4dCk7CiAgICAgIGN1cnNvcjogcG9pbnRlcjsKICAgICAgd2lkdGg6IDQwcHg7CiAgICAgIGhlaWdodDogNDBweDsKICAgICAgYm9yZGVyLXJhZGl1czogNTAlOwogICAgICBkaXNwbGF5OiBmbGV4OwogICAgICBhbGlnbi1pdGVtczogY2VudGVyOwogICAgICBqdXN0aWZ5LWNvbnRlbnQ6IGNlbnRlcjsKICAgICAgdHJhbnNpdGlvbjogYWxsIDAuMnMgdmFyKC0tc3ByaW5nKTsKICAgIH0KICAgIC5idG4tY29udHJvbDpob3ZlciB7IGJhY2tncm91bmQ6IHJnYmEoMjU1LCAyNTUsIDI1NSwgMC4xKTsgdHJhbnNmb3JtOiBzY2FsZSgxLjEpOyB9CiAgICAuYnRuLXBsYXkgewogICAgICB3aWR0aDogNTZweDsKICAgICAgaGVpZ2h0OiA1NnB4OwogICAgICBiYWNrZ3JvdW5kOiB2YXIoLS10ZXh0KTsKICAgICAgY29sb3I6ICMwOTBkMTY7CiAgICAgIGJvcmRlci1yYWRpdXM6IDUwJTsKICAgICAgZGlzcGxheTogZmxleDsKICAgICAgYWxpZ24taXRlbXM6IGNlbnRlcjsKICAgICAganVzdGlmeS1jb250ZW50OiBjZW50ZXI7CiAgICAgIGJveC1zaGFkb3c6IDAgOHB4IDI0cHggcmdiYSgyNTUsIDI1NSwgMjU1LCAwLjI1KTsKICAgIH0KICAgIC5idG4tcGxheTpob3ZlciB7IHRyYW5zZm9ybTogc2NhbGUoMS4wOCk7IGJhY2tncm91bmQ6ICNmZmZmZmY7IGJveC1zaGFkb3c6IDAgMTBweCAyOHB4IHJnYmEoNTYsIDE4OSwgMjQ4LCAwLjQpOyB9CiAgICAudm9sdW1lLXJvdyB7IGRpc3BsYXk6IGZsZXg7IGFsaWduLWl0ZW1zOiBjZW50ZXI7IGdhcDogMTJweDsgcGFkZGluZzogMCA0cHg7IH0KICAgIC52b2x1bWUtc2xpZGVyIHsgZmxleDogMTsgaGVpZ2h0OiA0cHg7IGJhY2tncm91bmQ6IHJnYmEoMjU1LCAyNTUsIDI1NSwgMC4xMik7IGJvcmRlci1yYWRpdXM6IDk5OXB4OyBjdXJzb3I6IHBvaW50ZXI7IH0KICAgIC52b2x1bWUtZmlsbCB7IGhlaWdodDogMTAwJTsgd2lkdGg6IDc1JTsgYmFja2dyb3VuZDogdmFyKC0tdGV4dC1tdXRlZCk7IGJvcmRlci1yYWRpdXM6IDk5OXB4OyB9CiAgPC9zdHlsZT4KPC9oZWFkPgo8Ym9keT4KICA8ZGl2IGNsYXNzPSJwbGF5ZXItY2FyZCI+CiAgICA8ZGl2IGNsYXNzPSJhbGJ1bS1hcnQtd3JhcCI+CiAgICAgIDxkaXYgY2xhc3M9ImFsYnVtLWFydCBwbGF5aW5nIiBpZD0iYXJ0Ij4KICAgICAgICA8ZGl2IGNsYXNzPSJ2aW55bC1ncm9vdmVzIj48L2Rpdj4KICAgICAgICA8ZGl2IGNsYXNzPSJ2aW55bC1jb3JlIj4KICAgICAgICAgIDxzdmcgd2lkdGg9IjIyIiBoZWlnaHQ9IjIyIiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHN0cm9rZT0iY3VycmVudENvbG9yIiBzdHJva2Utd2lkdGg9IjIuMiI+PGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iMyI+PC9jaXJjbGU+PHBhdGggZD0iTTEyIDJ2NG0wIDEydjRNNC45MyA0LjkzbDIuODMgMi44M204LjQ4IDguNDhsMi44MyAyLjgzTTIgMTJoNG0xMiAwaDRNNC45MyAxOS4wN2wyLjgzLTIuODNtOC40OC04LjQ4bDIuODMtMi44MyI+PC9wYXRoPjwvc3ZnPgogICAgICAgIDwvZGl2PgogICAgICA8L2Rpdj4KICAgIDwvZGl2PgogICAgPGRpdiBjbGFzcz0idHJhY2staW5mbyI+CiAgICAgIDxkaXY+CiAgICAgICAgPGRpdiBjbGFzcz0idHJhY2stdGl0bGUiPkN1cGVydGlubyBOaWdodHM8L2Rpdj4KICAgICAgICA8ZGl2IGNsYXNzPSJ0cmFjay1hcnRpc3QiPkFudGlncmF2aXR5IFN0dWRpbyDigKIgTGlxdWlkIEdsYXNzPC9kaXY+CiAgICAgIDwvZGl2PgogICAgICA8c3BhbiBjbGFzcz0icGlsbC1iYWRnZSI+TG9zc2xlc3M8L3NwYW4+CiAgICA8L2Rpdj4KICAgIDxkaXYgY2xhc3M9InNjcnViYmVyIj4KICAgICAgPGRpdiBjbGFzcz0ic2NydWJiZXItYmFyIiBvbmNsaWNrPSJzZWVrKGV2ZW50KSI+CiAgICAgICAgPGRpdiBjbGFzcz0ic2NydWJiZXItZmlsbCIgaWQ9ImZpbGwiPjwvZGl2PgogICAgICA8L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0idGltZS1sYWJlbHMiPgogICAgICAgIDxzcGFuIGlkPSJjdXIiPjE6Mjg8L3NwYW4+CiAgICAgICAgPHNwYW4+MzozMjwvc3Bhbj4KICAgICAgPC9kaXY+CiAgICA8L2Rpdj4KICAgIDxkaXYgY2xhc3M9ImNvbnRyb2xzIj4KICAgICAgPGJ1dHRvbiBjbGFzcz0iYnRuLWNvbnRyb2wiIG9uY2xpY2s9InByZXYoKSI+PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJjdXJyZW50Q29sb3IiIHN0cm9rZS13aWR0aD0iMi4yIj48cG9seWdvbiBwb2ludHM9IjE5IDIwIDkgMTIgMTkgNCAxOSAyMCI+PC9wb2x5Z29uPjxsaW5lIHgxPSI1IiB5MT0iMTkiIHgyPSI1IiB5Mj0iNSI+PC9saW5lPjwvc3ZnPjwvYnV0dG9uPgogICAgICA8YnV0dG9uIGNsYXNzPSJidG4tY29udHJvbCBidG4tcGxheSIgb25jbGljaz0idG9nZ2xlUGxheSgpIj48c3ZnIGlkPSJwbGF5SWNvbiIgd2lkdGg9IjIyIiBoZWlnaHQ9IjIyIiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9ImN1cnJlbnRDb2xvciI+PHJlY3QgeD0iNiIgeT0iNCIgd2lkdGg9IjQiIGhlaWdodD0iMTYiPjwvcmVjdD48cmVjdCB4PSIxNCIgeT0iNCIgd2lkdGg9IjQiIGhlaWdodD0iMTYiPjwvcmVjdD48L3N2Zz48L2J1dHRvbj4KICAgICAgPGJ1dHRvbiBjbGFzcz0iYnRuLWNvbnRyb2wiIG9uY2xpY2s9Im5leHQoKSI+PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJjdXJyZW50Q29sb3IiIHN0cm9rZS13aWR0aD0iMi4yIj48cG9seWdvbiBwb2ludHM9IjUgNCAxNSAxMiA1IDIwIDUgNCI+PC9wb2x5Z29uPjxsaW5lIHgxPSIxOSIgeTE9IjUiIHgyPSIxOSIgeTI9IjE5Ij48L2xpbmU+PC9zdmc+PC9idXR0b24+CiAgICA8L2Rpdj4KICAgIDxkaXYgY2xhc3M9InZvbHVtZS1yb3ciPgogICAgICA8c3ZnIHdpZHRoPSIxNSIgaGVpZ2h0PSIxNSIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9InZhcigtLXRleHQtbXV0ZWQpIiBzdHJva2Utd2lkdGg9IjIiPjxwb2x5Z29uIHBvaW50cz0iMTEgNSA2IDkgMiA5IDIgMTUgNiAxNSAxMSAxOSAxMSA1Ij48L3BvbHlnb24+PC9zdmc+CiAgICAgIDxkaXYgY2xhc3M9InZvbHVtZS1zbGlkZXIiIG9uY2xpY2s9InNldFZvbChldmVudCkiPgogICAgICAgIDxkaXYgY2xhc3M9InZvbHVtZS1maWxsIiBpZD0idm9sRmlsbCI+PC9kaXY+CiAgICAgIDwvZGl2PgogICAgICA8c3ZnIHdpZHRoPSIxNyIgaGVpZ2h0PSIxNyIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9InZhcigtLXRleHQtbXV0ZWQpIiBzdHJva2Utd2lkdGg9IjIiPjxwb2x5Z29uIHBvaW50cz0iMTEgNSA2IDkgMiA5IDIgMTUgNiAxNSAxMSAxOSAxMSA1Ij48L3BvbHlnb24+PHBhdGggZD0iTTE5LjA3IDQuOTNhMTAgMTAgMCAwIDEgMCAxNC4xNE0xNS41NCA4LjQ2YTUgNSAwIDAgMSAwIDcuMDciPjwvcGF0aD48L3N2Zz4KICAgIDwvZGl2PgogIDwvZGl2PgogIDxzY3JpcHQ+CiAgICBsZXQgaXNQbGF5aW5nID0gdHJ1ZTsKICAgIGZ1bmN0aW9uIHRvZ2dsZVBsYXkoKSB7CiAgICAgIGlzUGxheWluZyA9ICFpc1BsYXlpbmc7CiAgICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdhcnQnKS5jbGFzc0xpc3QudG9nZ2xlKCdwbGF5aW5nJywgaXNQbGF5aW5nKTsKICAgICAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3BsYXlJY29uJykuaW5uZXJIVE1MID0gaXNQbGF5aW5nID8gJzxyZWN0IHg9IjYiIHk9IjQiIHdpZHRoPSI0IiBoZWlnaHQ9IjE2Ij48L3JlY3Q+PHJlY3QgeD0iMTQiIHk9IjQiIHdpZHRoPSI0IiBoZWlnaHQ9IjE2Ij48L3JlY3Q+JyA6ICc8cG9seWdvbiBwb2ludHM9IjUgMyAxOSAxMiA1IDIxIDUgMyI+PC9wb2x5Z29uPic7CiAgICB9CiAgICBmdW5jdGlvbiBzZWVrKGUpIHsKICAgICAgY29uc3QgcmVjdCA9IGUuY3VycmVudFRhcmdldC5nZXRCb3VuZGluZ0NsaWVudFJlY3QoKTsKICAgICAgY29uc3QgcGN0ID0gKGUuY2xpZW50WCAtIHJlY3QubGVmdCkgLyByZWN0LndpZHRoICogMTAwOwogICAgICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnZmlsbCcpLnN0eWxlLndpZHRoID0gcGN0ICsgJyUnOwogICAgfQogICAgZnVuY3Rpb24gc2V0Vm9sKGUpIHsKICAgICAgY29uc3QgcmVjdCA9IGUuY3VycmVudFRhcmdldC5nZXRCb3VuZGluZ0NsaWVudFJlY3QoKTsKICAgICAgY29uc3QgcGN0ID0gKGUuY2xpZW50WCAtIHJlY3QubGVmdCkgLyByZWN0LndpZHRoICogMTAwOwogICAgICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgndm9sRmlsbCcpLnN0eWxlLndpZHRoID0gcGN0ICsgJyUnOwogICAgfQogICAgZnVuY3Rpb24gbmV4dCgpIHsgYWxlcnQoJ05leHQgdHJhY2s6IE9wZW5Eb3RzIEFtYmllbnQgQ2FudmFzJyk7IH0KICAgIGZ1bmN0aW9uIHByZXYoKSB7IGFsZXJ0KCdQcmV2aW91cyB0cmFjazogQ3VwZXJ0aW5vIFNwcmluZycpOyB9CiAgPC9zY3JpcHQ+CjwvYm9keT4KPC9odG1sPg==";
    const SHOWCASE_HTML = atob(SHOWCASE_B64);

    function selectAgent(agentName) {
      currentAgent = agentName;
      ['claude', 'codex', 'aider', 'opendots', 'orchestrator'].forEach(a => {
        const el = document.getElementById('agent-card-' + a);
        if (el) el.classList.toggle('active', a === agentName);
      });

      const label = document.getElementById('studio-prompt-label');
      const input = document.getElementById('studio-prompt-input');

      if (agentName === 'opendots') {
        if (label) label.innerText = 'Design with OpenDots Generative UI Canvas & Visual Dots';
        if (input && !input.value) input.placeholder = 'Ask OpenDots to generate an interactive canvas component with visual state dots and channels...';
        switchStudioTab('dots');
      } else if (agentName === 'claude') {
        if (label) label.innerText = 'Design & Architect with Claude Code (Bedrock Opus 4.6)';
        if (input && !input.value) input.placeholder = 'Describe a component, layout, or visual design to build and preview live...';
      } else if (agentName === 'codex') {
        if (label) label.innerText = 'Build & Prototype with OpenAI Codex (gpt-5.6-terra)';
        if (input && !input.value) input.placeholder = 'Instruct Codex to build and test code in the sandbox...';
      } else if (agentName === 'aider') {
        if (label) label.innerText = 'Pair-Program & Refactor with Aider (5-Tier Gateway)';
        if (input && !input.value) input.placeholder = 'Ask Aider to modify code or design with model auto-routing...';
      } else {
        if (label) label.innerText = 'Orchestrate Multi-Agent Swarm & AST Sensor';
      }
    }

    function setStudioMode(mode) {
      currentStudioMode = mode;
      ['design', 'dots', 'code', 'cli'].forEach(m => {
        const el = document.getElementById('mode-' + m + '-btn');
        if (el) el.classList.toggle('active', m === mode);
      });
      if (mode === 'dots') switchStudioTab('dots');
      else if (mode === 'code') switchStudioTab('code');
      else if (mode === 'cli') switchStudioTab('logs');
      else switchStudioTab('preview');
    }

    function setPresetPrompt(text, mode) {
      const input = document.getElementById('studio-prompt-input');
      if (input) {
        input.value = text;
        input.focus();
      }
      if (mode) setStudioMode(mode);
    }

    function switchStudioTab(tab) {
      const tabs = ['preview', 'dots', 'code', 'logs', 'app'];
      tabs.forEach(t => {
        const btn = document.getElementById('tab-canvas-' + t + '-btn');
        const view = document.getElementById('view-canvas-' + t);
        if (btn) btn.classList.toggle('active', t === tab);
        if (view) view.style.display = (t === tab) ? ((t === 'preview' || t === 'app') ? 'flex' : 'block') : 'none';
      });
    }

    function setCanvasViewport(size) {
      const iframe = document.getElementById('studio-live-iframe');
      const deskBtn = document.getElementById('vp-desktop-btn');
      const mobBtn = document.getElementById('vp-mobile-btn');
      if (!iframe) return;
      if (size === 'mobile') {
        iframe.classList.add('mobile-view');
        if (mobBtn) mobBtn.style.color = 'var(--accent)';
        if (deskBtn) deskBtn.style.color = 'var(--text-muted)';
      } else {
        iframe.classList.remove('mobile-view');
        if (deskBtn) deskBtn.style.color = 'var(--accent)';
        if (mobBtn) mobBtn.style.color = 'var(--text-muted)';
      }
    }

    function renderInCanvas(htmlContent) {
      activeComponentHtml = htmlContent;
      const iframe = document.getElementById('studio-live-iframe');
      const codeViewer = document.getElementById('studio-code-viewer');
      if (iframe) iframe.srcdoc = htmlContent;
      if (codeViewer) codeViewer.innerText = htmlContent;
    }

    function resetShowcaseDesign() {
      renderInCanvas(SHOWCASE_HTML);
      switchStudioTab('preview');
      const st = document.getElementById('studio-exec-status');
      if (st) st.innerText = 'Showcase component loaded';
    }

    function copyCanvasCode() {
      if (activeComponentHtml) {
        navigator.clipboard.writeText(activeComponentHtml);
        const st = document.getElementById('studio-exec-status');
        if (st) {
          const old = st.innerText;
          st.innerText = '✓ Code copied to clipboard!';
          setTimeout(() => st.innerText = old, 2000);
        }
      }
    }

    function downloadCanvasHtml() {
      if (!activeComponentHtml) return;
      const blob = new Blob([activeComponentHtml], {type: 'text/html'});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `component-${currentAgent}-${Date.now()}.html`;
      a.click();
    }

    function openCanvasNewTab() {
      if (!activeComponentHtml) return;
      const blob = new Blob([activeComponentHtml], {type: 'text/html'});
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    }

    function selectDot(dotType) {
      const dotMeta = {
        research: {
          title: 'Research Dot (agent-reach)',
          desc: 'Specialized in gathering real-time web, GitHub, and academic knowledge without paid API keys.',
          prompt: 'Use OpenDots research dot to find modern WWDC glassmorphism patterns and synthesize a design'
        },
        architect: {
          title: 'UI Architect Dot (Apple HIG Core)',
          desc: 'Generates Apple HIG compliant glassmorphism layouts, Cupertino typography, and responsive Bento grids.',
          prompt: 'Design an Apple HIG liquid-glass dashboard widget with Cupertino spring physics and hairline borders'
        },
        canvas: {
          title: 'Generative Canvas Dot (CopilotKit :5173)',
          desc: 'Interactive visual state engine connected to local CopilotKit threads, channels, and spaces.',
          prompt: 'Create an OpenDots interactive generative UI canvas component with live reactive visual dots'
        },
        security: {
          title: 'Security Shield Dot (strix & ggshield)',
          desc: 'Monitors secrets, scans inputs for injection vulnerabilities, and enforces safety gates.',
          prompt: 'Audit the component for XSS injection, safe styling, and zero credential leakage'
        },
        motion: {
          title: 'Spring Motion Dot (WWDC Spring)',
          desc: 'Applies fluid WWDC spring physics (cubic-bezier(0.23, 1, 0.32, 1)) and tactile micro-interactions.',
          prompt: 'Add fluid spring hover transitions and tactile feedback to the design'
        }
      };

      if (dotMeta[dotType]) {
        document.getElementById('dot-inspector-title').innerText = dotMeta[dotType].title;
        document.getElementById('dot-inspector-desc').innerText = dotMeta[dotType].desc;
        setPresetPrompt(dotMeta[dotType].prompt, 'dots');
      }
    }

    async function startOpenDotsServer() {
      const st = document.getElementById('studio-exec-status');
      if (st) st.innerText = 'Starting OpenDots Vite server on port 5173...';
      try {
        const r = await fetch('/v1/opendots/start', {method: 'POST'});
        const d = await r.json();
        alert(d.message || 'OpenDots server started on http://localhost:5173');
        if (st) st.innerText = 'OpenDots online on port 5173';
        switchStudioTab('app');
      } catch (e) {
        alert('Notice: ' + e.message);
      }
    }

    async function generateDesign() {
      const input = document.getElementById('studio-prompt-input');
      const msg = input.value.trim();
      if (!msg) {
        alert('Please enter a prompt or instruction.');
        return;
      }

      const model = document.getElementById('studio-model-select').value;
      const statusEl = document.getElementById('studio-exec-status');
      const genBtn = document.getElementById('btn-studio-generate');
      const diagEl = document.getElementById('studio-diagnostics-text');

      genBtn.disabled = true;
      genBtn.innerHTML = '<span class="dot" style="display:inline-block;animation:pulse 1s infinite;"></span> Generating...';
      statusEl.innerText = `Generating design with ${currentAgent.toUpperCase()}...`;
      diagEl.innerText = `[${new Date().toLocaleTimeString()}] Dispatching design prompt to ${currentAgent} (Model: ${model}, Mode: ${currentStudioMode})...\n> Prompt: ${msg}\n`;

      const startT = performance.now();
      try {
        const r = await fetch('/v1/agents/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            agent: currentAgent,
            message: msg,
            model: model,
            mode: currentStudioMode
          })
        });
        const data = await r.json();
        const durationSec = ((performance.now() - startT) / 1000).toFixed(2);

        if (r.ok && data.status === 'ok') {
          statusEl.innerText = `✓ Generated in ${durationSec}s`;
          diagEl.innerText = `[${new Date().toLocaleTimeString()} • ${durationSec}s • Agent: ${data.agent}]\n\n${data.response}`;

          if (data.code) {
            renderInCanvas(data.code);
            if (currentStudioMode !== 'dots') {
              switchStudioTab('preview');
            }
          } else {
            const wrapped = '<!DOCTYPE html><html><head><meta charset="UTF-8"><style>body{background:#090d16;color:#f8fafc;font-family:system-ui,-apple-system,sans-serif;padding:32px;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;}.card{background:rgba(17,24,39,0.85);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.12);border-radius:18px;padding:28px;max-width:620px;line-height:1.65;box-shadow:0 20px 50px rgba(0,0,0,0.6);}</style></head><body><div class="card">' + data.response.replace(/\n/g, '<br>') + '</div>' + '<' + '/body>' + '<' + '/html>';
            renderInCanvas(wrapped);
            switchStudioTab('preview');
          }
        } else {
          statusEl.innerText = 'Generation error';
          diagEl.innerText = `[ERROR • ${durationSec}s]\n${data.response || data.detail || JSON.stringify(data, null, 2)}`;
        }
      } catch (err) {
        statusEl.innerText = 'Request failed';
        diagEl.innerText = `[Network Error]: ${err.message}`;
      } finally {
        genBtn.disabled = false;
        genBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg> Generate &amp; Render Design';
      }
    }

    // Keyboard shortcut: Ctrl+Enter or Cmd+Enter to generate design
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        const input = document.getElementById('studio-prompt-input');
        if (input && document.activeElement === input) {
          e.preventDefault();
          generateDesign();
        }
      }
    });

    // Auto-load showcase design on page load
    window.addEventListener('load', () => {
      resetShowcaseDesign();
      fetchAgentStatus();
    });

    async function runTestPrompt() {
      const model = document.getElementById('test-model').value;
      const prompt = document.getElementById('test-prompt').value;
      const outBox = document.getElementById('test-output');
      const btn = document.getElementById('run-btn');
      const btnLbl = document.getElementById('run-btn-label');
      const badge = document.getElementById('routed-badge');

      btn.disabled = true;
      btnLbl.innerText = 'Dispatching to Gateway...';
      outBox.innerText = `[DISPATCHING] Requested Tier: ${model}...\n`;

      const start = performance.now();
      try {
        const resp = await fetch('/v1/chat/completions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: model,
            messages: [{ role: 'user', content: prompt }]
          })
        });
        const data = await resp.json();
        const duration = Math.round(performance.now() - start);
        if (data.choices && data.choices[0]) {
          badge.innerText = `routed -> ${data.model} (${duration}ms)`;
          outBox.innerText = `[SUCCESS • ${duration}ms • Engine: ${data.model}]\n\n${data.choices[0].message.content}\n\n[Tokens: ${data.usage?.prompt_tokens || 0} in / ${data.usage?.completion_tokens || 0} out]`;
        } else {
          outBox.innerText = `[ERROR]\n` + JSON.stringify(data, null, 2);
        }
        fetchStats();
      } catch (err) {
        outBox.innerText = `[GATEWAY ERROR]: ${err.message}`;
      } finally {
        btn.disabled = false;
        btnLbl.innerText = 'Execute on Gateway';
      }
    }

    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (document.activeElement && document.activeElement.id === 'test-prompt') {
          runTestPrompt();
        } else if (document.activeElement && document.activeElement.id === 'skill-query') {
          testSkillRoute();
        }
      }
    });

    fetchStats();
    testSkillRoute();
    pollTimer = setInterval(() => { if (pollingActive) fetchStats(); }, 5000);
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "providers": {
            "bedrock": bedrock is not None,
            "openrouter": bool(os.environ.get("OPENROUTER_API_KEY")),
            "nvidia": bool(os.environ.get("NVIDIA_API_KEY")),
            "deepseek": bool(os.environ.get("DEEPSEEK_API_KEY")),
            "groq": bool(os.environ.get("GROQ_API_KEY")),
            "openai": bool(os.environ.get("OPENAI_API_KEY")),
            "ollama": True
        },
        "active_models": len(MODEL_MAP)
    }


@app.get("/v1/config/status")
def get_config_status():
    """Returns masked status of configured local credentials (never returns raw secret keys)."""
    load_local_env(override=False)
    return {
        "aws_profile": os.environ.get("AWS_PROFILE", ""),
        "aws_region": os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        "bedrock_active": bedrock is not None,
        "nvidia": _mask_secret(os.environ.get("NVIDIA_API_KEY")),
        "openrouter": _mask_secret(os.environ.get("OPENROUTER_API_KEY")),
        "deepseek": _mask_secret(os.environ.get("DEEPSEEK_API_KEY")),
        "groq": _mask_secret(os.environ.get("GROQ_API_KEY")),
        "openai": _mask_secret(os.environ.get("OPENAI_API_KEY")),
    }


@app.post("/v1/config/keys")
def update_config_keys(req: ApiKeysUpdateRequest):
    """Updates personal API keys in local git-ignored .env and hot-reloads providers in memory."""
    env_path = Path(__file__).resolve().parent / ".env"
    existing: Dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                existing[k.strip()] = v.strip().strip("\"'")

    def _clean(val: Optional[str], key_name: str) -> str:
        if val is not None and val.strip():
            return val.strip().replace("\\_", "_").strip("\"'")
        return existing.get(key_name, os.environ.get(key_name, ""))

    aws_prof = _clean(req.aws_profile, "AWS_PROFILE")
    aws_reg = _clean(req.aws_region, "AWS_DEFAULT_REGION") or "us-east-1"
    or_key = _clean(req.openrouter_api_key, "OPENROUTER_API_KEY")
    nv_key = _clean(req.nvidia_api_key, "NVIDIA_API_KEY")
    ds_key = _clean(req.deepseek_api_key, "DEEPSEEK_API_KEY")
    gq_key = _clean(req.groq_api_key, "GROQ_API_KEY")
    oa_key = _clean(req.openai_api_key, "OPENAI_API_KEY")

    lines = [
        "# Antigravity Autonomous Workstation — Local Environment Configuration",
        "# WARNING: This file is git-ignored. Never commit secrets to version control.",
        "",
        f"AWS_PROFILE={aws_prof}",
        f"AWS_DEFAULT_REGION={aws_reg}",
        "",
        f"OPENROUTER_API_KEY={or_key}",
        f"NVIDIA_API_KEY={nv_key}",
        f"DEEPSEEK_API_KEY={ds_key}",
        f"GROQ_API_KEY={gq_key}",
        f"OPENAI_API_KEY={oa_key}",
        "",
        f"OLLAMA_HOST={existing.get('OLLAMA_HOST', 'http://127.0.0.1:11434')}",
    ]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(env_path, 0o600)
    except Exception:
        pass

    reload_runtime_credentials()
    # Automatically configure all agent harnesses on key save
    auto_cfg_res = {}
    try:
        if auto_configurator:
            auto_cfg_res = auto_configurator.run_full_auto_configuration(force=True)
    except Exception as e:
        auto_cfg_res = {"error": str(e)}

    return {
        "status": "ok",
        "message": "Saved to local .env (0600 permissions), hot-reloaded active providers, and auto-configured all agent harnesses.",
        "providers": health()["providers"],
        "agents": auto_cfg_res,
    }


@app.post("/v1/config/aws-auto")
def auto_configure_aws_endpoint():
    """Auto-detects local ~/.aws login, creates a dedicated workstation IAM profile if needed, and hot-reloads Bedrock."""
    import sys
    try:
        tools_dir = Path(__file__).resolve().parent / "tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        import setup_wizard
        prof, reg = setup_wizard.auto_detect_and_configure_aws(tty_stream=None, non_interactive=True)
        if not prof:
            return {"status": "warning", "message": "No local ~/.aws/credentials found. Run `aws configure` first or enter an API key below."}
        update_config_keys(ApiKeysUpdateRequest(aws_profile=prof, aws_region=reg))
        if auto_configurator:
            auto_configurator.run_full_auto_configuration(force=True)
        return {
            "status": "ok",
            "message": f"Activated AWS Bedrock profile [{prof}] ({reg}) and hot-reloaded gateway.",
            "aws_profile": prof,
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

@app.get("/v1/usage")
def get_usage():
    if STATS_FILE.exists():
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"totals": {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "estimated_usd": 0.0}, "by_model": {}}

@app.get("/v1/postmortems")
def get_postmortems():
    pm_file = STATS_DIR / "postmortems.json"
    if pm_file.exists():
        try:
            with open(pm_file, "r", encoding="utf-8") as f:
                return {"postmortems": json.load(f)}
        except Exception:
            pass
    return {"postmortems": []}

@app.get("/v1/graph")
def get_graph_summary():
    graph_path = Path(__file__).resolve().parent / "graphify-out" / "graph.json"
    if not graph_path.exists():
        graph_path = Path.cwd() / "graphify-out" / "graph.json"
    if graph_path.exists():
        try:
            with open(graph_path, "r", encoding="utf-8") as f:
                g = json.load(f)
            nodes = len(g.get("nodes", []))
            edges = len(g.get("links", g.get("edges", [])))
            communities = len({n.get("community") for n in g.get("nodes", []) if n.get("community") is not None})
            return {"status": "synced", "nodes": nodes, "edges": edges, "communities": communities}
        except Exception as e:
            return {"status": "error", "detail": str(e)}
    return {"status": "missing", "nodes": 0, "edges": 0, "communities": 0}


@app.get("/graphify", response_class=HTMLResponse)
def open_graphify_file():
    """
    Opens the interactive Graphify AST Graph HTML file (graphify-out/graph.html)
    when the user taps on the Graphify card on /dashboard.
    If graph.html is missing on a fresh install, auto-builds or renders an interactive AST explorer.
    """
    import sys
    base_dir = Path(__file__).resolve().parent
    html_file = base_dir / "graphify-out" / "graph.html"
    if not html_file.exists():
        html_file = Path.cwd() / "graphify-out" / "graph.html"
    if not html_file.exists():
        try:
            subprocess.run(
                [sys.executable, "-m", "graphify", "update", "."],
                cwd=str(base_dir),
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
        except Exception:
            pass
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8", errors="replace"))
    return open_graphify_report()


@app.get("/graphify/report", response_class=HTMLResponse)
def open_graphify_report():
    """
    Renders graphify-out/GRAPH_REPORT.md in a sleek dark-mode viewer with a link to /graphify.
    """
    import html as html_lib
    base_dir = Path(__file__).resolve().parent
    report_file = base_dir / "graphify-out" / "GRAPH_REPORT.md"
    if not report_file.exists():
        report_file = Path.cwd() / "graphify-out" / "GRAPH_REPORT.md"
    raw_md = report_file.read_text(encoding="utf-8", errors="replace") if report_file.exists() else "# Graphify AST Report\nRun `python -m graphify update .` to build the knowledge graph."
    escaped = html_lib.escape(raw_md)
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Graphify AST Architecture Report</title>
<style>
  body {{ background: #070a10; color: #f1f5f9; font-family: 'Plus Jakarta Sans', system-ui, sans-serif; margin: 0; padding: 28px; }}
  .bar {{ max-width: 1100px; margin: 0 auto 18px; display: flex; justify-content: space-between; align-items: center; background: #0e131f; border: 1px solid rgba(148,163,184,0.18); padding: 14px 20px; border-radius: 12px; }}
  a.btn {{ background: #a855f7; color: #fff; text-decoration: none; padding: 8px 14px; border-radius: 8px; font-weight: 600; font-size: 0.85rem; }}
  pre {{ max-width: 1100px; margin: 0 auto; background: #0e131f; border: 1px solid rgba(148,163,184,0.18); padding: 24px; border-radius: 12px; white-space: pre-wrap; font-family: 'JetBrains Mono', monospace; font-size: 0.84rem; line-height: 1.6; color: #cbd5e1; }}
</style></head>
<body>
  <div class="bar">
    <div><strong>Graphify AST Architecture Report</strong> <span style="color:#94a3b8;font-size:0.82rem;">(graphify-out/GRAPH_REPORT.md)</span></div>
    <div style="display:flex;gap:10px;">
      <a class="btn" href="/graphify">Open Interactive 2D/3D Graph.html &rarr;</a>
      <a class="btn" style="background:#1e293b;" href="/dashboard">&larr; Back to Dashboard</a>
    </div>
  </div>
  <pre>{escaped}</pre>
</body></html>"""
    return HTMLResponse(content=page)


@app.get("/v1/graphify/query")
def query_graphify_ast(q: str = ""):
    import sys
    base_dir = Path(__file__).resolve().parent
    if not q.strip():
        return {"status": "ok", "output": "Enter a symbol, function, or concept to query graphify-out/graph.json."}
    try:
        res = subprocess.run(
            [sys.executable, "-m", "graphify", "query", q.strip(), "--budget", "800"],
            cwd=str(base_dir),
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )
        out = (res.stdout or res.stderr or "").strip()
        return {"status": "ok", "query": q, "output": out or "No matching AST nodes found."}
    except Exception as e:
        return {"status": "error", "output": str(e)}


@app.get("/v1/hardware")
def get_hardware_endpoint():
    import sys
    try:
        hw_cache = STATS_DIR / "hardware_profile.json"
        if hw_cache.exists():
            return json.loads(hw_cache.read_text(encoding="utf-8"))
        tools_dir = Path(__file__).resolve().parent / "tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        import setup_wizard
        return setup_wizard.detect_hardware_profile()
    except Exception as e:
        return {"os": "Unknown", "detail": str(e)}


@app.get("/v1/last-route")
def get_last_route_endpoint():
    route_file = STATS_DIR / "last_route.json"
    if route_file.exists():
        try:
            return json.loads(route_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"tier": "auto", "matched_repos": [], "prompt_preview": "Waiting for next prompt..."}

@app.get("/v1/skills/route")
def route_skills_endpoint(q: str = ""):
    import sys
    try:
        tools_dir = Path(__file__).resolve().parent / "tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        import skill_router
        if not q.strip():
            idx = skill_router.build_or_load_skill_index()
            return {"status": "ready", "indexed_skills": len(idx), "repositories": 32}
        return skill_router.auto_route_domain_tools(q)
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/v1/models")
def list_models():
    models_data = []
    for alias, info in MODEL_MAP.items():
        models_data.append({
            "id": alias,
            "object": "model",
            "created": int(time.time()),
            "owned_by": info["provider"],
            "tier": info.get("tier", "general"),
            "real_model_id": info["id"]
        })
    return {"object": "list", "data": models_data}

def stream_bedrock_events(kwargs, model_alias: str, real_model_id: str):
    stream_id = f"chatcmpl-bedrock-{int(time.time())}"
    resp = bedrock.converse_stream(**kwargs)
    for event in resp.get("stream"):
        if "contentBlockDelta" in event:
            delta = event["contentBlockDelta"]["delta"].get("text", "")
            chunk = {
                "id": stream_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model_alias,
                "choices": [{
                    "index": 0,
                    "delta": {"content": delta},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
        elif "messageStop" in event:
            chunk = {
                "id": stream_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model_alias,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": event["messageStop"].get("stopReason", "stop")
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
        elif "metadata" in event:
            usage = event["metadata"].get("usage", {})
            record_usage(real_model_id, usage.get("inputTokens", 0), usage.get("outputTokens", 0))

    yield "data: [DONE]\n\n"

def stream_ollama_events(ollama_body, model_alias: str):
    stream_id = f"chatcmpl-local-{int(time.time())}"
    req_data = json.dumps(ollama_body).encode("utf-8")
    url_req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(url_req, timeout=120) as resp:
        for line in resp:
            if not line:
                continue
            item = json.loads(line.decode("utf-8"))
            delta = item.get("message", {}).get("content", "")
            done = item.get("done", False)
            chunk = {
                "id": stream_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model_alias,
                "choices": [{
                    "index": 0,
                    "delta": {"content": delta} if delta else {},
                    "finish_reason": "stop" if done else None
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            if done:
                record_usage("llama3.2:1b", item.get("prompt_eval_count", 0), item.get("eval_count", 0))
                break
    yield "data: [DONE]\n\n"

def stream_openai_compatible_events(endpoint_url: str, api_key: str, payload: dict, model_alias: str, extra_headers: dict = None):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    if extra_headers:
        headers.update(extra_headers)
    
    payload["stream"] = True
    req = urllib.request.Request(endpoint_url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        for line in resp:
            if not line:
                continue
            line_str = line.decode("utf-8", errors="replace")
            yield line_str
    yield "data: [DONE]\n\n"

def call_openai_compatible(endpoint_url: str, api_key: str, payload: dict, extra_headers: dict = None):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    if extra_headers:
        headers.update(extra_headers)
    
    req = urllib.request.Request(endpoint_url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        for choice in data.get("choices", []):
            msg = choice.get("message", {})
            if not msg.get("content") and msg.get("reasoning_content"):
                msg["content"] = msg["reasoning_content"]
        return data

async def invoke_model_with_fallback(req: ChatCompletionRequest, requested_alias: str):
    """
    Executes model invocation.
    Priority order:
    1. AWS Bedrock (if credentials configured and functional)
    2. BYOK Providers (OpenRouter, NVIDIA, DeepSeek, Groq, OpenAI if key present)
    3. Local Ollama GPU Engine (always available for $0.00)
    """
    candidates = [requested_alias] + FALLBACK_CHAINS.get(requested_alias, ["coder", "fast", "local"])
    
    last_exception = None
    for alias in candidates:
        clean_name = alias.replace("openai/", "").replace("bedrock/", "").replace("ollama/", "")
        target = MODEL_MAP.get(clean_name, {"provider": "bedrock", "id": clean_name})
        
        # Prepare system & user messages
        system_prompts = []
        if req.enhance_quality:
            system_prompts.append({"text": QUALITY_DIRECTIVE})
            
        converse_messages = []
        for m in req.messages:
            if m.role == "system":
                system_prompts.append({"text": str(m.content)})
            elif m.role in ["user", "assistant"]:
                converse_messages.append({
                    "role": m.role,
                    "content": [{"text": str(m.content)}]
                })
        if not converse_messages:
            converse_messages = [{"role": "user", "content": [{"text": "Hello"}]}]

        # 1. AWS Bedrock execution (if configured)
        if target["provider"] == "bedrock" and bedrock is not None:
            kwargs = {
                "modelId": target["id"],
                "messages": converse_messages,
                "inferenceConfig": {
                    "maxTokens": req.max_tokens or 4096,
                    "temperature": req.temperature or 0.7
                }
            }
            if system_prompts:
                kwargs["system"] = system_prompts

            if req.stream:
                try:
                    return StreamingResponse(
                        stream_bedrock_events(kwargs, alias, target["id"]),
                        media_type="text/event-stream"
                    )
                except Exception as e:
                    print(f"[Bedrock Stream Warning] {alias} error: {e}. Trying BYOK or fallback...")
                    last_exception = e
            else:
                try:
                    resp = bedrock.converse(**kwargs)
                    out_msg = resp["output"]["message"]
                    text_parts = []
                    reasoning_parts = []
                    for blk in out_msg.get("content", []):
                        if "text" in blk and blk["text"]:
                            text_parts.append(blk["text"])
                        if "reasoningContent" in blk:
                            rt = blk["reasoningContent"].get("reasoningText", {}).get("text", "")
                            if rt:
                                reasoning_parts.append(rt)
                    content = "\n".join(text_parts).strip()
                    reasoning = "\n".join(reasoning_parts).strip() or None
                    if not content and reasoning:
                        content = reasoning
                    
                    usage = resp.get("usage", {})
                    p_tokens = usage.get("inputTokens", 0)
                    c_tokens = usage.get("outputTokens", 0)
                    record_usage(target["id"], p_tokens, c_tokens)

                    return {
                        "id": f"chatcmpl-bedrock-{int(time.time())}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": alias,
                        "choices": [{
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": content,
                                "reasoning": reasoning
                            },
                            "finish_reason": resp.get("stopReason", "stop")
                        }],
                        "usage": {
                            "prompt_tokens": p_tokens,
                            "completion_tokens": c_tokens,
                            "total_tokens": usage.get("totalTokens", 0)
                        },
                        "latency_ms": resp.get("metrics", {}).get("latencyMs", 0)
                    }
                except Exception as e:
                    print(f"[Bedrock Warning] Model {alias} error: {e}. Trying BYOK / fallback...")
                    last_exception = e

        # 2. Check BYOK Providers (OpenRouter, NVIDIA, DeepSeek, Groq, OpenAI)
        for prov_name, prov_cfg in BYOK_PROVIDERS.items():
            if prov_cfg["key"] and clean_name in prov_cfg["models"]:
                mapped_model = prov_cfg["models"][clean_name]
                try:
                    std_messages = []
                    for sp in system_prompts:
                        std_messages.append({"role": "system", "content": sp["text"]})
                    for m in req.messages:
                        if m.role != "system":
                            std_messages.append({"role": m.role, "content": str(m.content)})
                    
                    body = {
                        "model": mapped_model,
                        "messages": std_messages,
                        "temperature": req.temperature,
                        "max_tokens": req.max_tokens
                    }

                    if req.stream:
                        return StreamingResponse(
                            stream_openai_compatible_events(prov_cfg["url"], prov_cfg["key"], body, alias, prov_cfg["headers"]),
                            media_type="text/event-stream"
                        )
                    
                    res = call_openai_compatible(prov_cfg["url"], prov_cfg["key"], body, prov_cfg["headers"])
                    usage = res.get("usage", {})
                    record_usage(prov_name, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
                    res["model"] = alias
                    return res
                except Exception as e:
                    print(f"[{prov_name} Warning] Model {mapped_model} error: {e}. Cascading...")
                    last_exception = e
                    continue

        # 3. Local Ollama Execution ($0.00 / Free)
        if target["provider"] == "ollama" or alias == "local":
            try:
                ollama_messages = []
                for sp in system_prompts:
                    ollama_messages.append({"role": "system", "content": sp["text"]})
                for cm in converse_messages:
                    ollama_messages.append({"role": cm["role"], "content": cm["content"][0]["text"]})
                
                ollama_body = {
                    "model": target.get("id", "llama3.2:1b") if target.get("provider") == "ollama" else "llama3.2:1b",
                    "messages": ollama_messages,
                    "stream": req.stream,
                    "options": {
                        "temperature": req.temperature,
                        "num_predict": req.max_tokens
                    }
                }
                if req.stream:
                    return StreamingResponse(
                        stream_ollama_events(ollama_body, alias),
                        media_type="text/event-stream"
                    )
                
                req_data = json.dumps(ollama_body).encode("utf-8")
                url_req = urllib.request.Request(
                    f"{OLLAMA_URL}/api/chat",
                    data=req_data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(url_req, timeout=60) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                
                content = res_json.get("message", {}).get("content", "")
                p_tokens = res_json.get("prompt_eval_count", 0)
                c_tokens = res_json.get("eval_count", 0)
                record_usage("llama3.2:1b", p_tokens, c_tokens)

                return {
                    "id": f"chatcmpl-local-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": alias,
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": p_tokens,
                        "completion_tokens": c_tokens,
                        "total_tokens": p_tokens + c_tokens
                    }
                }
            except Exception as e:
                print(f"[Ollama Warning] Local inference failed: {e}")
                last_exception = e
                continue

    raise HTTPException(status_code=500, detail=f"All models & BYOK providers failed. Last error: {str(last_exception)}")


def resolve_auto_model_from_messages(messages: List[ChatMessage]) -> str:
    """Smart 5-Tier router for /v1/chat/completions when model='auto'."""
    user_text = " ".join(str(m.content) for m in messages if m.role == "user").lower()
    if any(k in user_text for k in ["format", "lint", "docstring", "comment", "typo", "spelling", "1 sentence"]):
        return "local"
    if any(k in user_text for k in ["test", "unit test", "boilerplate", "config", "readme", "commit", "html", "css", "rename"]):
        return "fast"
    if any(k in user_text for k in ["debug", "why", "algorithm", "race condition", "memory leak", "root cause", "critique", "diff"]):
        return "reasoner"
    if any(k in user_text for k in ["architect", "security audit", "system design", "crypto", "auth overhaul"]):
        return "claude"
    return "coder"


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    clean_model_name = req.model.replace("openai/", "").replace("bedrock/", "").replace("ollama/", "")
    if clean_model_name == "auto":
        clean_model_name = resolve_auto_model_from_messages(req.messages)
    return await invoke_model_with_fallback(req, clean_model_name)


@app.post("/v1/orchestrate")
async def orchestrate_agent(req: OrchestrationRequest):
    """
    Dispatches a task to an external agent harness (Aider, Claude Code, Codex, or OpenCode).
    """
    cwd = req.working_dir or os.getcwd()
    cmd = []
    
    selected_model = req.model
    if selected_model == "auto":
        # Smart Auto Selection
        task_lower = req.task.lower()
        if any(w in task_lower for w in ["format", "lint", "docstring", "comment", "typo", "spelling"]):
            selected_model = "local"
        elif any(w in task_lower for w in ["test", "boilerplate", "config", "readme", "commit", "html", "css"]):
            selected_model = "fast"
        elif any(w in task_lower for w in ["debug", "why", "algorithm", "race condition", "leak", "optimize"]):
            selected_model = "reasoner"
        elif any(w in task_lower for w in ["architect", "security", "audit", "system design"]):
            selected_model = "claude"
        else:
            selected_model = "coder"
            
    agent_type = req.agent.lower()
    if agent_type == "aider":
        cmd = [
            "aider",
            "--openai-api-base", "http://127.0.0.1:8000/v1",
            "--openai-api-key", "dummy-key",
            "--model", f"openai/{selected_model}",
            "--message", req.task,
            "--yes-always"
        ]

    elif agent_type == "claude":
        cmd = ["claude", "-p", req.task, "--dangerously-skip-permissions"]

    elif agent_type == "codex":
        if selected_model in ["local", "llama3.2"]:
            cmd = ["codex", "exec", req.task, "--oss", "--local-provider", "ollama", "-m", "llama3.2:1b", "--dangerously-bypass-approvals-and-sandbox"]
        else:
            cmd = ["codex", "exec", req.task, "--dangerously-bypass-approvals-and-sandbox"]

    elif agent_type == "opencode":
        cmd = ["opencode", "run", "--prompt", req.task, "--auto"]

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported agent harness: {req.agent}")

    print(f"Orchestrating {agent_type} (Model: {selected_model}): {' '.join(cmd)}")
    
    start_t = time.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        duration = round(time.time() - start_t, 2)
        
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "agent": req.agent,
            "resolved_model": selected_model,
            "exit_code": proc.returncode,
            "duration_seconds": duration,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace")
        }
    except asyncio.TimeoutError:
        return {"status": "timeout", "detail": "Agent process exceeded 300s timeout."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestration execution error: {str(e)}")


@app.get("/v1/agents/status")
def get_agents_status_endpoint():
    """Returns the live configuration, version, and readiness status of all workstation agents."""
    if auto_configurator:
        return auto_configurator.get_agents_status()
    return {"error": "auto_configurator not loaded"}


@app.post("/v1/config/auto-configure")
def trigger_auto_configuration():
    """Triggers the full self-healing auto-configuration workflow across Claude Code, Codex, Aider, OpenDots, and Ollama."""
    if auto_configurator:
        return auto_configurator.run_full_auto_configuration(force=True)
    return {"status": "error", "message": "auto_configurator not loaded"}


@app.post("/v1/opendots/configure")
def configure_opendots_endpoint():
    """Auto-configures OpenDots (.env and gateway bridge) for local CopilotKit canvas execution."""
    if auto_configurator:
        return auto_configurator.configure_opendots()
    return {"status": "error", "message": "auto_configurator not loaded"}


@app.get("/v1/opendots/status")
def get_opendots_status_endpoint():
    """Returns live status of OpenDots Vite frontend (port 5173) and backend (port 4310)."""
    opendots_dir = TOOLS_DIR / "OpenDots"
    has_nm = (opendots_dir / "node_modules").exists()
    has_env = (opendots_dir / ".env").exists()
    
    port_5173_online = False
    port_4310_online = False
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:5173/", timeout=0.8) as r:
            port_5173_online = (r.status == 200)
    except Exception:
        pass
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:4310/", timeout=0.8) as r:
            port_4310_online = True
    except Exception:
        pass

    return {
        "installed": opendots_dir.exists(),
        "has_node_modules": has_nm,
        "configured": has_env,
        "vite_online": port_5173_online,
        "server_online": port_4310_online,
        "url": "http://localhost:5173" if port_5173_online else None,
        "port": 5173
    }


@app.post("/v1/opendots/start")
def start_opendots_server_endpoint():
    """Starts OpenDots Vite frontend server on port 5173 in the background."""
    opendots_dir = TOOLS_DIR / "OpenDots"
    if not (opendots_dir / "node_modules").exists():
        return {"status": "error", "message": "node_modules missing. Please run npm install first."}
    
    st = get_opendots_status_endpoint()
    if st["vite_online"]:
        return {"status": "already_running", "message": "OpenDots is already online on http://localhost:5173", "url": "http://localhost:5173"}
    
    try:
        subprocess.Popen(
            ["npx", "vite", "--port", "5173"],
            cwd=str(opendots_dir),
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return {"status": "starting", "message": "Launched OpenDots Vite server on http://localhost:5173", "url": "http://localhost:5173"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to start OpenDots: {e}"}


def _extract_code_block(text: str) -> str:
    m = re.search(r"```(?:html|jsx|tsx|css|xml|svg)?\s*\n([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    if "<!DOCTYPE html>" in text or "<html" in text or ("<div" in text and "</div>" in text):
        return text.strip()
    return ""


DESIGN_SYSTEM_PROMPT = """You are an elite Principal Design Engineer mastering Apple Human Interface Guidelines (HIG), Cupertino spring physics, Tailwind CSS, Lucide icons, glassmorphism, responsive Bento grids, and OpenDots CopilotKit visual agent canvas patterns.

When asked to design a component, layout, or interactive agent interface:
1. Deliver a complete, self-contained, runnable HTML5 + CSS3 / Tailwind / modern inline style component wrapped in ```html ... ``` code fences.
2. Ensure rich visual polish: sub-pixel borders, frosted glassmorphism (backdrop-filter: blur(20px)), subtle spring animations (cubic-bezier(0.23, 1, 0.32, 1)), dark-mode aesthetic, and tactile hover states.
3. Make the component interactive: buttons should toggle states, sliders should update numbers, cards should react to clicks, and animations should feel alive with JavaScript.
4. If designing for OpenDots, include visual state dots (pulsing avatar nodes, thread channels, CopilotKit status pills, and reactive agent state).
5. Always explain the design choices, typography scale, and interaction physics after the code block.
"""


@app.post("/v1/agents/chat")
async def chat_with_agent(req: AgentChatRequest):
    print(f"[AGENT_CHAT] ENTERED: agent={req.agent}, mode={req.mode}, model={req.model}", flush=True)
    """
    Direct interactive chat, visual design, and code generation endpoint for Claude Code, Codex, Aider, OpenDots, and Orchestrator.
    Supports instant visual UI generation (mode='design') and non-interactive CLI dispatch (mode='cli').
    """
    cwd = req.working_dir or str(Path(__file__).resolve().parent)
    agent = req.agent.lower().strip()
    msg = req.message.strip()
    mode = (req.mode or "design").lower().strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    start_time = time.time()

    # Fast AI Design & Visual Generation Mode (direct gateway model router)
    if mode in ["design", "code", "auto"] or agent in ["opendots"]:
        # 1. Claude Mode (AWS Bedrock Opus 4.6 / Sonnet 4.6)
        if agent == "claude" and bedrock is not None:
            model_id = "us.anthropic.claude-sonnet-4-6"
            if req.model and "opus" in req.model:
                model_id = "us.anthropic.claude-opus-4-6-v1"
            elif req.model in ["sonnet", "claude-sonnet"]:
                model_id = "us.anthropic.claude-sonnet-4-6"
            
            print(f'[AGENT_CHAT] Calling Bedrock converse with model {model_id}... (bedrock={bedrock is not None})', flush=True)
            try:
                loop = asyncio.get_running_loop()
                resp = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: bedrock.converse(
                            modelId=model_id,
                            system=[{"text": DESIGN_SYSTEM_PROMPT}],
                            messages=[{"role": "user", "content": [{"text": msg}]}],
                            inferenceConfig={"maxTokens": 3500, "temperature": 0.7}
                        )
                    ),
                    timeout=85.0
                )
                print(f"[AGENT_CHAT] Bedrock converse FINISHED in {time.time() - start_time:.2f}s", flush=True)
                out_msg = resp["output"]["message"]
                text_parts = [b["text"] for b in out_msg.get("content", []) if "text" in b]
                full_text = "\n".join(text_parts).strip()
                code = _extract_code_block(full_text)
                dur = round(time.time() - start_time, 2)
                return {
                    "status": "ok",
                    "agent": "claude",
                    "model": model_id,
                    "mode": mode,
                    "response": full_text,
                    "code": code,
                    "duration_seconds": dur,
                    "exit_code": 0
                }
            except Exception as e:
                print(f"[AGENT_CHAT] Bedrock EXCEPTION: {type(e).__name__}: {e}", flush=True)

        # 2. OpenDots Mode (CopilotKit Generative UI Canvas & Visual Dots)
        elif agent == "opendots":
            opendots_prompt = f"{DESIGN_SYSTEM_PROMPT}\n\nTask: Generate an OpenDots interactive generative UI canvas component with visual state dots, reactive agent channels, and living document cards for: {msg}"
            # Route to Bedrock if available, else local router
            if bedrock is not None:
                try:
                    loop = asyncio.get_running_loop()
                    resp = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: bedrock.converse(
                                modelId="us.anthropic.claude-sonnet-4-6",
                                system=[{"text": opendots_prompt}],
                                messages=[{"role": "user", "content": [{"text": msg}]}],
                                inferenceConfig={"maxTokens": 3500, "temperature": 0.7}
                            )
                        ),
                        timeout=85.0
                    )
                    full_text = "\n".join([b["text"] for b in resp["output"]["message"].get("content", []) if "text" in b]).strip()
                    code = _extract_code_block(full_text)
                    return {
                        "status": "ok",
                        "agent": "opendots",
                        "model": "us.anthropic.claude-opus-4-6-v1",
                        "mode": mode,
                        "response": full_text,
                        "code": code,
                        "duration_seconds": round(time.time() - start_time, 2),
                        "exit_code": 0
                    }
                except Exception as e:
                    print(f"[OpenDots Fallback] {e}")

        # 3. Direct Gateway Chat Completions fallback for Codex, Aider, Orchestrator
        try:
            target_model = req.model if req.model and req.model != "auto" else "claude"
            comp_req = ChatCompletionRequest(
                model=target_model,
                messages=[
                    ChatMessage(role="system", content=DESIGN_SYSTEM_PROMPT),
                    ChatMessage(role="user", content=msg)
                ],
                max_tokens=4096,
                temperature=0.7
            )
            res = await invoke_model_with_fallback(comp_req, target_model)
            full_text = res.get("choices", [{}])[0].get("message", {}).get("content", "")
            code = _extract_code_block(full_text)
            dur = round(time.time() - start_time, 2)
            return {
                "status": "ok",
                "agent": agent,
                "model": res.get("model", target_model),
                "mode": mode,
                "response": full_text,
                "code": code,
                "duration_seconds": dur,
                "exit_code": 0
            }
        except Exception as e:
            print(f"[Gateway Design Fallback Error] {e}")

    # Fallback to CLI subprocess execution (if mode == 'cli' or fallback requested)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    extra_bins = os.pathsep.join([
        str(Path.home() / ".local" / "bin"),
        str(Path.home() / "bin"),
        str(Path.home() / "AppData" / "Roaming" / "npm"),
        "/opt/homebrew/bin",
        "/usr/local/bin",
    ])
    env["PATH"] = f"{extra_bins}{os.pathsep}{env.get('PATH', '')}"

    if agent == "claude":
        env["CLAUDE_CODE_USE_BEDROCK"] = env.get("CLAUDE_CODE_USE_BEDROCK", "1")
        env["AWS_REGION"] = env.get("AWS_REGION", "us-east-1")
        env["AWS_DEFAULT_REGION"] = env.get("AWS_DEFAULT_REGION", "us-east-1")
        env["AWS_PROFILE"] = env.get("AWS_PROFILE", os.environ.get("AWS_PROFILE", "default"))
        env["ANTHROPIC_MODEL"] = "us.anthropic.claude-opus-4-6-v1" if (req.model and "opus" in req.model) else "us.anthropic.claude-sonnet-4-6"
        clean_prompt = msg.replace('"', '\\"')
        cmd = f'claude -p "{clean_prompt}" --dangerously-skip-permissions'

    elif agent == "codex":
        clean_prompt = msg.replace('"', '\\"')
        cmd = f'codex exec "{clean_prompt}" --dangerously-bypass-approvals-and-sandbox'

    elif agent == "aider":
        clean_prompt = msg.replace('"', '\\"')
        cmd = f'aider --openai-api-base http://127.0.0.1:8000/v1 --openai-api-key dummy-local-key --model openai/auto --message "{clean_prompt}" --exit --no-git --yes-always --no-show-model-warnings'

    elif agent == "orchestrator":
        clean_prompt = msg.replace('"', '\\"')
        py_exe = sys.executable
        orch_py = str((Path(__file__).resolve().parent / "orchestrate.py").resolve())
        cmd = f'"{py_exe}" "{orch_py}" --task "{clean_prompt}" --no-shield'

    else:
        cmd = f'claude -p "{msg.replace('"', '\\"')}" --dangerously-skip-permissions'

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cwd
        )
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=180)
        dur = round(time.time() - start_time, 2)
        stdout_txt = stdout_b.decode("utf-8", errors="replace").strip()
        stderr_txt = stderr_b.decode("utf-8", errors="replace").strip()
        out = stdout_txt if stdout_txt else stderr_txt
        code = _extract_code_block(out)

        return {
            "status": "ok" if proc.returncode == 0 else "error",
            "agent": agent,
            "mode": "cli",
            "response": out,
            "code": code,
            "stderr": stderr_txt if proc.returncode != 0 else "",
            "duration_seconds": dur,
            "exit_code": proc.returncode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution error running {agent}: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("laptop_api_server:app", host="127.0.0.1", port=8000, reload=False)
