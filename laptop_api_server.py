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
  <title>Antigravity Autonomous Workstation Gateway</title>
  <style>
    :root {
      --bg: #0b0f17;
      --card-bg: #121824;
      --card-border: #1e293b;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.15);
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      padding: 24px;
      line-height: 1.5;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 16px;
    }
    .header h1 {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .badge-online {
      background: rgba(16, 185, 129, 0.15);
      color: var(--success);
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 18px;
    }
    .kpi-title {
      font-size: 0.8rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 6px;
    }
    .kpi-val {
      font-size: 1.7rem;
      font-weight: 700;
      color: var(--text);
    }
    .kpi-sub {
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-top: 4px;
    }
    .section-title {
      font-size: 1.1rem;
      font-weight: 600;
      margin-bottom: 12px;
      color: var(--accent);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .tiers-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .tier-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 16px;
      transition: border-color 0.2s;
    }
    .tier-card:hover {
      border-color: var(--accent);
    }
    .tier-badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.7rem;
      font-weight: 600;
      margin-bottom: 8px;
      background: rgba(56, 189, 248, 0.1);
      color: var(--accent);
    }
    .tier-name {
      font-weight: 600;
      font-size: 1rem;
      margin-bottom: 4px;
    }
    .tier-desc {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-bottom: 8px;
    }
    .tier-price {
      font-size: 0.75rem;
      color: var(--success);
      font-family: monospace;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
      margin-top: 8px;
    }
    th, td {
      padding: 10px 12px;
      text-align: left;
      border-bottom: 1px solid var(--card-border);
    }
    th {
      color: var(--text-muted);
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.75rem;
    }
    .mono { font-family: monospace; }
    .interactive-panel {
      margin-top: 24px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }
    @media (max-width: 900px) {
      .interactive-panel { grid-template-columns: 1fr; }
    }
    textarea, select, button {
      width: 100%;
      background: #0d121c;
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 0.9rem;
      margin-bottom: 12px;
      font-family: inherit;
    }
    button {
      background: var(--accent);
      color: #0b0f17;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: opacity 0.2s;
    }
    button:hover { opacity: 0.9; }
    .output-box {
      background: #090c12;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px;
      font-family: monospace;
      font-size: 0.8rem;
      height: 220px;
      overflow-y: auto;
      white-space: pre-wrap;
      color: #cbd5e1;
    }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1><span>⚡</span> Antigravity Autonomous Workstation</h1>
      <p style="color: var(--text-muted); font-size: 0.85rem;">Unified Multi-Provider AI Gateway & Orchestrator Control Plane</p>
    </div>
    <div style="display: flex; gap: 12px; align-items: center;">
      <span class="badge-online" id="status-badge">ONLINE • 127.0.0.1:8000</span>
      <button onclick="fetchStats()" style="width: auto; margin-bottom: 0; padding: 6px 14px; font-size: 0.8rem;">Refresh</button>
    </div>
  </div>

  <div class="kpi-grid">
    <div class="card">
      <div class="kpi-title">Total Spend (USD)</div>
      <div class="kpi-val" id="total-usd">$0.0000</div>
      <div class="kpi-sub" id="requests-count">0 total requests logged</div>
    </div>
    <div class="card">
      <div class="kpi-title">Smart-Tier Savings</div>
      <div class="kpi-val" style="color: var(--success);" id="saved-usd">$0.0000</div>
      <div class="kpi-sub">vs Claude Opus baseline</div>
    </div>
    <div class="card">
      <div class="kpi-title">Total Tokens</div>
      <div class="kpi-val" id="total-tokens">0</div>
      <div class="kpi-sub" id="tokens-sub">0 prompt / 0 completion</div>
    </div>
    <div class="card">
      <div class="kpi-title">Gateway Health</div>
      <div class="kpi-val" style="color: var(--accent);" id="active-models">21 Models</div>
      <div class="kpi-sub" id="latency-ms">Checking ping...</div>
    </div>
  </div>

  <div class="section-title">⚡ 5-Tier Smart Auto-Routing Hierarchy</div>
  <div class="tiers-grid">
    <div class="tier-card">
      <span class="tier-badge" style="color: var(--success); background: rgba(16,185,129,0.1);">TIER 1 • LOCAL GPU ($0.00)</span>
      <div class="tier-name">Ollama AMD Vulkan GPU</div>
      <div class="tier-desc">Llama 3.2 1B running on AMD Radeon RX 5500M discrete GPU. Zero latency, 100% offline, zero credit spend.</div>
      <div class="tier-price">Cost: $0.00 / 1M tokens • Used for docs, format, typos</div>
    </div>
    <div class="tier-card">
      <span class="tier-badge">TIER 2 • FAST SCOUT</span>
      <div class="tier-name">Llama 4 Scout (Bedrock / BYOK)</div>
      <div class="tier-desc">Ultra-fast sub-second responses for boilerplate, scripts, HTML/CSS tweaks, and unit tests.</div>
      <div class="tier-price">Cost: $0.08 in / $0.30 out per 1M tokens</div>
    </div>
    <div class="tier-card">
      <span class="tier-badge" style="color: #a78bfa; background: rgba(167,139,250,0.1);">TIER 3 • PRODUCTION CODER</span>
      <div class="tier-name">Llama 3.3 70B Instruct</div>
      <div class="tier-desc">Full-stack feature engineering, complex refactoring, and AST-compliant code generation.</div>
      <div class="tier-price">Cost: $0.72 in / $0.72 out per 1M tokens</div>
    </div>
    <div class="tier-card">
      <span class="tier-badge" style="color: #f59e0b; background: rgba(245,158,11,0.1);">TIER 4 • REASONER CRITIC</span>
      <div class="tier-name">DeepSeek R1 Reasoning</div>
      <div class="tier-desc">Chain-of-thought analysis, bug investigation, and Frontier Critic consensus review (--judge).</div>
      <div class="tier-price">Cost: $1.35 in / $2.19 out per 1M tokens</div>
    </div>
    <div class="tier-card">
      <span class="tier-badge" style="color: #ec4899; background: rgba(236,72,153,0.1);">TIER 5 • FRONTIER FLAGSHIP</span>
      <div class="tier-name">Claude Sonnet 4.5 & Opus 4.5</div>
      <div class="tier-desc">System architecture, security audits, and multi-file cross-repo orchestrations.</div>
      <div class="tier-price">Cost: Sonnet ($3/$15) • Opus ($15/$75) per 1M</div>
    </div>
  </div>

  <div class="interactive-panel">
    <div class="card">
      <div class="section-title">🧪 Live Gateway Playground</div>
      <label style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-bottom: 4px;">Model Tier / Alias</label>
      <select id="test-model">
        <option value="auto">auto (5-Tier Smart Routing)</option>
        <option value="local">local (Ollama GPU - $0.00)</option>
        <option value="fast">fast (Llama 4 Scout)</option>
        <option value="coder">coder (Llama 3.3 70B)</option>
        <option value="reasoner">reasoner (DeepSeek R1)</option>
        <option value="claude">claude (Claude Sonnet 4.5)</option>
        <option value="opus">opus (Claude Opus 4.5)</option>
      </select>
      <label style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-bottom: 4px;">Test Prompt</label>
      <textarea id="test-prompt" rows="3" placeholder="Enter task instruction or prompt...">Explain in 1 sentence how the 5-tier router conserves credits.</textarea>
      <button onclick="runTestPrompt()" id="run-btn">Execute on Gateway</button>
      <div class="output-box" id="test-output">Awaiting prompt execution...</div>
    </div>

    <div class="card">
      <div class="section-title">📊 Token & Spend Breakdown</div>
      <div style="overflow-x: auto; max-height: 380px;">
        <table id="spend-table">
          <thead>
            <tr>
              <th>Model / Provider</th>
              <th>Requests</th>
              <th>Prompt Tokens</th>
              <th>Compl Tokens</th>
              <th>Cost (USD)</th>
            </tr>
          </thead>
          <tbody id="spend-tbody">
            <tr><td colspan="5" style="color: var(--text-muted);">Loading spend telemetry...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    async function fetchStats() {
      const startT = performance.now();
      try {
        const hResp = await fetch('/health');
        const hData = await hResp.json();
        const lat = Math.round(performance.now() - startT);
        document.getElementById('latency-ms').innerText = `${lat}ms latency • Ollama GPU OK`;
        document.getElementById('active-models').innerText = `${hData.active_models || 21} Models`;
        document.getElementById('status-badge').innerText = `ONLINE • ${lat}ms PING`;
      } catch (e) {
        document.getElementById('status-badge').innerText = 'OFFLINE';
        document.getElementById('status-badge').style.color = 'var(--danger)';
      }

      try {
        const uResp = await fetch('/v1/usage');
        const uData = await uResp.json();
        const totals = uData.totals || {};
        const totalUsd = totals.estimated_usd || 0;
        const pTok = totals.prompt_tokens || 0;
        const cTok = totals.completion_tokens || 0;
        
        document.getElementById('total-usd').innerText = `$${totalUsd.toFixed(4)}`;
        document.getElementById('requests-count').innerText = `${totals.requests || 0} total requests logged`;
        document.getElementById('total-tokens').innerText = (pTok + cTok).toLocaleString();
        document.getElementById('tokens-sub').innerText = `${pTok.toLocaleString()} in / ${cTok.toLocaleString()} out`;

        // Calculate savings vs Opus
        const opusCost = (pTok * 15.0 / 1e6) + (cTok * 75.0 / 1e6);
        const saved = Math.max(0, opusCost - totalUsd);
        document.getElementById('saved-usd').innerText = `$${saved.toFixed(4)}`;

        // Table
        const tbody = document.getElementById('spend-tbody');
        tbody.innerHTML = '';
        const byModel = uData.by_model || {};
        if (Object.keys(byModel).length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" style="color: var(--text-muted);">No requests logged yet.</td></tr>';
        } else {
          for (const [m, stat] of Object.entries(byModel)) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td class="mono" style="color: var(--accent);">${m}</td>
              <td>${stat.requests}</td>
              <td class="mono">${stat.prompt_tokens.toLocaleString()}</td>
              <td class="mono">${stat.completion_tokens.toLocaleString()}</td>
              <td class="mono" style="color: var(--success); font-weight: 600;">$${(stat.estimated_usd || 0).toFixed(4)}</td>
            `;
            tbody.appendChild(tr);
          }
        }
      } catch (e) {
        console.error('Error fetching usage stats:', e);
      }
    }

    async function runTestPrompt() {
      const model = document.getElementById('test-model').value;
      const prompt = document.getElementById('test-prompt').value;
      const outBox = document.getElementById('test-output');
      const btn = document.getElementById('run-btn');
      
      btn.disabled = true;
      btn.innerText = 'Dispatching to Gateway...';
      outBox.innerText = `[DISPATCHING] Model: ${model}...\n`;

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
          outBox.innerText = `[SUCCESS - ${duration}ms | Model: ${data.model}]\n\n${data.choices[0].message.content}\n\n[Usage: ${data.usage?.prompt_tokens} in / ${data.usage?.completion_tokens} out]`;
        } else {
          outBox.innerText = `[ERROR]\n` + JSON.stringify(data, null, 2);
        }
        fetchStats();
      } catch (err) {
        outBox.innerText = `[GATEWAY ERROR]: ${err.message}`;
      } finally {
        btn.disabled = false;
        btn.innerText = 'Execute on Gateway';
      }
    }

    fetchStats();
    setInterval(fetchStats, 5000);
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
        if target["provider"] == "ollama" or alias == "local" or True:
            try:
                ollama_messages = []
                for sp in system_prompts:
                    ollama_messages.append({"role": "system", "content": sp["text"]})
                for cm in converse_messages:
                    ollama_messages.append({"role": cm["role"], "content": cm["content"][0]["text"]})
                
                ollama_body = {
                    "model": target.get("id", "llama3.2:1b"),
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


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    clean_model_name = req.model.replace("openai/", "").replace("bedrock/", "").replace("ollama/", "")
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
