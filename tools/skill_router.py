#!/usr/bin/env python3
"""
tools/skill_router.py
Zero-Name Automatic Repository & Skill Router for the Antigravity Workstation.

Automatically maps ANY natural-language user prompt (from ANY project directory on the laptop)
to the 32 installed tool repositories and 1,041+ SKILL.md runbooks without requiring the user
to ever mention the repository or skill name.
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

_LOCAL_TOOLS_DIR = Path(__file__).resolve().parent
_CENTRAL_TOOLS_DIR = Path.home() / ".agent-workstation" / "repo" / "tools"
TOOLS_DIR = _CENTRAL_TOOLS_DIR if (_CENTRAL_TOOLS_DIR / "9router").exists() and not (_LOCAL_TOOLS_DIR / "9router").exists() else _LOCAL_TOOLS_DIR
WORKSPACE_ROOT = TOOLS_DIR.parent
CACHE_DIR = Path.home() / ".agent_workstation"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
SKILL_INDEX_CACHE = CACHE_DIR / "skills_index_v1.json"

# Deterministic Domain-to-Repo Intent Matrix covering all 32 Curated Repos + Eko + Skyvern
DOMAIN_INTENT_MATRIX: List[Dict[str, Any]] = [
    {
        "domain": "Apple HIG & macOS/iOS Polish",
        "repos": ["dickwu-apple-design-skill", "emilkowalski-skills"],
        "keywords": ["apple", "ios", "macos", "swift", "swiftui", "hig", "glassmorphism", "sf pro", "cupertino", "ipad"],
        "priority_files": [
            "dickwu-apple-design-skill/SKILL.md",
            "emilkowalski-skills/skills/apple-design/SKILL.md",
            "emilkowalski-skills/skills/write-swift/SKILL.md"
        ]
    },
    {
        "domain": "Web Animations & Micro-Interactions",
        "repos": ["emilkowalski-skills", "hairline"],
        "keywords": ["animate", "animation", "spring", "transition", "framer", "motion", "micro-interaction", "keyframe", "toast", "sonner", "drawer"],
        "priority_files": [
            "emilkowalski-skills/skills/emil-design-eng/SKILL.md",
            "emilkowalski-skills/skills/animate/SKILL.md",
            "emilkowalski-skills/skills/animation-performance/SKILL.md",
            "hairline/skills/hairline-create/SKILL.md"
        ]
    },
    {
        "domain": "UI/UX Design Systems, Landing Pages & Frontend",
        "repos": ["ui-ux-pro-max-skill", "reimagine-it", "open-design", "pretext", "OpenDots"],
        "keywords": ["ui", "ux", "landing page", "dashboard", "tailwind", "shadcn", "component", "redesign", "layout", "typography", "color palette", "frontend", "css", "card", "modal", "button", "responsive"],
        "priority_files": [
            "ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md",
            "reimagine-it/skills/reimagine-it/SKILL.md",
            "pretext/README.md"
        ]
    },
    {
        "domain": "Modern Go (Golang) Engineering",
        "repos": ["go-modern-guidelines"],
        "keywords": ["golang", "go module", "go.mod", "goroutine", "go server", "go api", "go struct", "go test", "write go "],
        "priority_files": [
            "go-modern-guidelines/plugin/skills/use-modern-go/SKILL.md"
        ]
    },
    {
        "domain": "SEO, Copywriting & Anti-Slop Content",
        "repos": ["open-seo"],
        "keywords": ["seo", "sitemap", "meta tag", "open graph", "json-ld", "copywriting", "deslop", "ai slop", "keyword research", "competitor analysis", "serp", "marketing copy"],
        "priority_files": [
            "open-seo/.agents/skills/deslop/SKILL.md",
            "open-seo/.agents/skills/ai-visibility-audit/SKILL.md",
            "open-seo/.agents/skills/competitor-analysis/SKILL.md"
        ]
    },
    {
        "domain": "Security Auditing, Pentesting & Red-Teaming",
        "repos": ["strix"],
        "keywords": ["pentest", "vulnerability", "xss", "sqli", "csrf", "owasp", "exploit", "security scan", "penetration test", "cve", "auth bypass", "idor"],
        "priority_files": [
            "strix/README.md"
        ]
    },
    {
        "domain": "Codebase Architecture, Refactoring & Knowledge Graph",
        "repos": ["graphify", "archify", "rea"],
        "keywords": ["architecture", "refactor", "simplify codebase", "dependency graph", "knowledge graph", "module boundary", "coupling", "clean architecture", "dead code"],
        "priority_files": [
            "archify/archify/SKILL.md",
            "archify/.agents/skills/simplify-codebase/SKILL.md",
            "graphify/graphify/skill.md"
        ]
    },
    {
        "domain": "Cross-Session Agent Memory & Post-Mortems",
        "repos": ["agentmemory", "hindsight"],
        "keywords": ["remember", "recall", "memory", "handoff", "session history", "postmortem", "lesson learned", "recap"],
        "priority_files": [
            "hindsight/SKILL.md",
            "agentmemory/plugin/skills/memory-discipline/SKILL.md",
            "agentmemory/plugin/skills/recall/SKILL.md"
        ]
    },
    {
        "domain": "Time-Series Forecasting & Quantitative Analytics",
        "repos": ["timesfm"],
        "keywords": ["forecast", "time series", "timeseries", "predict trend", "anomaly detection", "seasonality", "arima", "timesfm"],
        "priority_files": [
            "timesfm/timesfm-forecasting/SKILL.md"
        ]
    },
    {
        "domain": "Scientific Research, Bioinformatics & Literature",
        "repos": ["scientific-agent-skills", "OpenMAIC"],
        "keywords": ["pubmed", "arxiv", "biorxiv", "protein", "genomics", "clinical trial", "molecule", "chembl", "citation", "literature review", "scientific"],
        "priority_files": [
            "scientific-agent-skills/README.md"
        ]
    },
    {
        "domain": "AI Video, Podcast, Documentary & Avatar Generation",
        "repos": ["cinematic-marathi-podcast-production", "open-higgsfield", "higgsfield-video", "LongCat-Video", "bible-strong-avatar-lab"],
        "keywords": ["video generation", "avatar", "lip sync", "higgsfield", "longcat", "text-to-video", "image-to-video", "storyboard", "podcast", "documentary", "marathi", "multi-cam", "google flow", "2-shot", "b-roll", "episode", "omni flash"],
        "priority_files": [
            "../skills/cinematic-marathi-podcast-production/SKILL.md",
            "open-higgsfield/README.md",
            "LongCat-Video/README.md",
            "bible-strong-avatar-lab/README.md"
        ]
    },
    {
        "domain": "Multi-Agent Swarms, Routers & Browser Automation",
        "repos": ["ruflo", "radiant", "9router", "agent-reach", "openclaude", "jcode", "RuView", "gods-eye-view", "minimind"],
        "keywords": ["multi-agent", "swarm", "browser automation", "scrape", "crawler", "playwright", "router", "subagent", "workflow automation", "spatial view", "wifi sensing"],
        "priority_files": [
            "agent-reach/agent_reach/skill/SKILL.md",
            "9router/skills/9router/SKILL.md",
            "ruflo/SKILL.md"
        ]
    }
]


def _extract_frontmatter_and_summary(md_path: Path) -> Dict[str, str]:
    """Reads name, description, and a concise instructional excerpt from a SKILL.md or README.md file."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"name": md_path.parent.name, "description": "", "excerpt": ""}

    name = md_path.parent.name
    desc = ""
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            body = parts[2].strip()
            m_name = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
            if m_name:
                name = m_name.group(1).strip().strip("'\"")
            m_desc = re.search(r"^description:\s*(?:>-\s*\n)?(.+?)(?:\n\w+:|\Z)", fm, re.MULTILINE | re.DOTALL)
            if m_desc:
                desc = " ".join(m_desc.group(1).split())[:300]

    # Clean excerpt (first 700 chars of actionable markdown body)
    clean_lines = []
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("![") or s.startswith("<img"):
            continue
        clean_lines.append(line)
        if sum(len(x) for x in clean_lines) > 750:
            break
    excerpt = "\n".join(clean_lines)[:750]
    if not desc:
        desc = excerpt[:200].replace("\n", " ")

    return {
        "name": name,
        "description": desc,
        "excerpt": excerpt
    }


