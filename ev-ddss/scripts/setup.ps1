#!/usr/bin/env pwsh
# =============================================================================
# EV-DDSS Environment Setup Script (Windows PowerShell)
# =============================================================================
# Usage:
#   .\scripts\setup.ps1           # Create venv and install dependencies
#   .\scripts\setup.ps1 -Dev      # Include dev dependencies
# =============================================================================

param(
    [switch]$Dev = $false
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$VenvPath = Join-Path $ProjectRoot ".venv"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  EV-DDSS Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
$pythonVersion = python --version 2>&1
Write-Host "Python: $pythonVersion"

# Create virtual environment
if (-not (Test-Path $VenvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $VenvPath
    Write-Host "  Virtual environment created at: $VenvPath"
} else {
    Write-Host "Virtual environment already exists: $VenvPath"
}

# Activate paths
$pip = Join-Path $VenvPath "Scripts\pip.exe"
$python = Join-Path $VenvPath "Scripts\python.exe"

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
& $python -m pip install --upgrade pip --quiet

# Install requirements
Write-Host "Installing production dependencies..." -ForegroundColor Yellow
& $pip install -r (Join-Path $ProjectRoot "requirements.txt") --quiet
if ($LASTEXITCODE -ne 0) { throw "Failed to install production dependencies" }

# Install dev dependencies if requested
if ($Dev) {
    Write-Host "Installing development dependencies..." -ForegroundColor Yellow
    & $pip install -r (Join-Path $ProjectRoot "requirements-dev.txt") --quiet
    if ($LASTEXITCODE -ne 0) { throw "Failed to install dev dependencies" }

    Write-Host "Installing pre-commit hooks..." -ForegroundColor Yellow
    & $pip install pre-commit --quiet
}

# Create .env from example if not exists
$envFile = Join-Path $ProjectRoot ".env"
$envExample = Join-Path $ProjectRoot ".env.example"
if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "Created .env from .env.example - please update with your settings." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the environment:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "To run the application:"
Write-Host "  python main.py"
Write-Host ""
Write-Host "To run tests:"
Write-Host "  python main.py test"
Write-Host "  (or) pytest tests/ -v"
