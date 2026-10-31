#!/usr/bin/env python3
"""
tools/manage_tools.py
Automated Manager, Skill Registrar & Auditor for Master AI Developer Tools.
1. Clones, verifies, and audits all 32 curated tools in parallel with automatic retry.
2. Automatically registers every single one of the 32 repositories as a native Antigravity
   Skill (`SKILL.md`) in `~/.gemini/config/skills/`, `~/.gemini/config/plugins/antigravity-workstation/skills/`,
   and `.agents/skills/` so Antigravity IDE natively discovers and activates all 32 repos.
"""

import os
import re
import sys
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

TOOLS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TOOLS_DIR.parent

CURATED_REPOS: List[Tuple[str, str]] = [
    # Agent Harnesses & Memory
    ("9router", "https://github.com/decolua/9router"),
    ("ruflo", "https://github.com/ruvnet/ruflo"),
    ("openclaude", "https://github.com/Gitlawb/openclaude"),
    ("jcode", "https://github.com/1jehuang/jcode"),
    ("agent-reach", "https://github.com/Panniantong/agent-reach"),
    ("agentmemory", "https://github.com/rohitg00/agentmemory"),
    ("hindsight", "https://github.com/EfficientStreet/hindsight"),
    ("OpenDots", "https://github.com/CopilotKit/OpenDots"),
    ("radiant", "https://github.com/templetongroup/radiant"),

    # Media & Video
    ("open-higgsfield", "https://github.com/wide-trace/open-higgsfield"),
    ("higgsfield-video", "https://github.com/navi3582/higgsfield-video"),
    ("LongCat-Video", "https://github.com/meituan-longcat/LongCat-Video"),
    ("bible-strong-avatar-lab", "https://github.com/smontlouis/bible-strong-avatar-lab"),

    # UI/UX & Design Architecture
    ("graphify", "https://github.com/Graphify-Labs/graphify"),
    ("archify", "https://github.com/tt-a1i/archify"),
    ("ui-ux-pro-max-skill", "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill"),
    ("emilkowalski-skills", "https://github.com/emilkowalski/skills"),
    ("dickwu-apple-design-skill", "https://github.com/dickwu/apple-design-skill"),
    ("open-design", "https://github.com/nexu-io/open-design"),
    ("pretext", "https://github.com/chenglou/pretext"),
    ("reimagine-it", "https://github.com/Kayforkind/reimagine-it"),
    ("hairline", "https://github.com/lucasmarkes/hairline"),

    # Security, Research & Domain Specialization
    ("strix", "https://github.com/usestrix/strix"),
    ("open-seo", "https://github.com/every-app/open-seo"),
    ("rea", "https://github.com/morluto/rea"),
    ("timesfm", "https://github.com/google-research/timesfm"),
    ("scientific-agent-skills", "https://github.com/K-Dense-AI/scientific-agent-skills"),
    ("OpenMAIC", "https://github.com/THU-MAIC/OpenMAIC"),
    ("minimind", "https://github.com/jingyaogong/minimind"),
    ("RuView", "https://github.com/ruvnet/RuView"),
    ("gods-eye-view", "https://github.com/bilawalsidhu/gods-eye-view"),
    ("go-modern-guidelines", "https://github.com/JetBrains/go-modern-guidelines"),
    ("MiroFish", "https://github.com/666ghj/MiroFish"),
    ("ai-engineering-from-scratch", "https://github.com/rohitg00/ai-engineering-from-scratch"),
    ("context7", "https://github.com/upstash/context7"),
    ("magic-mcp", "https://github.com/21st-dev/magic-mcp"),
    ("TradingAgents", "https://github.com/TauricResearch/TradingAgents"),
    ("agent-skills", "https://github.com/addyosmani/agent-skills"),
    ("scrapling", "https://github.com/D4Vinci/Scrapling"),
    ("cloudflare-security-audit-skill", "https://github.com/cloudflare/security-audit-skill"),
]

