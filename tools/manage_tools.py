#!/usr/bin/env python3
"""
tools/manage_tools.py
Automated Manager & Auditor for Master AI Developer Tools.
Clones, verifies, and audits all 32 curated tools in parallel with automatic retry
so any agent or new workstation install completes rapidly and reliably.
"""

import os
import sys
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple

TOOLS_DIR = Path(__file__).parent.resolve()

CURATED_REPOS = [
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
]


def _clone_single_repo(name: str, url: str) -> Tuple[str, str, str]:
    """Clones a single repository with shallow blob-filtered clone and automatic retry."""
    target_path = TOOLS_DIR / name
    if target_path.exists() and any(target_path.iterdir()):
        return (name, "present", "already installed")

    for attempt in (1, 2):
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
    else:
        clone_missing_tools()
        audit_tools()