def build_or_load_skill_index(force_rebuild: bool = False) -> List[Dict[str, str]]:
    """
    Builds or loads a fast cached index of all 1,041+ SKILL.md files and 32 tool repos in tools/.
    Completes in <5ms when cached.
    """
    if not force_rebuild and SKILL_INDEX_CACHE.exists():
        try:
            cache_age = time.time() - SKILL_INDEX_CACHE.stat().st_mtime
            if cache_age < 86400:
                return json.loads(SKILL_INDEX_CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass

    entries: List[Dict[str, str]] = []
    if not TOOLS_DIR.exists():
        return entries

    for repo_dir in sorted(TOOLS_DIR.iterdir()):
        if not repo_dir.is_dir() or repo_dir.name.startswith((".", "_")):
            continue
        repo_name = repo_dir.name
        skill_files = list(repo_dir.rglob("SKILL.md")) + list(repo_dir.rglob("skill.md"))
        # Deduplicate case-insensitive paths on Windows
        seen_paths = set()
        unique_skills = []
        for sf in skill_files:
            if sf.name.startswith("._") or any(part.startswith("._") for part in sf.parts):
                continue
            norm = str(sf.resolve()).lower()
            if norm not in seen_paths:
                seen_paths.add(norm)
                unique_skills.append(sf)

        if unique_skills:
            # Cap per-repo indexed skills at 80 to keep index compact and fast while covering key skills
            for sf in unique_skills[:80]:
                meta = _extract_frontmatter_and_summary(sf)
                rel_path = str(sf.relative_to(TOOLS_DIR)).replace("\\", "/")
                entries.append({
                    "repo": repo_name,
                    "name": meta["name"],
                    "rel_path": rel_path,
                    "description": meta["description"],
                    "excerpt": meta["excerpt"]
                })
        else:
            readme = repo_dir / "README.md"
            if readme.exists():
                meta = _extract_frontmatter_and_summary(readme)
                entries.append({
                    "repo": repo_name,
                    "name": repo_name,
                    "rel_path": f"{repo_name}/README.md",
                    "description": meta["description"],
                    "excerpt": meta["excerpt"]
                })

    # Also index bundled first-party skills in <REPO_ROOT>/skills/
    bundled_skills_dir = WORKSPACE_ROOT / "skills"
    if bundled_skills_dir.exists():
        for sdir in sorted(bundled_skills_dir.iterdir()):
            if not sdir.is_dir() or sdir.name.startswith((".", "_")):
                continue
            sf = sdir / "SKILL.md"
            if sf.exists():
                meta = _extract_frontmatter_and_summary(sf)
                entries.append({
                    "repo": sdir.name,
                    "name": meta["name"],
                    "rel_path": f"../skills/{sdir.name}/SKILL.md",
                    "description": meta["description"],
                    "excerpt": meta["excerpt"]
                })

    try:
        SKILL_INDEX_CACHE.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    except Exception:
        pass
    return entries


def auto_route_domain_tools(task: str, max_skills: int = 3, max_chars: int = 1600) -> Dict[str, Any]:
    """
    Analyzes a user task/prompt (without requiring tool or repo names) and returns:
      - matched_domains: list of matched domain names
      - matched_repos: list of activated repository names from the 32 installed tools
      - matched_skills: list of relative SKILL.md paths activated
      - context_block: formatted markdown block ready for prompt injection
    """
    t_lower = task.lower()
    matched_domains: List[str] = []
    matched_repos: List[str] = []
    selected_excerpts: List[str] = []
    matched_skills: List[str] = []

    # 1. Deterministic Domain Matrix Check (Round-Robin across matched domains)
    matched_rules = []
    for rule in DOMAIN_INTENT_MATRIX:
        if any(kw in t_lower for kw in rule["keywords"]):
            matched_domains.append(rule["domain"])
            matched_rules.append(rule)
            for r in rule["repos"]:
                if r not in matched_repos and (TOOLS_DIR / r).exists():
                    matched_repos.append(r)

    # First pass: pick top priority file from each matched domain
    for rule in matched_rules:
        for rel_f in rule["priority_files"]:
            full_f = TOOLS_DIR / rel_f
            if full_f.exists() and rel_f not in matched_skills and len(matched_skills) < max_skills:
                meta = _extract_frontmatter_and_summary(full_f)
                matched_skills.append(rel_f)
                selected_excerpts.append(
                    f"### [{meta['name']}] (from `tools/{rel_f}`)\n{meta['excerpt'][:480]}"
                )
                break

    # Second pass: fill remaining slots from matched domains
    if len(matched_skills) < max_skills:
        for rule in matched_rules:
            for rel_f in rule["priority_files"]:
                full_f = TOOLS_DIR / rel_f
                if full_f.exists() and rel_f not in matched_skills and len(matched_skills) < max_skills:
                    meta = _extract_frontmatter_and_summary(full_f)
                    matched_skills.append(rel_f)
                    selected_excerpts.append(
                        f"### [{meta['name']}] (from `tools/{rel_f}`)\n{meta['excerpt'][:480]}"
                    )

    # 2. Dynamic Keyword Scoring across 1,041+ SKILL.md index if slots remain
    if len(matched_skills) < max_skills:
        stop_words = {
            "the", "and", "for", "with", "that", "this", "from", "into", "update",
            "check", "make", "please", "file", "code", "build", "create", "write",
            "add", "fix", "use", "using", "project", "app", "test", "run",
            "repo", "repos", "repository", "repositories", "skill", "skills",
            "tool", "tools", "there", "where", "here", "they", "them", "their",
            "are", "not", "nit", "getting", "got", "get", "active", "activate",
            "activated", "automatically", "auto", "install", "installed",
            "give", "status", "what", "when", "why", "how", "who", "our", "your",
            "can", "will", "just", "like", "also", "created", "other", "others",
            "work", "working", "setup", "set", "everything", "right", "now", "okay"
        }
        tokens = [
            w for w in re.findall(r"[a-z0-9_-]{3,}", t_lower)
            if w not in stop_words
        ]
        if tokens:
            index = build_or_load_skill_index()
            scored = []
            for item in index:
                if item["rel_path"] in matched_skills:
                    continue
                haystack = f"{item['name']} {item['repo']} {item['description']}".lower()
                score = sum(3 if tok in item["name"].lower() else (2 if tok in haystack else 0) for tok in tokens)
                if score >= 4:
                    scored.append((score, item))
            scored.sort(key=lambda x: x[0], reverse=True)
            for _, winner in scored[: (max_skills - len(matched_skills))]:
                matched_skills.append(winner["rel_path"])
                if winner["repo"] not in matched_repos:
                    matched_repos.append(winner["repo"])
                selected_excerpts.append(
                    f"### [{winner['name']}] (from `tools/{winner['rel_path']}`)\n{winner['excerpt'][:450]}"
                )

    if not matched_skills and not matched_repos:
        return {
            "matched_domains": [],
            "matched_repos": [],
            "matched_skills": [],
            "matched_skill_abs_paths": [],
            "context_block": ""
        }

    matched_skill_abs_paths: List[str] = []
    global_skills_root = Path.home() / ".gemini" / "config" / "skills"
    for r in matched_repos[:3]:
        cand = global_skills_root / r / "SKILL.md"
        if cand.exists():
            matched_skill_abs_paths.append(str(cand.resolve()))
    for rel_s in matched_skills:
        cand2 = (TOOLS_DIR / rel_s).resolve()
        if cand2.exists() and str(cand2) not in matched_skill_abs_paths:
            matched_skill_abs_paths.append(str(cand2))

    header = (
        f"\n[AUTO-ACTIVATED WORKSTATION SKILLS & REPOS]\n"
        f"Activated Repos: {', '.join(matched_repos[:6])}\n"
        f"Activated Skills: {', '.join(matched_skills)}\n"
        f"Native Skill Paths: {', '.join(matched_skill_abs_paths[:3])}\n"
    )
    body = "\n\n".join(selected_excerpts)
    context_block = (header + body)[:max_chars] + "\n"

    return {
        "matched_domains": matched_domains,
        "matched_repos": matched_repos,
        "matched_skills": matched_skills,
        "matched_skill_abs_paths": matched_skill_abs_paths,
        "context_block": context_block
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2 or sys.argv[1] == "--index":
        idx = build_or_load_skill_index(force_rebuild=True)
        print(f"[OK] Built workstation skill index: {len(idx)} skills indexed across 32 repositories.")
        sys.exit(0)

    query = " ".join(sys.argv[1:])
    res = auto_route_domain_tools(query)
    print(json.dumps({
        "query": query,
        "matched_domains": res["matched_domains"],
        "matched_repos": res["matched_repos"],
        "matched_skills": res["matched_skills"]
    }, indent=2))
    if res["context_block"]:
        print(res["context_block"])
