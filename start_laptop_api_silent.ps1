# Silent AI Stack Service Auto-Starter
# Automatically starts Ollama GPU engine and Laptop Unified AI API server

$logPath = "C:\Users\dhuri\.gemini\antigravity\brain\laptop_api_autostart.log"
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
    Start-Process -FilePath "C:\Users\dhuri\AppData\Local\Programs\Ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden
    Add-Content -Path $logPath -Value "[$timestamp] Ollama daemon started."
}

# 2. Check Laptop Unified AI API Server
$apiRunning = $false
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -ErrorAction Stop
    $apiRunning = $true
} catch {
    $apiRunning = $false
}

if (-not $apiRunning) {
    $pythonw = "c:\Users\dhuri\Downloads\antigravity ai workspace\pc local work\Skyvern\.venv\Scripts\pythonw.exe"
    $serverScript = "c:\Users\dhuri\Downloads\antigravity ai workspace\pc local work\laptop_api_server.py"
    $workDir = "c:\Users\dhuri\Downloads\antigravity ai workspace\pc local work"
    
    Start-Process -FilePath $pythonw -ArgumentList "`"$serverScript`"" -WorkingDirectory $workDir -WindowStyle Hidden
    Add-Content -Path $logPath -Value "[$timestamp] Laptop Unified AI API Server launched with pythonw."
}
