"""
Laptop Unified AI Agent & Model API Server
Routes requests to:
- AWS Bedrock Frontier Models:
    * Claude Opus 4.5 (us.anthropic.claude-opus-4-5-20251101-v1:0)
    * Claude Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)
    * DeepSeek R1 671B MoE (us.deepseek.r1-v1:0)
    * Meta Llama 3.3 70B (us.meta.llama3-3-70b-instruct-v1:0)
    * Meta Llama 4 Scout (us.meta.llama4-scout-17b-instruct-v1:0)
    * Mistral Pixtral Large (us.mistral.pixtral-large-2502-v1:0)
    * Amazon Nova Pro / Lite / Micro
- Local Ollama GPU Engine:
    * Llama 3.2 1B (AMD Radeon RX 5500M Discrete GPU via Vulkan)
Exposes standard OpenAI-compatible /v1/chat/completions (with SSE streaming) and /v1/models endpoints.
"""

import os
import time
import json
import asyncio
import subprocess
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
import urllib.request

app = FastAPI(title="Laptop Unified AI API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AWS Bedrock client
try:
    session = boto3.Session(region_name="us-east-1")
    bedrock = session.client("bedrock-runtime")
except Exception as e:
    print(f"Warning initializing Bedrock: {e}")
    bedrock = None

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

# Model Mapping Table
MODEL_MAP = {
    # Frontier Claude 4.5 Models
    "claude": {"provider": "bedrock", "id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0"},
    "claude-sonnet": {"provider": "bedrock", "id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0"},
    "claude-sonnet-4.5": {"provider": "bedrock", "id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0"},
    "sonnet": {"provider": "bedrock", "id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0"},
    "opus": {"provider": "bedrock", "id": "us.anthropic.claude-opus-4-5-20251101-v1:0"},
    "claude-opus": {"provider": "bedrock", "id": "us.anthropic.claude-opus-4-5-20251101-v1:0"},
    "claude-opus-4.5": {"provider": "bedrock", "id": "us.anthropic.claude-opus-4-5-20251101-v1:0"},
    # Deep Reasoning
    "reasoner": {"provider": "bedrock", "id": "us.deepseek.r1-v1:0"},
    "deepseek-r1": {"provider": "bedrock", "id": "us.deepseek.r1-v1:0"},
    # Coding & Fast Inference
    "coder": {"provider": "bedrock", "id": "us.meta.llama3-3-70b-instruct-v1:0"},
    "llama-3.3-70b": {"provider": "bedrock", "id": "us.meta.llama3-3-70b-instruct-v1:0"},
    "fast": {"provider": "bedrock", "id": "us.meta.llama4-scout-17b-instruct-v1:0"},
    "llama-4-scout": {"provider": "bedrock", "id": "us.meta.llama4-scout-17b-instruct-v1:0"},
    # Multimodal & Vision
    "pixtral": {"provider": "bedrock", "id": "us.mistral.pixtral-large-2502-v1:0"},
    "multimodal": {"provider": "bedrock", "id": "us.amazon.nova-pro-v1:0"},
    "nova-pro": {"provider": "bedrock", "id": "us.amazon.nova-pro-v1:0"},
    "nova-lite": {"provider": "bedrock", "id": "us.amazon.nova-lite-v1:0"},
    "nova-micro": {"provider": "bedrock", "id": "us.amazon.nova-micro-v1:0"},
    # Local GPU Models (Ollama)
    "local": {"provider": "ollama", "id": "llama3.2:1b"},
    "llama3.2:1b": {"provider": "ollama", "id": "llama3.2:1b"},
    "llama3.2": {"provider": "ollama", "id": "llama3.2:1b"},
}

class ChatMessage(BaseModel):
    role: str
    content: Any

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    stream: Optional[bool] = False

class OrchestrationRequest(BaseModel):
    task: str
    agent: Optional[str] = "aider"  # aider, codex, claude, opencode
    model: Optional[str] = "claude"  # claude, opus, reasoner, coder, fast, local
    working_dir: Optional[str] = None

@app.get("/")
def root():
    return {
        "status": "online",
        "description": "Laptop Unified AI API Server",
        "endpoints": ["/v1/models", "/v1/chat/completions", "/v1/orchestrate", "/health"]
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "bedrock_ready": bedrock is not None,
        "ollama_ready": True
    }

@app.get("/v1/models")
def list_models():
    models_data = []
    for alias, info in MODEL_MAP.items():
        models_data.append({
            "id": alias,
            "object": "model",
            "created": int(time.time()),
            "owned_by": info["provider"],
            "real_model_id": info["id"]
        })
    return {"object": "list", "data": models_data}


def stream_bedrock_events(kwargs, model_alias: str):
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
                break
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    clean_model_name = req.model.replace("openai/", "").replace("bedrock/", "").replace("ollama/", "")
    target = MODEL_MAP.get(clean_model_name, {"provider": "bedrock", "id": clean_model_name})
    
    # 1. Route to Local Ollama
    if target["provider"] == "ollama":
        ollama_body = {
            "model": target["id"],
            "messages": [{"role": m.role, "content": str(m.content)} for m in req.messages],
            "stream": req.stream,
            "options": {
                "temperature": req.temperature,
                "num_predict": req.max_tokens
            }
        }
        if req.stream:
            return StreamingResponse(
                stream_ollama_events(ollama_body, req.model),
                media_type="text/event-stream"
            )
        try:
            req_data = json.dumps(ollama_body).encode("utf-8")
            url_req = urllib.request.Request(
                f"{OLLAMA_URL}/api/chat",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(url_req, timeout=60) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
            
            content = res_json.get("message", {}).get("content", "")
            return {
                "id": f"chatcmpl-local-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": res_json.get("prompt_eval_count", 0),
                    "completion_tokens": res_json.get("eval_count", 0),
                    "total_tokens": res_json.get("prompt_eval_count", 0) + res_json.get("eval_count", 0)
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ollama local inference failed: {str(e)}")

    # 2. Route to AWS Bedrock
    elif target["provider"] == "bedrock":
        if not bedrock:
            raise HTTPException(status_code=500, detail="AWS Bedrock client not initialized")
        
        converse_messages = []
        system_prompts = []
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
            return StreamingResponse(
                stream_bedrock_events(kwargs, req.model),
                media_type="text/event-stream"
            )

        try:
            resp = bedrock.converse(**kwargs)
            out_msg = resp["output"]["message"]
            content = out_msg["content"][0].get("text", "")
            
            reasoning = None
            if len(out_msg["content"]) > 1 and "reasoningContent" in out_msg["content"][1]:
                reasoning = out_msg["content"][1]["reasoningContent"]["reasoningText"]["text"]
            
            usage = resp.get("usage", {})
            return {
                "id": f"chatcmpl-bedrock-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
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
                    "prompt_tokens": usage.get("inputTokens", 0),
                    "completion_tokens": usage.get("outputTokens", 0),
                    "total_tokens": usage.get("totalTokens", 0)
                },
                "latency_ms": resp.get("metrics", {}).get("latencyMs", 0)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Bedrock invocation error: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown model provider: {target['provider']}")


@app.post("/v1/orchestrate")
async def orchestrate_agent(req: OrchestrationRequest):
    """
    Dispatches a task to an external agent harness (Aider, Claude Code, Codex, or OpenCode).
    """
    cwd = req.working_dir or os.getcwd()
    cmd = []
    
    agent_type = req.agent.lower()
    if agent_type == "aider":
        cmd = [
            "aider",
            "--openai-api-base", "http://127.0.0.1:8000/v1",
            "--openai-api-key", "dummy-key",
            "--model", f"openai/{req.model}",
            "--message", req.task,
            "--yes-always"
        ]

    elif agent_type == "claude":
        cmd = ["claude", "-p", req.task, "--dangerously-skip-permissions"]

    elif agent_type == "codex":
        if req.model in ["local", "llama3.2"]:
            cmd = ["codex", "exec", req.task, "--oss", "--local-provider", "ollama", "-m", "llama3.2:1b", "--dangerously-bypass-approvals-and-sandbox"]
        else:
            cmd = ["codex", "exec", req.task, "--dangerously-bypass-approvals-and-sandbox"]

    elif agent_type == "opencode":
        cmd = ["opencode", "run", "--prompt", req.task, "--auto"]

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported agent harness: {req.agent}")

    print(f"Orchestrating {agent_type}: {' '.join(cmd)}")
    
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
