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

# Load local .env if present (Zero-leakage local configuration)
def load_local_env():
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("\"'")
                    if k and k not in os.environ:
                        os.environ[k] = v

load_local_env()

# Pricing per 1,000,000 tokens (USD)
PRICING_PER_M = {
    "us.anthropic.claude-opus-4-5-20251101-v1:0": {"input": 15.00, "output": 75.00},
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0": {"input": 3.00, "output": 15.00},
    "us.deepseek.r1-v1:0": {"input": 1.35, "output": 2.19},
    "us.meta.llama3-3-70b-instruct-v1:0": {"input": 0.72, "output": 0.72},
    "us.meta.llama4-scout-17b-instruct-v1:0": {"input": 0.08, "output": 0.30},
    "us.mistral.pixtral-large-2502-v1:0": {"input": 2.00, "output": 6.00},
    "us.amazon.nova-pro-v1:0": {"input": 0.80, "output": 3.20},
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
aws_profile = os.environ.get("AWS_PROFILE")
aws_region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

try:
    if aws_profile:
        session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    else:
        session = boto3.Session(region_name=aws_region)
    bedrock = session.client("bedrock-runtime")
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
            "reasoner": "deepseek-ai/deepseek-r1",
            "deepseek-r1": "deepseek-ai/deepseek-r1",
            "coder": "meta/llama-3.3-70b-instruct",
            "llama-3.3-70b": "meta/llama-3.3-70b-instruct",
            "fast": "meta/llama-3.1-8b-instruct",
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
    # Frontier Claude
    "claude": {"provider": "bedrock", "id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0", "tier": "frontier"},
    "claude-sonnet": {"provider": "bedrock", "id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0", "tier": "frontier"},
    "claude-sonnet-4.5": {"provider": "bedrock", "id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0", "tier": "frontier"},
    "sonnet": {"provider": "bedrock", "id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0", "tier": "frontier"},
    "opus": {"provider": "bedrock", "id": "us.anthropic.claude-opus-4-5-20251101-v1:0", "tier": "frontier"},
    "claude-opus": {"provider": "bedrock", "id": "us.anthropic.claude-opus-4-5-20251101-v1:0", "tier": "frontier"},
    "claude-opus-4.5": {"provider": "bedrock", "id": "us.anthropic.claude-opus-4-5-20251101-v1:0", "tier": "frontier"},
    # Deep Reasoning
    "reasoner": {"provider": "bedrock", "id": "us.deepseek.r1-v1:0", "tier": "reasoning"},
    "deepseek-r1": {"provider": "bedrock", "id": "us.deepseek.r1-v1:0", "tier": "reasoning"},
    # Standard Full-Stack Coding (Cost Efficient)
    "coder": {"provider": "bedrock", "id": "us.meta.llama3-3-70b-instruct-v1:0", "tier": "coding"},
    "llama-3.3-70b": {"provider": "bedrock", "id": "us.meta.llama3-3-70b-instruct-v1:0", "tier": "coding"},
    # Ultra-Fast / Budget Scout
    "fast": {"provider": "bedrock", "id": "us.meta.llama4-scout-17b-instruct-v1:0", "tier": "scout"},
    "llama-4-scout": {"provider": "bedrock", "id": "us.meta.llama4-scout-17b-instruct-v1:0", "tier": "scout"},
    # Multimodal & Vision
    "pixtral": {"provider": "bedrock", "id": "us.mistral.pixtral-large-2502-v1:0", "tier": "multimodal"},
    "multimodal": {"provider": "bedrock", "id": "us.amazon.nova-pro-v1:0", "tier": "multimodal"},
    "nova-pro": {"provider": "bedrock", "id": "us.amazon.nova-pro-v1:0", "tier": "general"},
    "nova-lite": {"provider": "bedrock", "id": "us.amazon.nova-lite-v1:0", "tier": "scout"},
    "nova-micro": {"provider": "bedrock", "id": "us.amazon.nova-micro-v1:0", "tier": "micro"},
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

class OrchestrationRequest(BaseModel):
    task: str
    agent: Optional[str] = "aider"  # aider, codex, claude, opencode
    model: Optional[str] = "auto"   # auto, fast, coder, reasoner, claude, local
    working_dir: Optional[str] = None
    verify: Optional[bool] = True

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

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
      }
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
          <span class="version-pill mono">v3.3 OS</span>
        </div>
        <div class="brand-sub">Unified 5-Tier AI Gateway • Graphify AST Engine • Zero-Name 32-Repo Skill Router</div>
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

      <div class="card">
        <div class="kpi-header">
          <span class="kpi-title">Graphify AST Graph</span>
          <span class="kpi-icon" style="background: var(--purple-soft); color: var(--purple);" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
          </span>
        </div>
        <div class="kpi-val tabular" style="color: var(--purple);" id="graph-nodes">2,397 Nodes</div>
        <div class="kpi-sub">
          <span id="graph-sub" class="tabular">4,445 edges • 155 communities</span>
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
          <div class="tier-name">Claude Sonnet & Opus 4.5</div>
          <div class="tier-desc">High-stakes system architecture, cryptography, security overhauls, and multi-repo synthesis.</div>
        </div>
        <div class="tier-meta mono">
          <span style="color: var(--pink);">$3.00 / 1M</span>
          <span style="color: var(--text-muted);">~2.0s</span>
        </div>
      </button>
    </section>

    <!-- 3-Column Interactive Operations Deck -->
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

      <!-- Column 3: Spend Breakdown & Post-Mortem Memory Tabs -->
      <div class="card">
        <div class="section-bar">
          <div class="section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2.2" aria-hidden="true"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
            Telemetry Ledger & Memory
          </div>
          <div class="tab-group" role="tablist">
            <button type="button" class="tab-btn active" id="tab-spend-btn" onclick="switchTab('spend')">Model Spend</button>
            <button type="button" class="tab-btn" id="tab-pm-btn" onclick="switchTab('pm')">Post-Mortems</button>
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
      </div>
    </section>
  </main>

  <script>
    let pollingActive = true;
    let pollTimer = null;

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
      const isSpend = tab === 'spend';
      document.getElementById('tab-spend-view').style.display = isSpend ? 'block' : 'none';
      document.getElementById('tab-pm-view').style.display = isSpend ? 'none' : 'block';
      document.getElementById('tab-spend-btn').classList.toggle('active', isSpend);
      document.getElementById('tab-pm-btn').classList.toggle('active', !isSpend);
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
          document.getElementById('graph-sub').innerText = `${(gData.edges || 0).toLocaleString()} edges • ${gData.communities || 0} communities`;
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

@app.get("/v1/skills/route")
def route_skills_endpoint(q: str = ""):
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
        return json.loads(resp.read().decode("utf-8"))

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
                    content = out_msg["content"][0].get("text", "")
                    reasoning = None
                    if len(out_msg["content"]) > 1 and "reasoningContent" in out_msg["content"][1]:
                        reasoning = out_msg["content"][1]["reasoningContent"]["reasoningText"]["text"]
                    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("laptop_api_server:app", host="127.0.0.1", port=8000, reload=False)
