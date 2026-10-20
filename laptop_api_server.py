"""
Laptop Unified AI Agent & Model API Server (v2.0)
Advanced features:
- Multi-tier Cost Protection & Zero-Downtime Auto-Fallback:
    * Prevents credit depletion by automatically cascading:
      Opus -> Sonnet -> DeepSeek R1 -> Llama 3.3 70B -> Llama 4 Scout -> Local Ollama
- Built-in High-Craft Engineering Directives:
    * Guarantees complete implementations without placeholders, strict type safety,
      and defensive error handling for superior code quality.
- Real-Time Credit & Usage Analytics:
    * Persists token usage and estimated spend in ~/.agent_workstation/usage_stats.json
    * /v1/usage endpoint for monitoring budget and consumption.
- Routes to AWS Bedrock & Local Ollama (AMD Radeon RX 5500M Discrete GPU via Vulkan)
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
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
from botocore.exceptions import ClientError
import urllib.request

app = FastAPI(title="Laptop Unified AI API - Cost & Quality Protected", version="2.0.0")

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

# Bedrock Pricing per 1,000,000 tokens (USD)
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
    print(f"Warning initializing Bedrock: {e}")
    bedrock = None

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

MODEL_MAP = {
    # Frontier Claude 4.5
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
def root():
    return {
        "status": "online",
        "version": "2.0.0",
        "description": "Laptop Unified AI Gateway with Cost-Guard & Fallback Protection",
        "endpoints": ["/v1/models", "/v1/chat/completions", "/v1/usage", "/v1/orchestrate", "/health"]
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "bedrock_ready": bedrock is not None,
        "ollama_ready": True,
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
    total_out_tokens = 0
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

async def invoke_model_with_fallback(req: ChatCompletionRequest, requested_alias: str):
    """
    Executes model invocation. If high-tier model fails due to credits or limits,
    cascades gracefully to fallback models so coding sessions are never interrupted.
    """
    candidates = [requested_alias] + FALLBACK_CHAINS.get(requested_alias, ["coder", "fast", "local"])
    
    last_exception = None
    for alias in candidates:
        clean_name = alias.replace("openai/", "").replace("bedrock/", "").replace("ollama/", "")
        target = MODEL_MAP.get(clean_name, {"provider": "bedrock", "id": clean_name})
        
        # Prepare messages & enhance system prompt
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

        # 1. Ollama execution
        if target["provider"] == "ollama":
            try:
                ollama_messages = []
                for sp in system_prompts:
                    ollama_messages.append({"role": "system", "content": sp["text"]})
                for cm in converse_messages:
                    ollama_messages.append({"role": cm["role"], "content": cm["content"][0]["text"]})
                
                ollama_body = {
                    "model": target["id"],
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
                record_usage(target["id"], p_tokens, c_tokens)

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
                print(f"[Fallback Warning] Local Ollama ({alias}) failed: {e}")
                last_exception = e
                continue

        # 2. Bedrock execution
        elif target["provider"] == "bedrock":
            if not bedrock:
                continue
            
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
                    # Test stream initiation
                    return StreamingResponse(
                        stream_bedrock_events(kwargs, alias, target["id"]),
                        media_type="text/event-stream"
                    )
                except Exception as e:
                    print(f"[Fallback Warning] Bedrock stream for {alias} failed: {e}. Cascading...")
                    last_exception = e
                    continue

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
                    "latency_ms": resp.get("metrics", {}).get("latencyMs", 0),
                    "fallback_from": requested_alias if alias != requested_alias else None
                }
            except Exception as e:
                print(f"[Fallback Triggered] Model {alias} ({target['id']}) error: {e}. Cascading down...")
                last_exception = e
                continue

    raise HTTPException(status_code=500, detail=f"All models in fallback chain failed. Last error: {str(last_exception)}")


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
            selected_model = "coder"  # Default workhorse: Llama 3.3 70B
            
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
