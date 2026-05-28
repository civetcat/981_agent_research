@echo off
REM 雙擊就能啟動的 wrapper：呼叫 PowerShell 腳本並繞過 ExecutionPolicy。
setlocal
set "ROOT=%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
