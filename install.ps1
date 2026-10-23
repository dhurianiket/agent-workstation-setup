# Universal AI Agent Workstation Installer for Windows (v3.6)
# Supports both 1-line remote install AND running inside a cloned repository:
#   Remote: irm https://raw.githubusercontent.com/dhurianiket/agent-workstation-setup/main/install.ps1 | iex
#   Local : .\install.ps1

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "     ANTIGRAVITY AUTONOMOUS AI WORKSTATION — UNIVERSAL WINDOWS INSTALLER        " -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# 1. Package Management via Winget
Write-Host "[1/5] Checking & installing developer CLI dependencies (Git, uv, Node, Ollama)..." -ForegroundColor Yellow
$wingetPackages = @("Git.Git", "astral-sh.uv", "OpenJS.NodeJS.LTS", "pnpm.pnpm", "Ollama.Ollama", "GitHub.cli")
foreach ($pkg in $wingetPackages) {
    winget install --id $pkg --silent --accept-package-agreements --accept-source-agreements --erroraction silentlycontinue | Out-Null
}

# Refresh PATH in current session
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$sysPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$env:Path = "$userPath;$sysPath;$HOME\.local\bin"

# 2. Resolve Repository Directory (use current folder if already cloned, else clone to ~/.agent-workstation/repo)
if (Test-Path (Join-Path (Get-Location) "tools\setup_wizard.py")) {
    $repoDir = (Get-Location).Path
    Write-Host "[2/5] Using existing cloned repository at: $repoDir" -ForegroundColor Green
} else {
    $installDir = "$HOME\.agent-workstation"
    if (-not (Test-Path $installDir)) { New-Item -ItemType Directory -Path $installDir -Force | Out-Null }
    $repoDir = "$installDir\repo"
    if (-not (Test-Path "$repoDir\.git")) {
        Write-Host "[2/5] Cloning agent-workstation-setup repository..." -ForegroundColor Yellow
        git clone https://github.com/dhurianiket/agent-workstation-setup.git $repoDir
    } else {
        Write-Host "[2/5] Updating existing workstation repository at $repoDir..." -ForegroundColor Yellow
        git -C $repoDir pull --ff-only
    }
}
Set-Location $repoDir

# 3. Install Agent Harnesses & GitGuardian Security Shield
Write-Host "[3/5] Installing AI agent harnesses (Aider, GitGuardian ggshield, Claude Code, Codex)..." -ForegroundColor Yellow
uv tool install aider-chat 2>$null
uv tool install ggshield 2>$null
if (Get-Command npm -ErrorAction SilentlyContinue) {
    npm install -g @anthropic-ai/claude-code @openai/codex 2>$null
}

# 4. Create Python Virtual Environment & Install Gateway + MCP + Graphify Packages
Write-Host "[4/5] Creating Python virtual environment (.venv) and installing Gateway + Graphify + MCP..." -ForegroundColor Yellow
if (-not (Test-Path "$repoDir\.venv")) {
    uv venv .venv
}
$venvPy = "$repoDir\.venv\Scripts\python.exe"
uv pip install --python $venvPy fastapi uvicorn boto3 pydantic requests "mcp<2" graphifyy ggshield

# 5. Run All-In-One Setup Wizard (Hardware Detection, Ollama Model, Interactive API Keys, 32 Repos, Antigravity Plugin & Gateway Daemon)
Write-Host "[5/5] Launching All-In-One Setup Wizard (Ollama Model + Personal API Keys + 32 GitHub Repos + Gateway Daemon)..." -ForegroundColor Cyan
& $venvPy "$repoDir\tools\setup_wizard.py" $args

Write-Host "`n================================================================================" -ForegroundColor Green
Write-Host " [OK] ANTIGRAVITY AUTONOMOUS WORKSTATION IS READY!" -ForegroundColor Green
Write-Host "  • Live Web Dashboard & API Keys : http://127.0.0.1:8000/dashboard" -ForegroundColor Cyan
Write-Host "  • Interactive Graphify AST      : http://127.0.0.1:8000/graphify" -ForegroundColor Cyan
Write-Host "  • How It Works Guide            : python orchestrate.py --guide" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Green