REPO_SKILL_DESCRIPTIONS: Dict[str, str] = {
    "9router": "Multi-provider AI router, web fetch, embeddings, STT/TTS, image/video generation, and 40+ LLM fallback routing. Activate when configuring model routers, API gateways, or multi-provider LLM fallbacks.",
    "ruflo": "Enterprise multi-agent swarm orchestration, Claude Flow workflows, browser automation, and distributed agent teams. Activate when coordinating multi-agent swarms or parallel agent pipelines.",
    "openclaude": "Open-source Claude Code CLI harness patterns, tool-use loops, and terminal agent workflows. Activate when building or debugging CLI coding agents.",
    "jcode": "High-speed Python/Rust coding agent optimization, context compression, and fast repository editing workflows. Activate when optimizing agent execution speed or token efficiency.",
    "agent-reach": "Live internet, GitHub, X/Twitter, Reddit, YouTube, and web search/scraping capability for AI agents without paid APIs. Activate when searching external web sources, social media, or GitHub repos.",
    "agentmemory": "Persistent cross-session episodic memory, recall, recap, and memory discipline hooks for coding agents. Activate when storing or recalling project decisions, user preferences, or session history.",
    "hindsight": "Automated error post-mortem analysis, retrospective learning, and anti-regression guardrails from git commits and failures. Activate after debugging errors or conducting retrospectives.",
    "OpenDots": "Interactive CopilotKit generative UI canvas, visual state dots, and agentic frontend co-pilot patterns. Activate when building interactive agent UIs or CopilotKit integrations.",
    "radiant": "550+ specialized domain skills covering frontend design direction, brand voice, benchmarking, inference optimization, and full-stack product engineering. Activate for product engineering and benchmarking.",
    "open-higgsfield": "Open-source AI studio for multi-model image and video generation across 38+ generative models. Activate when building or running image-to-video and text-to-video pipelines.",
    "higgsfield-video": "Automated Higgsfield AI cinematic camera motion, character consistency, and video generation scripts. Activate for cinematic AI video synthesis.",
    "LongCat-Video": "Long-context, temporally consistent AI video generation and multi-scene video continuation engine. Activate when generating long-form AI video sequences.",
    "bible-strong-avatar-lab": "Expressive talking-head avatar synthesis, lip-sync alignment, and multi-character dialogue video production. Activate for avatar lip-sync or two-host video generation.",
    "graphify": "Tree-sitter AST knowledge graph builder and query engine (`graphify query/path/explain/update`). Activate for codebase architecture navigation, dependency analysis, and AST symbol lookup.",
    "archify": "Software architecture simplification, module boundary auditing, test-value analysis, and clean architecture refactoring (`simplify-codebase`). Activate when refactoring or simplifying architecture.",
    "ui-ux-pro-max-skill": "79+ UI style systems, color palettes, typography scales, banner design, and component polish rules for web and mobile apps. Activate on any UI/UX design, dashboard, or styling task.",
    "emilkowalski-skills": "Emil Kowalski's design engineering runbooks for fluid spring animations, micro-interactions, Swift/iOS polish, and animation performance. Activate when building animations, transitions, or polished UI.",
    "dickwu-apple-design-skill": "Apple Human Interface Guidelines (HIG), macOS/iOS glassmorphism, optical typography, spring physics, and Cupertino UI patterns. Activate when designing Apple-style macOS, iOS, or web interfaces.",
    "open-design": "Comprehensive creative design templates, PDF/slide layout systems, full-page visual audits, and Swiss grid typography. Activate for creative layouts, presentations, and visual design.",
    "pretext": "DOM-less high-performance canvas/WebGL text layout, multiline measurement, and sub-pixel typography rendering. Activate when optimizing text rendering or canvas layouts.",
    "reimagine-it": "Website & UI redesign engine, visual variations generator, and infographic synthesis from existing pages or wireframes. Activate when redesigning existing screens, landing pages, or infographics.",
    "hairline": "Sub-pixel 1px border, divider, and ultra-crisp layout precision patterns (`hairline-create`, `hairline-adopt`). Activate when polishing borders, grids, and high-DPI UI alignment.",
    "strix": "Autonomous OWASP Top 10 security auditing, penetration testing, vulnerability scanning, and code patch verification (`owasp-top-10-testing`, `find-security-vulnerabilities-in-code`). Activate on any security, auth, or vulnerability task.",
    "open-seo": "78+ technical SEO, AI visibility audit (`ai-visibility-audit`), keyword research, competitor analysis, and prose anti-slop (`deslop`) skills. Activate on SEO, copywriting, landing pages, or content polish.",
    "rea": "Reverse-engineering analysis (`reverse-engineer-anything`), CI test auditing, and codebase optimization runbooks. Activate when auditing unfamiliar repositories, binaries, or CI pipelines.",
    "timesfm": "Google Research TimesFM zero-shot time-series forecasting, anomaly detection, and quantitative trend prediction. Activate for forecasting, metrics prediction, or time-series analysis.",
    "scientific-agent-skills": "350+ scientific research, bioinformatics, genomics, cheminformatics, clinical trials, and literature analysis skills. Activate for scientific computing, biology, chemistry, or academic research.",
    "OpenMAIC": "Multi-agent interactive classroom, slide-craft, pedagogical persona cloning, and educational presentation synthesis. Activate when building educational content, slides, or tutoring agents.",
    "minimind": "Lightweight LLM pretraining, LoRA fine-tuning, RLHF/DPO alignment, and compact PyTorch transformer architecture reference. Activate for LLM training, fine-tuning, or PyTorch model code.",
    "RuView": "WiFi DensePose spatial sensing, RF pose estimation, and cognitive spatial telemetry (`cognitum-spaces`). Activate for spatial sensing, signal processing, or hardware telemetry tasks.",
    "gods-eye-view": "3D geospatial telemetry, aerial scene reconstruction, and spatial visualization dashboards. Activate for 3D mapping, WebGL/Three.js spatial views, or geospatial visualization.",
    "go-modern-guidelines": "JetBrains Modern Go (`use-modern-go`) idioms, Go 1.22+ standard library routing, concurrency patterns, and zero-allocation Go engineering. Activate whenever writing or reviewing Go (Golang) code.",
    "MiroFish": "High-fidelity parallel digital world social simulation and swarm intelligence prediction engine. Simulates public opinion dynamics, policy outcomes, and counterfactual events via multi-agent OASIS environment.",
    "ai-engineering-from-scratch": "542-lesson AI engineering curriculum from raw math to mini-GPT, including interactive Claude tutor skills (/find-your-level, /learn, /learn-mcp). Activate for AI engineering education, model pretraining guides, or placement assessment.",
    "context7": "Context7 up-to-date documentation engine and MCP server for AI coding agents. Feeds real-time, version-specific library docs (React, Next.js, Cloudflare, Supabase) to prevent hallucinated or deprecated APIs.",
    "magic-mcp": "21st Magic MCP server: instant access to 10,000+ production-ready React and Tailwind UI components with AI component generation directly in your coding agent.",
    "TradingAgents": "Multi-agent LLM financial trading and quantitative market research framework. Parallel analyst teams (fundamentals, sentiment, technicals) with Bull vs. Bear debate loops and risk management.",
    "agent-skills": "Addy Osmani's 25 production-grade software lifecycle skills for AI coding agents: /spec, /plan, /build, /test, /constraints, /review, /webperf, /code-simplify, and /ship.",
    "scrapling": "Adaptive web scraping, Cloudflare stealth engine (StealthyFetcher), anti-bot bypass, self-healing DOM tracking, and high-speed HTML parsing MCP server. Activate for web scraping, anti-bot handling, or WAF defense testing.",
    "cloudflare-security-audit-skill": "Cloudflare's defensive security audit skill for source-first vulnerability review, trust boundary verification, attack surface mapping, and safe reproduction across APIs, web apps, and daemons. Activate for security audits, pen tests, or vulnerability research.",
}


