#Requires -Version 5.1
<#
.SYNOPSIS
    Set up the AI Learning Engine development environment on Windows.
.DESCRIPTION
    Creates a venv, installs editable package with dev deps, and runs
    initial lint/type checks.
#>
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$VenvDir = Join-Path $ProjectRoot ".venv"

Write-Host "==> Creating virtual environment in $VenvDir ..."
python -m venv $VenvDir

Write-Host "==> Activating virtual environment ..."
& "$VenvDir\Scripts\Activate.ps1"

Write-Host "==> Upgrading pip ..."
python -m pip install --upgrade pip

Write-Host "==> Installing project in editable mode with dev dependencies ..."
pip install -e "$ProjectRoot[dev,all]"

Write-Host "==> Running initial lint check ..."
ruff check "$ProjectRoot\core" 2>$null

Write-Host "==> Running type check ..."
mypy "$ProjectRoot\core" 2>$null

Write-Host ""
Write-Host "Development environment ready."
Write-Host "Activate with:  $VenvDir\Scripts\Activate.ps1"
