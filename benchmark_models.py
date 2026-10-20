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
        print("=" * 65)
    except urllib.error.URLError as e:
        print(f"[ERROR] Could not fetch models from {API_BASE}/v1/models: {e}")

if __name__ == "__main__":
    benchmark_gateway()
