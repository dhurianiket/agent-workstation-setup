#!/usr/bin/env python3
"""
AI Agent Workstation - Models & Providers Benchmark Utility
Queries the local AI Gateway (http://127.0.0.1:8000) and displays:
1. Active Providers & Hardware Engines
2. Model Tiering Matrix (Local GPU, Scout, Coder, Reasoner, Frontier)
3. Live Gateway Latency Benchmark
"""

import sys
import time
import json
import urllib.request
import urllib.error

API_BASE = "http://127.0.0.1:8000"

def benchmark_gateway():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 65)
    print("      AI AGENT WORKSTATION: LIVE MODEL & ENGINE AUDIT")
    print("=" * 65)
    
    # 1. Health & Providers Check
    start_t = time.time()
    try:
        req = urllib.request.Request(f"{API_BASE}/health", headers={"User-Agent": "Benchmark"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            health_data = json.loads(resp.read().decode("utf-8"))
        latency_health = round((time.time() - start_t) * 1000, 1)
        print(f"[OK] Gateway Health : {health_data.get('status', 'unknown').upper()} ({latency_health}ms)")
        
        providers = health_data.get("providers", {})
        print("\nActive Provider Engines:")
        for prov, active in providers.items():
            mark = "[x] ACTIVE" if active else "[ ] inactive"
            print(f"  * {prov:<15} : {mark}")
            
    except urllib.error.URLError as e:
        print(f"[ERROR] Could not reach gateway at {API_BASE}: {e}")
        return

    # 2. Models & Tiering Audit
    start_t = time.time()
    try:
        req = urllib.request.Request(f"{API_BASE}/v1/models", headers={"User-Agent": "Benchmark"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            models_data = json.loads(resp.read().decode("utf-8"))
        latency_models = round((time.time() - start_t) * 1000, 1)
        
        model_list = models_data.get("data", [])
        print(f"\n[OK] Registered Models : {len(model_list)} models available ({latency_models}ms)")
        print("-" * 65)
        print(f"{'Alias':<18} {'Tier':<14} {'Owner':<12} {'Real Engine ID':<20}")
        print("-" * 65)
        for m in model_list:
            alias = m.get("id", "")
            tier = m.get("tier", "")
            owner = m.get("owned_by", "")
            real_id = m.get("real_model_id", "")
            print(f"{alias:<18} {tier:<14} {owner:<12} {real_id[:18]:<20}")
        print("-" * 65)
    except urllib.error.URLError as e:
        print(f"[ERROR] Could not fetch models from {API_BASE}/v1/models: {e}")

    # 3. Knowledge Graph & Usage Telemetry Audit
    try:
        req = urllib.request.Request(f"{API_BASE}/v1/graph", headers={"User-Agent": "Benchmark"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            g_data = json.loads(resp.read().decode("utf-8"))
        if g_data.get("status") == "synced" or g_data.get("nodes", 0) > 0:
            print(f"[OK] Graphify AST Graph: {g_data.get('nodes', 0):,} nodes | {g_data.get('edges', 0):,} edges | {g_data.get('communities', 0)} communities")
        else:
            print("[!] Graphify AST Graph: Not built yet")
    except Exception as e:
        print(f"[!] Could not query /v1/graph: {e}")

    try:
        req = urllib.request.Request(f"{API_BASE}/v1/usage", headers={"User-Agent": "Benchmark"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            u_data = json.loads(resp.read().decode("utf-8"))
        totals = u_data.get("totals", {})
        print(f"[OK] Credit Guard Telemetry: {totals.get('requests', 0)} reqs | ${totals.get('estimated_usd', 0.0):.4f} USD spent")
    except Exception as e:
        print(f"[!] Could not query /v1/usage: {e}")

    # 4. Live Inference & Smart Auto-Routing Latency Test
    print("\nLive Inference & Smart Auto-Router Verification:")
    for test_model, test_prompt in [
        ("auto", "Write a unit test config check: reply with 1 word PASS"),
        ("local", "Reply with 1 word READY")
    ]:
        t0 = time.time()
        try:
            payload = json.dumps({
                "model": test_model,
                "messages": [{"role": "user", "content": test_prompt}],
                "max_tokens": 12,
                "temperature": 0.0
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{API_BASE}/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "Benchmark"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                r_data = json.loads(resp.read().decode("utf-8"))
            elapsed_ms = round((time.time() - t0) * 1000, 1)
            routed_to = r_data.get("model", "unknown")
            reply = r_data["choices"][0]["message"]["content"].strip().replace("\n", " ")[:40]
            print(f"  * request='{test_model}' -> routed='{routed_to}' ({elapsed_ms}ms) : \"{reply}\"")
        except Exception as e:
            print(f"  * request='{test_model}' -> [FAIL] {e}")

    print("=" * 65)

if __name__ == "__main__":
    benchmark_gateway()
