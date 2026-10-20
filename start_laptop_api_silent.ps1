# Silent AI Stack Service Auto-Starter (Hardware & Path Agnostic)
# Automatically starts Ollama GPU engine and Unified AI API server

$WorkDir = $PSScriptRoot
$LogDir = Join-Path $HOME ".agent_workstation"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
$logPath = Join-Path $LogDir "laptop_api_autostart.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# 1. Check Ollama
$ollamaRunning = $false
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    $ollamaRunning = $true
} catch {
    $ollamaRunning = $false
}

if (-not $ollamaRunning) {
    $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    $ollamaExe = if ($ollamaCmd) { $ollamaCmd.Source } else { Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe" }
    if (Test-Path $ollamaExe) {
        Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        Add-Content -Path $logPath -Value "[$timestamp] Ollama daemon started."
    }
}

# 2. Check Unified AI API Server
$apiRunning = $false
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -ErrorAction Stop
    $apiRunning = $true
} catch {
    $apiRunning = $false
}

if (-not $apiRunning) {
    $venvCandidates = @(
        (Join-Path $WorkDir ".venv\Scripts\pythonw.exe"),
        (Join-Path $WorkDir "Skyvern\.venv\Scripts\pythonw.exe")
    )
    $pythonw = "pythonw.exe"
    foreach ($cand in $venvCandidates) {
        if (Test-Path $cand) {
            $pythonw = $cand
            break
        }
    }
    $serverScript = Join-Path $WorkDir "laptop_api_server.py"
    if (Test-Path $serverScript) {
        Start-Process -FilePath $pythonw -ArgumentList "`"$serverScript`"" -WorkingDirectory $WorkDir -WindowStyle Hidden
        Add-Content -Path $logPath -Value "[$timestamp] Unified AI API Server launched from $WorkDir."
    }
}
