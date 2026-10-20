# Comprehensive Laptop & AI Agent Status Check

# Refresh User PATH in current session
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$sysPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$env:Path = "$userPath;$sysPath"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       LAPTOP & AI AGENT HEALTH DASHBOARD" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Hardware info
$cs = Get-CimInstance Win32_ComputerSystem
$proc = Get-CimInstance Win32_Processor | Select-Object -First 1
$os = Get-CimInstance Win32_OperatingSystem
$gpu = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -like "*5500M*" -or $_.Name -like "*Radeon*" } | Select-Object -First 1

$totalRamGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$freeRamGB = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$usedRamGB = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 1)

Write-Host "Laptop Model : $($cs.Manufacturer) $($cs.Model)"
Write-Host "Processor    : $($proc.Name.Trim()) ($($proc.NumberOfCores) Cores, $($proc.NumberOfLogicalProcessors) Threads)"
Write-Host "Memory (RAM) : $usedRamGB GB used / $totalRamGB GB total ($freeRamGB GB free)"
if ($gpu) {
    Write-Host "Discrete GPU : $($gpu.Name) (4 GB GDDR6 VRAM)"
}

# Power plan
$power = powercfg /getactivescheme
Write-Host "Power Scheme : $power"

Write-Host "`n--- AI & Developer Tools ---" -ForegroundColor Yellow
$tools = @("git", "uv", "python", "node", "pnpm", "wsl", "ollama", "aws", "claude", "codex", "aider", "opencode")
foreach ($t in $tools) {
    $cmd = Get-Command $t -ErrorAction SilentlyContinue
    if ($cmd) {
        Write-Host " [OK] $t -> $($cmd.Source)" -ForegroundColor Green
    } else {
        Write-Host " [MISSING] $t" -ForegroundColor Red
    }
}

Write-Host "`n--- AWS & Bedrock Connectivity ---" -ForegroundColor Yellow
try {
    $awsId = aws sts get-caller-identity --profile msi-lappy --output json | ConvertFrom-Json
    Write-Host " [OK] AWS Connected : $($awsId.Arn)" -ForegroundColor Green
    Write-Host "      Profile       : msi-lappy (Region: us-east-1)" -ForegroundColor Gray
} catch {
    Write-Host " [WARN] AWS CLI session expired. Run 'aws login --profile msi-lappy'" -ForegroundColor Yellow
}

Write-Host "`n--- Local AI & API Servers ---" -ForegroundColor Yellow
# Ollama
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

# Laptop API Server
try {
    $api = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2
    Write-Host " [OK] Laptop Unified API : RUNNING (http://127.0.0.1:8000)" -ForegroundColor Green
    Write-Host "       Bedrock Ready: $($api.bedrock_ready) | Ollama Ready: $($api.ollama_ready)" -ForegroundColor Gray
} catch {
    Write-Host " [STOPPED] Laptop API Server is not running. Run '.\start_laptop_api.ps1'" -ForegroundColor Yellow
}

Write-Host "==========================================================" -ForegroundColor Cyan
