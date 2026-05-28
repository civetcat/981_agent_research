# 停止 backend (8000) 和 frontend (5173)。
# 用法：.\scripts\stop.ps1

function Stop-PortListener($port) {
    $line = (netstat -ano | Select-String ":$port\s.*LISTENING")
    if (-not $line) {
        Write-Host "[stop] :$port no listener" -ForegroundColor DarkGray
        return
    }
    foreach ($l in $line) {
        $parts = $l.ToString().Trim() -split "\s+"
        $procId = $parts[-1].Trim()
        if ($procId -match "^\d+$") {
            Write-Host "[stop] killing :$port  PID=$procId" -ForegroundColor Yellow
            & taskkill /F /PID $procId | Out-Null
        }
    }
}

Stop-PortListener 8000
Stop-PortListener 5173
Write-Host "[stop] done." -ForegroundColor Green
