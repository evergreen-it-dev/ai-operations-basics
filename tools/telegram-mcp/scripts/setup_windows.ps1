# Telegram MCP — Windows one-shot setup
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File tools\telegram-mcp\scripts\setup_windows.ps1
#
# Before run: put real api_id + api_hash in workspace\keys\telegram (from my.telegram.org)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $Root

Write-Host "== Telegram MCP setup ==" -ForegroundColor Cyan

# Bun
if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
    Write-Host "Installing bun..." -ForegroundColor Yellow
    npm install -g bun
}

# Keys -> .env
py tools\telegram-mcp\scripts\sync_telegram_keys.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# LF normalize .env (Windows CRLF breaks Bun env reader)
py -c "from pathlib import Path; p=Path('tools/telegram-mcp/.env'); t=p.read_text(encoding='utf-8'); p.write_text(t.replace('\r\n','\n'), encoding='utf-8', newline='\n')"

# Validate api_id not placeholder
$envText = Get-Content "tools\telegram-mcp\.env" -Raw
if ($envText -match 'TELEGRAM_API_ID=12345678' -or $envText -match 'TELEGRAM_API_ID=2040' -or $envText -match 'TELEGRAM_API_ID=6\s') {
    Write-Host ""
    Write-Host "ERROR: workspace\keys\telegram has placeholder or blocked public API keys." -ForegroundColor Red
    Write-Host "Get real keys from https://my.telegram.org/apps (phone + 4G often works)." -ForegroundColor Yellow
    Write-Host "Then re-run this script." -ForegroundColor Yellow
    exit 1
}

Set-Location tools\telegram-mcp
bun install

# MCP config
Set-Location $Root
py tools\telegram-mcp\scripts\sync_telegram_mcp.py

Write-Host ""
Write-Host "Starting server on http://localhost:3000 ..." -ForegroundColor Green
Write-Host "After start: open the auth URL from log, click QR, scan with your Telegram account" -ForegroundColor Green
Write-Host ""

Set-Location tools\telegram-mcp
bun start
