#!/usr/bin/env pwsh
# =============================================================================
# EV-DDSS Run Script (Windows PowerShell)
# =============================================================================
# Usage:
#   .\scripts\run.ps1             # Start the server
#   .\scripts\run.ps1 -Test       # Run the test suite
# =============================================================================

param(
    [switch]$Test = $false,
    [switch]$Dev = $false
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$VenvPath = Join-Path $ProjectRoot ".venv"
$Python = Join-Path $VenvPath "Scripts\python.exe"

# Check if virtual environment exists
if (-not (Test-Path $VenvPath)) {
    Write-Host "Virtual environment not found. Run setup.ps1 first." -ForegroundColor Red
    exit 1
}

# Change to project root
Set-Location $ProjectRoot

if ($Test) {
    Write-Host "Running tests..." -ForegroundColor Cyan
    & $Python -m pytest tests/ -v
} else {
    Write-Host "Starting EV-DDSS server..." -ForegroundColor Cyan
    if ($Dev) {
        & $Python main.py --help
    } else {
        & $Python main.py
    }
}
