# Master AI Developer Tools, Repositories & Agent Ecosystem Manifest

A unified catalog of all 32 curated GitHub repositories powering full-stack development, AI agent workflows, UI/UX engineering, and media automation across your machines. Automatically cloned and indexed into 456+ `SKILL.md` runbooks by `python tools/setup_wizard.py` and `python tools/manage_tools.py sync`.

All curated tools can be audited or synchronized at any time with:
```bash
python tools/manage_tools.py audit
# or to clone/update all 32 repositories:
python tools/manage_tools.py sync
```

---

## 1. Autonomous AI Agents, Coding Harnesses & Memory

These repositories focus on local/cloud agent execution, persistent memory, and multi-provider routing for heavy development workflows.

| Repository | Purpose & Superpower | Local Status |
| :--- | :--- | :--- |
| [**`decolua/9router`**](https://github.com/decolua/9router) | **Free Multi-Provider Router**: Connects Claude Code, Cursor, Cline, and Antigravity to 40+ free AI providers with auto-fallback and -40% RTK token compression. | Installed (`tools/9router`) |
| [**`ruvnet/ruflo`**](https://github.com/ruvnet/ruflo) | **Swarm Harness**: Multi-agent swarm coordinator with adaptive memory, vector RAG, and native Claude Code / Codex / Hermes integration. | Installed (`tools/ruflo`) |
| [**`google-antigravity/antigravity-sdk-python`**](https://github.com/google-antigravity/antigravity-sdk-python) | **Antigravity SDK**: Official Python SDK for building autonomous agents leveraging the Antigravity setup. | Documented & Linked |
| [**`Gitlawb/openclaude`**](https://github.com/Gitlawb/openclaude) | **Open Claude Harness**: Model-agnostic terminal coding-agent harness allowing Claude Code-style workflows with any backend LLM. | Installed (`tools/openclaude`) |
| [**`1jehuang/jcode`**](https://github.com/1jehuang/jcode) | **Rust Memory-Efficient Agent**: Ultra-low memory footprint coding agent harness ideal when running alongside local models. | Installed (`tools/jcode`) |
| [**`Panniantong/agent-reach`**](https://github.com/Panniantong/agent-reach) | **Live Internet Eyes**: Gives AI agents zero-fee read and search access across YouTube, GitHub, Reddit, and X. | Installed (`tools/agent-reach`) |
| [**`rohitg00/agentmemory`**](https://github.com/rohitg00/agentmemory) | **Persistent Agent Memory**: #1 benchmarked persistent memory layer retaining cross-session project context and bug patterns. | Installed (`tools/agentmemory`) |
| [**`EfficientStreet/hindsight`**](https://github.com/EfficientStreet/hindsight) | **Agent Post-Mortem System**: Records past execution errors and root causes so coding agents don't repeat the same debugging mistakes. | Installed (`tools/hindsight`) |
| [**`CopilotKit/OpenDots`**](https://github.com/CopilotKit/OpenDots) | **Autonomous AI Coworker**: Framework for embedding collaborative agentic workflows directly into applications. | Installed (`tools/OpenDots`) |
| [**`templetongroup/radiant`**](https://github.com/templetongroup/radiant) | **Shared Conversation Swarms**: Enables multi-agent collaboration within a single shared conversation thread. | Installed (`tools/radiant`) |
| [**`ChromeDevTools/chrome-devtools-mcp`**](https://github.com/ChromeDevTools/chrome-devtools-mcp) | **Chrome DevTools MCP**: Official MCP server giving coding agents live access to Chrome DevTools for DOM inspection and debugging. | Configured & Active |

---

## 2. AI Video Generation, Post-Production & Media Automation

Directly applicable to programmatic video editing, media pipelines, and automated post-production workflows.

| Repository | Purpose & Superpower | Local Status |
| :--- | :--- | :--- |
| [**`WyattBlue/auto-editor`**](https://github.com/WyattBlue/auto-editor) | **Automated Rough Cuts**: Command-line tool for automatically analyzing audio/video to cut out dead air and silences instantly. | Installed (`uv tool: auto-editor`) |
| [**`remotion-dev/remotion`**](https://github.com/remotion-dev/remotion) | **Programmatic Video via React**: Create automated motion graphics, video intros, captions, and dynamic video renders using React and TypeScript. | Documented & Linked |
| [**`wide-trace/open-higgsfield`**](https://github.com/wide-trace/open-higgsfield) | **AI Video Studio**: Open-source studio workspace for multi-model AI video generation and cinematic camera control. | Installed (`tools/open-higgsfield`) |
| [**`navi3582/higgsfield-video`**](https://github.com/navi3582/higgsfield-video) | **Higgsfield Video Tooling**: Multi-model video generation pipeline for programmatic video rendering. | Installed (`tools/higgsfield-video`) |
| [**`meituan-longcat/LongCat-Video`**](https://github.com/meituan-longcat/LongCat-Video) | **Long-Form Video Synthesis**: Foundational model for unified AI video generation. | Installed (`tools/LongCat-Video`) |
| [**`smontlouis/bible-strong-avatar-lab`**](https://github.com/smontlouis/bible-strong-avatar-lab) | **Avatar & Character Lab**: Avatar generation workflow for character-driven video and media storytelling. | Installed (`tools/bible-strong-avatar-lab`) |

---

## 3. UI/UX, Frontend Design & Architecture Systems

Useful for polishing React/Next.js/Vite frontends, designing high-craft interfaces, and mapping system architectures.

| Repository | Purpose & Superpower | Local Status |
| :--- | :--- | :--- |
| [**`Graphify-Labs/graphify`**](https://github.com/Graphify-Labs/graphify) | **AST Knowledge Graph**: Converts codebases, SQL schemas, and docs into a queryable knowledge graph without vector stores. Works as a `/graphify` skill. | Installed (`tools/graphify`) |
| [**`tt-a1i/archify`**](https://github.com/tt-a1i/archify) | **Interactive Architecture Diagrams**: Converts codebase analysis directly into interactive architecture diagrams for documentation. | Installed (`tools/archify`) |
| [**`nextlevelbuilder/ui-ux-pro-max-skill`**](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | **Design Intelligence Skill**: Cross-platform design intelligence, typography, spacing, palettes, and component guidelines for coding agents. | Installed (`tools/ui-ux-pro-max-skill`) |
| [**`emilkowalski/skills`**](https://github.com/emilkowalski/skills) | **Apple Design & Animations**: Human Interface Guidelines (HIG), motion physics, spring curves, and UI polish. | Installed (`tools/emilkowalski-skills`) |
| [**`dickwu/apple-design-skill`**](https://github.com/dickwu/apple-design-skill) | **Apple HIG Reviewer Skill**: Dedicated skill for reviewing and polishing web/native interfaces against Apple design standards. | Installed (`tools/dickwu-apple-design-skill`) |
| [**`nexu-io/open-design`**](https://github.com/nexu-io/open-design) | **Collaborative AI Design**: Local-first collaborative AI workspace for generating motion, prototypes, websites, and UI assets. | Installed (`tools/open-design`) |
| [**`chenglou/pretext`**](https://github.com/chenglou/pretext) | **DOM-Less Text Layout**: Pure arithmetic text measurement bypassing DOM reflows for 10x faster canvas, markdown, and chat rendering. | Installed (`tools/pretext`) |
| [**`Kayforkind/reimagine-it`**](https://github.com/Kayforkind/reimagine-it) | **Content-Derived UI Refactoring**: Reimagines and refactors existing web interfaces directly from page content. | Installed (`tools/reimagine-it`) |
| [**`lucasmarkes/hairline`**](https://github.com/lucasmarkes/hairline) | **Interactive Isometric Graphics**: Interactive pointer-reactive line figures for React and DOM applications. | Installed (`tools/hairline`) |

---

## 4. Security, SEO, Time-Series & Specialized Research

Tools for auditing deployments, training compact models, and specialized analytical workflows.

| Repository | Purpose & Superpower | Local Status |
| :--- | :--- | :--- |
| [**`usestrix/strix`**](https://github.com/usestrix/strix) | **AI Penetration Testing**: Autonomous security pentesting agent discovering OWASP vulnerabilities and generating verified patch diffs. | Installed (`tools/strix`) |
| [**`every-app/open-seo`**](https://github.com/every-app/open-seo) | **Self-Hostable SEO Audit**: Automated SEO audit and optimization skills to boost organic discoverability for web platforms. | Installed (`tools/open-seo`) |
| [**`morluto/rea`**](https://github.com/morluto/rea) | **Reverse Engineering**: Agentic decompilation of native binaries, protocols, and undocumented APIs. | Installed (`tools/rea`) |
| [**`google-research/timesfm`**](https://github.com/google-research/timesfm) | **Time-Series Foundation Model**: Google Research foundation model for zero-shot time-series forecasting. | Installed (`tools/timesfm`) |
| [**`K-Dense-AI/scientific-agent-skills`**](https://github.com/K-Dense-AI/scientific-agent-skills) | **Scientific Agent Skills**: 50+ specialized scientific, clinical, and data pipeline skills. | Installed (`tools/scientific-agent-skills`) |
| [**`THU-MAIC/OpenMAIC`**](https://github.com/THU-MAIC/OpenMAIC) | **AI-Native Classrooms**: Interactive multi-agent educational framework for modern LMS platforms. | Installed (`tools/OpenMAIC`) |
| [**`jingyaogong/minimind`**](https://github.com/jingyaogong/minimind) | **Train Tiny LLMs**: Framework for training tiny language models from scratch on consumer hardware and local GPUs. | Installed (`tools/minimind`) |
| [**`ruvnet/RuView`**](https://github.com/ruvnet/RuView) | **WiFi Spatial Sensing**: Real-time vital sign monitoring and presence detection using ambient WiFi signals. | Installed (`tools/RuView`) |
| [**`bilawalsidhu/gods-eye-view`**](https://github.com/bilawalsidhu/gods-eye-view) | **3D Global Visualizer**: Real-time 3D global data feed visualization and spatial telemetry tracking. | Installed (`tools/gods-eye-view`) |
| [**`omacom/omarchy`**](https://github.com/omacom/omarchy) | **Keyboard Developer Linux Setup**: DHH's keyboard-centric developer OS setup for maximum coding speed. | Documented & Linked |
| [**`JetBrains/go-modern-guidelines`**](https://github.com/JetBrains/go-modern-guidelines) | **Modern Go Conventions**: Official guidelines and idiomatic practices for modern Go development. | Installed (`tools/go-modern-guidelines`) |
