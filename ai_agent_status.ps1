# Comprehensive Workstation & AI Agent Health Check (Hardware-Adaptive)

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$sysPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$env:Path = "$userPath;$sysPath"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "     AUTONOMOUS AI WORKSTATION HEALTH DASHBOARD" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Hardware info
$cs = Get-CimInstance Win32_ComputerSystem
$proc = Get-CimInstance Win32_Processor | Select-Object -First 1
$os = Get-CimInstance Win32_OperatingSystem
$gpus = Get-CimInstance Win32_VideoController

$totalRamGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$freeRamGB = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$usedRamGB = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 1)

Write-Host "System Model : $($cs.Manufacturer) $($cs.Model)"
Write-Host "Processor    : $($proc.Name.Trim()) ($($proc.NumberOfCores) Cores, $($proc.NumberOfLogicalProcessors) Threads)"
Write-Host "Memory (RAM) : $usedRamGB GB used / $totalRamGB GB total ($freeRamGB GB free)"
foreach ($g in $gpus) {
    Write-Host "GPU Adapter  : $($g.Name)"
}

Write-Host "`n--- AI & Developer Tools ---" -ForegroundColor Yellow
$tools = @("git", "uv", "python", "node", "pnpm", "ollama", "aws", "claude", "codex", "aider", "opencode")
foreach ($t in $tools) {
    $cmd = Get-Command $t -ErrorAction SilentlyContinue
    if ($cmd) {
        Write-Host " [OK] $t -> $($cmd.Source)" -ForegroundColor Green
    } else {
        Write-Host " [OPTIONAL] $t (not in PATH)" -ForegroundColor DarkGray
    }
}

Write-Host "`n--- Cloud & AWS Bedrock Connectivity ---" -ForegroundColor Yellow
$awsProfile = if ($env:AWS_PROFILE) { $env:AWS_PROFILE } else { "default" }
try {
    $awsId = aws sts get-caller-identity --profile $awsProfile --output json 2>$null | ConvertFrom-Json
    if ($awsId) {
        Write-Host " [OK] AWS Connected (Profile: $awsProfile)" -ForegroundColor Green
    } else {
        Write-Host " [INFO] AWS Profile '$awsProfile' not active (using BYOK / Local Ollama)" -ForegroundColor Gray
    }
} catch {
    Write-Host " [INFO] AWS CLI optional session not active (using BYOK / Local Ollama)" -ForegroundColor Gray
}

Write-Host "`n--- Local AI & API Servers ---" -ForegroundColor Yellow
try {
    $ollama = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2
    Write-Host " [OK] Ollama Service : RUNNING (http://127.0.0.1:11434)" -ForegroundColor Green
    foreach ($m in $ollama.models) {
        $sizeGB = [math]::Round($m.size / 1GB, 2)
        Write-Host "       Model: $($m.name) ($sizeGB GB)" -ForegroundColor Gray
    }
} catch {
    Write-Host " [STOPPED] Ollama Service is not running." -ForegroundColor Red
}

try {
    $api = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2
    Write-Host " [OK] Unified AI Gateway : RUNNING (http://127.0.0.1:8000)" -ForegroundColor Green
    Write-Host "       Dashboard         : http://127.0.0.1:8000/dashboard" -ForegroundColor Cyan
    Write-Host "       Graphify Explorer : http://127.0.0.1:8000/graphify" -ForegroundColor Cyan
    Write-Host "       Bedrock Ready: $($api.bedrock_ready) | Ollama Ready: $($api.ollama_ready)" -ForegroundColor Gray
} catch {
    Write-Host " [STOPPED] Unified API Server is not running. Run '.\start_laptop_api.ps1'" -ForegroundColor Yellow
}

Write-Host "==========================================================" -ForegroundColor Cyan
