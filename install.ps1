# Universal AI Agent Workstation Installer for Windows
# Run via: irm https://raw.githubusercontent.com/dhurianiket/agent-workstation-setup/main/install.ps1 | iex

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "    UNIVERSAL AI AGENT WORKSTATION INSTALLER (WINDOWS)    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$installDir = "$HOME\.agent-workstation"
if (-not (Test-Path $installDir)) { New-Item -ItemType Directory -Path $installDir | Out-Null }
Set-Location $installDir

# 1. Package Management via Winget
Write-Host "[+] Installing developer CLI tools via winget..." -ForegroundColor Yellow
$wingetPackages = @("Git.Git", "astral-sh.uv", "OpenJS.NodeJS.LTS", "pnpm.pnpm", "Ollama.Ollama", "Amazon.AWSCLIV2", "GitHub.cli")
foreach ($pkg in $wingetPackages) {
    winget install --id $pkg --silent --accept-package-agreements --accept-source-agreements --erroraction silentlycontinue
}

# Refresh User PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$sysPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$env:Path = "$userPath;$sysPath"

# 2. Power Plan: Ultimate Performance
Write-Host "[+] Activating Ultimate Performance Power Scheme..." -ForegroundColor Yellow
powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61 | Out-Null
$schemes = powercfg -list
$ultScheme = $schemes | Where-Object { $_ -match "Ultimate Performance" } | ForEach-Object { ($_ -split "\s+")[3] }
if ($ultScheme) { powercfg /setactive $ultScheme }

# 3. Install Agent Harnesses & GitGuardian Security Shield
Write-Host "[+] Installing agent harnesses (Aider, Claude Code, Codex) & GitGuardian (ggshield)..." -ForegroundColor Yellow
uv tool install aider-chat
uv tool install ggshield
npm install -g @anthropic-ai/claude-code @openai/codex

# 4. Pull baseline Ollama model
Start-Process -FilePath "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden
Start-Sleep -Seconds 3
ollama pull llama3.2:1b

# 5. Clone Workstation Repo & Setup Virtual Environment
$repoDir = "$installDir\repo"
if (-not (Test-Path $repoDir)) {
    git clone https://github.com/dhurianiket/agent-workstation-setup.git $repoDir
}
Set-Location $repoDir

uv venv .venv
& "$repoDir\.venv\Scripts\activate.ps1"
uv pip install fastapi uvicorn boto3 requests

# 6. Install Global Antigravity Rules & Skills
$rulesTarget = "$HOME\.gemini\config\rules"
if (-not (Test-Path $rulesTarget)) { New-Item -ItemType Directory -Path $rulesTarget -Force | Out-Null }
if (Test-Path "$repoDir\rules") {
    Copy-Item -Recurse -Force "$repoDir\rules\*" $rulesTarget
}

$skillsTarget = "$HOME\.agents\skills"
if (-not (Test-Path $skillsTarget)) { New-Item -ItemType Directory -Path $skillsTarget -Force | Out-Null }
$builtinSkillsTarget = "$HOME\.gemini\antigravity\builtin\skills"
if (-not (Test-Path $builtinSkillsTarget)) { New-Item -ItemType Directory -Path $builtinSkillsTarget -Force | Out-Null }

if (Test-Path "$repoDir\skills") {
    Copy-Item -Recurse -Force "$repoDir\skills\*" $skillsTarget
    Copy-Item -Recurse -Force "$repoDir\skills\*" $builtinSkillsTarget
}

# 7. Register Startup VBScript
$startupDir = [Environment]::GetFolderPath('Startup')
Copy-Item -Force "$repoDir\StartAIStack.vbs" "$startupDir\StartAIStack.vbs"

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " [OK] UNIVERSAL AGENT WORKSTATION INSTALLED SUCCESSFULLY! " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host " - Local AI API Server : http://127.0.0.1:8000"
Write-Host " - Orchestrator CLI    : python orchestrate.py --task '...'"
Write-Host " - Next step: Run 'aws login --profile msi-lappy' to link credits."
Write-Host "==========================================================" -ForegroundColor Cyan
