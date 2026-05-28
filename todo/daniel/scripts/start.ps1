# 一鍵啟動 backend + frontend。
# 用法：在專案根目錄執行  .\scripts\start.ps1
#
# 行為：
#   1. 檢查 8000 / 5173 狀態：正常 reuse、卡住才砍、沒人 listen 才開新視窗
#   2. backend (uvicorn) / frontend (vite) 各自一個 PowerShell 視窗
#   3. 等 backend、frontend healthcheck 通過後開瀏覽器
#
# 關閉用 .\scripts\stop.ps1（無條件砍 port）

$ErrorActionPreference = "Stop"

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[start] 找不到 backend venv：$VenvPython" -ForegroundColor Red
    Write-Host "        請先 cd backend; py -3.13 -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"
    exit 1
}
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "[start] 找不到 frontend/node_modules，先跑一次 npm install" -ForegroundColor Yellow
    Push-Location $FrontendDir
    npm install
    Pop-Location
}

function Test-PortListening($port) {
    $line = (netstat -ano | Select-String ":$port\s.*LISTENING")
    return [bool]$line
}

function Stop-PortListener($port) {
    $line = (netstat -ano | Select-String ":$port\s.*LISTENING")
    if (-not $line) { return }
    foreach ($l in $line) {
        $parts = $l.ToString().Trim() -split "\s+"
        $procId = $parts[-1].Trim()
        if ($procId -match "^\d+$") {
            Write-Host "[start] kill stale listener on :$port (PID $procId)" -ForegroundColor DarkGray
            & taskkill /F /PID $procId 2>$null | Out-Null
        }
    }
}

function Test-HttpOk($url) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

# 回傳：'reuse' / 'restart' / 'new'
function Resolve-PortAction($port, $healthUrl) {
    if (-not (Test-PortListening $port)) { return 'new' }
    if (Test-HttpOk $healthUrl)         { return 'reuse' }
    return 'restart'
}

$backendHealth  = "http://127.0.0.1:8000/docs"
$frontendHealth = "http://localhost:5173/"

$backendAction  = Resolve-PortAction 8000 $backendHealth
$frontendAction = Resolve-PortAction 5173 $frontendHealth

function Start-BackendWindow {
    Write-Host "[start] launching backend (uvicorn) ..." -ForegroundColor Cyan
    $backendCmd = "Set-Location '$BackendDir'; & '$VenvPython' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
    Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-NoExit", "-Command", $backendCmd `
        -WindowStyle Normal | Out-Null
}

function Start-FrontendWindow {
    Write-Host "[start] launching frontend (vite) ..." -ForegroundColor Cyan
    $frontendCmd = "Set-Location '$FrontendDir'; npm run dev"
    Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-NoExit", "-Command", $frontendCmd `
        -WindowStyle Normal | Out-Null
}

switch ($backendAction) {
    'reuse'   { Write-Host "[start] backend  :8000 already healthy -> reuse" -ForegroundColor Green }
    'restart' { Write-Host "[start] backend  :8000 listener stuck -> restart" -ForegroundColor Yellow
                Stop-PortListener 8000
                Start-BackendWindow }
    'new'     { Write-Host "[start] backend  :8000 no listener -> new start" -ForegroundColor Cyan
                Start-BackendWindow }
}

switch ($frontendAction) {
    'reuse'   { Write-Host "[start] frontend :5173 already healthy -> reuse" -ForegroundColor Green }
    'restart' { Write-Host "[start] frontend :5173 listener stuck -> restart" -ForegroundColor Yellow
                Stop-PortListener 5173
                Start-FrontendWindow }
    'new'     { Write-Host "[start] frontend :5173 no listener -> new start" -ForegroundColor Cyan
                Start-FrontendWindow }
}

function Wait-Health($name, $url) {
    Write-Host "[start] waiting for $name on $url ..." -NoNewline
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Milliseconds 500
        if (Test-HttpOk $url) { Write-Host " up" -ForegroundColor Green; return $true }
        Write-Host "." -NoNewline
    }
    Write-Host " timeout" -ForegroundColor Yellow
    return $false
}

if ($backendAction -ne 'reuse') {
    [void](Wait-Health "backend" $backendHealth)
}
if ($frontendAction -ne 'reuse') {
    [void](Wait-Health "frontend" $frontendHealth)
}

Write-Host ""
Write-Host "  Backend  : http://127.0.0.1:8000  (docs: /docs)"
Write-Host "  Frontend : http://localhost:5173"
Write-Host ""
Write-Host "[start] opening browser ..." -ForegroundColor Cyan
Start-Process "http://localhost:5173"
