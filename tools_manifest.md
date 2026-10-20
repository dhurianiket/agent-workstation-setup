# Curated AI Agent Tools & Repositories Manifest

This manifest documents all open repositories from the developer workstation, detailing their capabilities, category, installation commands, and how they empower our multi-agent architecture.

---

## 1. Codebase Graph & Architecture Intelligence

### **Graphify**
- **Repository:** https://github.com/Graphify-Labs/graphify
- **Purpose:** Converts any codebase, docs, SQL schemas, and configs into a queryable knowledge graph. Uses local deterministic AST parsing without slow/costly vector stores.
- **Harness Support:** Native `/graphify` skill for Claude Code, Cursor, Codex, and Antigravity.
- **Install Command:**
  ```bash
  git clone https://github.com/Graphify-Labs/graphify.git tools/graphify
  ```

---

## 2. Design, UI/UX & Layout Intelligence

### **UI-UX Pro Max Skill**
- **Repository:** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
- **Purpose:** Comprehensive AI skill that injects professional design systems, component guidelines, color palettes, typography, and responsive UX patterns into agent code generation.
- **Install Command:**
  ```bash
  git clone https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git tools/ui-ux-pro-max-skill
  ```

### **Apple Design Skill**
- **Repository:** https://github.com/emilkowalski/skills
- **Path:** `skills/apple-design/SKILL.md`
- **Purpose:** Curated design intelligence following Apple's Human Interface Guidelines (HIG), motion physics, spacing, and typography.
- **Install Command:**
  ```bash
  git clone https://github.com/emilkowalski/skills.git tools/emilkowalski-skills
  ```

### **Open Design**
- **Repository:** https://github.com/nexu-io/open-design
- **Purpose:** Local-first, open-source collaborative AI design agent workspace. Generates UI motion, prototypes, websites, apps, and dashboards.
- **Install Command:**
  ```bash
  git clone https://github.com/nexu-io/open-design.git tools/open-design
  ```

### **Pretext**
- **Repository:** https://github.com/chenglou/pretext
- **Purpose:** High-performance, pure JavaScript/TypeScript multiline text measurement and layout engine. Bypasses DOM reflows (`getBoundingClientRect`), making text layout 10x faster for AI agent UIs, canvas, and SVG rendering.
- **Install Command:**
  ```bash
  git clone https://github.com/chenglou/pretext.git tools/pretext
  ```

---

## 3. Web Browsing & Live Internet Intelligence

### **Agent-Reach**
- **Repository:** https://github.com/Panniantong/agent-reach
- **Purpose:** Gives agents live eyes across the entire web. Search and read Twitter/X, Reddit, YouTube transcripts, GitHub, and social platforms via a single CLI with zero API keys.
- **Install Command:**
  ```bash
  git clone https://github.com/Panniantong/agent-reach.git tools/agent-reach
  ```

### **Chrome DevTools MCP Server**
- **Repository:** https://github.com/ChromeDevTools/chrome-devtools-mcp
- **Purpose:** Official Chrome DevTools Model Context Protocol (MCP) server. Enables coding agents to directly inspect DOM, execute JavaScript, take screenshots, capture console logs, and analyze network traces in real time.
- **Install Command:**
  ```bash
  npm install -g @chromadevtools/chrome-devtools-mcp
  ```

---

## 4. Persistent Memory & Multi-Agent Swarms

### **AgentMemory**
- **Repository:** https://github.com/rohitg00/agentmemory
- **Purpose:** #1 Benchmark-proven persistent memory system for AI coding agents. Retains cross-session project context, learned patterns, and bug history across agent sessions.
- **Install Command:**
  ```bash
  git clone https://github.com/rohitg00/agentmemory.git tools/agentmemory
  ```

### **Ruflo Swarm Harness**
- **Repository:** https://github.com/ruvnet/ruflo
- **Purpose:** Multi-agent swarm coordinator with adaptive memory, self-learning intelligence, and native Claude Code / Codex / Hermes integration.
- **Install Command:**
  ```bash
  git clone https://github.com/ruvnet/ruflo.git tools/ruflo
  ```

---

## 5. Security, Reverse Engineering & Zero-Cost Routing

### **Strix AI Penetration Testing**
- **Repository:** https://github.com/usestrix/strix
- **Purpose:** Open-source AI security pentesting agent that autonomously tests applications for OWASP Top 10 vulnerabilities, unauthorized access, and logic flaws, providing verified patch diffs.
- **Install Command:**
  ```bash
  git clone https://github.com/usestrix/strix.git tools/strix
  ```

### **Rea**
- **Repository:** https://github.com/morluto/rea
- **Purpose:** Agentic reverse engineering harness. Decompiles native binaries, inspects app behaviors, protocols, and undocumented APIs.
- **Install Command:**
  ```bash
  git clone https://github.com/morluto/rea.git tools/rea
  ```

### **9router**
- **Repository:** https://github.com/decolua/9router
- **Purpose:** Free AI coding router for Claude Code, Codex, Cursor, and Antigravity. Connects to 40+ providers with automatic failover and -40% RTK token compression.
- **Install Command:**
  ```bash
  git clone https://github.com/decolua/9router.git tools/9router
  ```

---

## 6. Spatial Intelligence & Avatar Labs

### **RuView**
- **Repository:** https://github.com/ruvnet/RuView
- **Purpose:** Turns commodity WiFi signals into real-time spatial intelligence, vital sign monitoring, and human presence detection without any video cameras.
- **Install Command:**
  ```bash
  git clone https://github.com/ruvnet/RuView.git tools/RuView
  ```

### **Bible Strong Avatar Lab**
- **Repository:** https://github.com/smontlouis/bible-strong-avatar-lab
- **Purpose:** 3D avatar and spatial character laboratory.
- **Install Command:**
  ```bash
  git clone https://github.com/smontlouis/bible-strong-avatar-lab.git tools/bible-strong-avatar-lab
  ```

### **Antigravity Python SDK**
- **Repository:** https://github.com/google-antigravity/antigravity-sdk-python
- **Purpose:** Official Python library for building autonomous AI agents with native Antigravity SDK bindings.
- **Install Command:**
  ```bash
  git clone https://github.com/google-antigravity/antigravity-sdk-python.git tools/antigravity-sdk-python
  ```
