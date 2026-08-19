# One-command start on Windows.  Usage:  .\quickstart.ps1  [-Port 8000] [-Seed]
param(
    [int]$Port = 8000,
    [switch]$Seed
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    Write-Host "creating virtualenv..." -ForegroundColor Cyan
    python -m venv .venv
}

$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

Write-Host "installing dependencies..." -ForegroundColor Cyan
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "created .env (demo mode, no API key needed)" -ForegroundColor Yellow
}

Write-Host "indexing knowledge base..." -ForegroundColor Cyan
& $py -m scripts.ingest --no-embed

if ($Seed) {
    Write-Host "seeding demo traffic..." -ForegroundColor Cyan
    & $py -m scripts.seed_demo
}

Write-Host ""
Write-Host "storefront  http://127.0.0.1:$Port/" -ForegroundColor Green
Write-Host "dashboard   http://127.0.0.1:$Port/admin   (token: demo-admin-token)" -ForegroundColor Green
Write-Host ""

& $py -m uvicorn app.main:app --host 127.0.0.1 --port $Port