def _clone_single_repo(name: str, url: str) -> Tuple[str, str, str]:
    """Clones a single repository with shallow blob-filtered clone and automatic retry."""
    target_path = TOOLS_DIR / name
    if target_path.exists() and any(target_path.iterdir()):
        return (name, "present", "already installed")

    for _ in (1, 2):
        if target_path.exists():
            shutil.rmtree(target_path, ignore_errors=True)
        try:
            res = subprocess.run(
                [
                    "git", "clone", "--depth", "1", "--single-branch",
                    "--no-tags", "--filter=blob:none", url, str(target_path)
                ],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            if res.returncode == 0 and target_path.exists():
                return (name, "cloned", "cloned successfully")
            err_msg = (res.stderr or res.stdout or f"exit {res.returncode}").strip()[:120]
        except Exception as exc:
            err_msg = str(exc)[:120]
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
    return (name, "failed", err_msg)


def _strip_frontmatter(md_text: str) -> str:
    if md_text.startswith("---"):
        parts = md_text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return md_text.strip()


def register_all_32_repo_skills(extra_skill_roots: List[Path] = None) -> int:
    """
    Automatically registers every single one of the 32 curated repositories in `tools/`
    as a native Antigravity Skill (`<skill_dir>/<repo_name>/SKILL.md`) so Antigravity IDE
    discovers and activates all 32 repositories natively in `<skills>` and the UI.
    """
    home = Path.home()
    target_roots = [
        home / ".gemini" / "config" / "plugins" / "antigravity-workstation" / "skills",
        home / ".gemini" / "config" / "skills",
        REPO_ROOT / ".agents" / "skills",
    ]
    if extra_skill_roots:
        for r in extra_skill_roots:
            if r not in target_roots:
                target_roots.append(r)

    for r in target_roots:
        r.mkdir(parents=True, exist_ok=True)

    registered = 0
    for repo_name, repo_url in CURATED_REPOS:
        repo_dir = TOOLS_DIR / repo_name
        if not repo_dir.exists() or not any(repo_dir.iterdir()):
            continue

        desc = REPO_SKILL_DESCRIPTIONS.get(
            repo_name,
            f"Curated workstation skill and runbook collection from {repo_name} ({repo_url}).",
        )

        # Find all SKILL.md files inside this repo
        raw_skills = list(repo_dir.rglob("SKILL.md")) + list(repo_dir.rglob("skill.md"))
        seen = set()
        sub_skills: List[Path] = []
        for sf in raw_skills:
            if sf.name.startswith("._") or any(p.startswith("._") for p in sf.parts):
                continue
            resolved_key = str(sf.resolve()).lower()
            if resolved_key not in seen:
                seen.add(resolved_key)
                sub_skills.append(sf)

        # Pick primary instructional body
        primary_body = ""
        primary_source = ""
        if sub_skills:
            # Prefer root SKILL.md or shortest path SKILL.md
            sub_skills.sort(key=lambda p: len(p.parts))
            best_sf = sub_skills[0]
            primary_source = str(best_sf.resolve())
            try:
                primary_body = _strip_frontmatter(best_sf.read_text(encoding="utf-8", errors="replace"))[:4500]
            except Exception:
                primary_body = ""
        else:
            readme = repo_dir / "README.md"
            if readme.exists():
                primary_source = str(readme.resolve())
                try:
                    primary_body = _strip_frontmatter(readme.read_text(encoding="utf-8", errors="replace"))[:4000]
                except Exception:
                    primary_body = ""

        sub_list_lines = []
        for sf in sub_skills[:35]:
            rel = sf.relative_to(repo_dir)
            sub_list_lines.append(f"- [`{rel}`](file://{sf.resolve()})")
        if len(sub_skills) > 35:
            sub_list_lines.append(f"- *...plus {len(sub_skills) - 35} additional `SKILL.md` runbooks in `{repo_dir.resolve()}`*")

        sub_section = (
            "## Indexed Sub-Skill Runbooks in This Repository\n"
            "Read any of these specialized `SKILL.md` files directly when deeper domain rules are needed:\n"
            + "\n".join(sub_list_lines)
            + "\n\n---\n\n"
            if sub_list_lines
            else ""
        )

        skill_md_content = (
            f"---\n"
            f"name: {repo_name}\n"
            f"description: >-\n"
            f"  {desc}\n"
            f"---\n\n"
            f"# {repo_name} — Autonomous Workstation Skill\n\n"
            f"- **Installed Repository Path**: `{repo_dir.resolve()}`\n"
            f"- **Primary Source**: `{primary_source}`\n"
            f"- **Total Bundled `SKILL.md` Runbooks**: `{len(sub_skills)}`\n\n"
            f"{sub_section}"
            f"## Core Runbook & Guidelines\n\n"
            f"{primary_body}\n"
        )

        for root in target_roots:
            dest_dir = root / repo_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            (dest_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")

        registered += 1

    print(f"  [OK] Registered {registered}/32 repository skills into Antigravity global & workspace skill directories.")
    return registered


def clone_missing_tools() -> None:
    print("=" * 65)
    print("  [TOOLS MANAGER] Verifying & Syncing All 32 Curated Repositories")
    print("=" * 65)

    installed_count = 0
    cloned_count = 0
    failed_count = 0

    missing = []
    for name, url in CURATED_REPOS:
        target_path = TOOLS_DIR / name
        if target_path.exists() and any(target_path.iterdir()):
            print(f"  [OK]      {name:<26} (already present)")
            installed_count += 1
        else:
            missing.append((name, url))

    if missing:
        print(f"  [*] Cloning {len(missing)} repository(ies) in parallel (6 workers)...")
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(_clone_single_repo, n, u): n for n, u in missing}
            for fut in as_completed(futures):
                name, status, detail = fut.result()
                if status in ("present", "cloned"):
                    print(f"  [CLONED]  {name:<26} -> DONE")
                    installed_count += 1
                    if status == "cloned":
                        cloned_count += 1
                else:
                    print(f"  [FAILED]  {name:<26} -> {detail}")
                    failed_count += 1

    print("\n" + "-" * 65)
    print(f"Summary: {installed_count}/{len(CURATED_REPOS)} available ({cloned_count} newly cloned, {failed_count} failed)")
    print("-" * 65)
    register_all_32_repo_skills()


def audit_tools() -> None:
    print("\n" + "=" * 65)
    print(f"  {'TOOL NAME':<26} | {'STATUS':<12} | {'TYPE':<20}")
    print("=" * 65)

    for name, _ in CURATED_REPOS:
        target_path = TOOLS_DIR / name
        if not target_path.exists() or not any(target_path.iterdir()):
            status = "MISSING"
            tool_type = "Uncloned"
        else:
            status = "READY"
            has_py = any(target_path.glob("*.py")) or (target_path / "pyproject.toml").exists()
            has_js = (target_path / "package.json").exists()
            has_skill = (target_path / "SKILL.md").exists() or any(
                p for p in target_path.glob("**/SKILL.md") if not p.name.startswith("._")
            )

            types = []
            if has_py:
                types.append("Python")
            if has_js:
                types.append("Node/JS")
            if has_skill:
                types.append("Skill/Rule")
            tool_type = ", ".join(types) if types else "Repo/Docs"

        print(f"  {name:<26} | {status:<12} | {tool_type:<20}")
    print("=" * 65)


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "sync"
    if action == "audit":
        audit_tools()
    elif action == "register-skills":
        register_all_32_repo_skills()
    else:
        clone_missing_tools()
        audit_tools()
