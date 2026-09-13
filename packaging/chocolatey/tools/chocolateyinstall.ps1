$ErrorActionPreference = 'Stop'

$packageName = 'lerev'

# Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python is required but not found. Installing Python..."
    choco install python312 -y
}

# Refresh PATH after potential Python install
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Install Lerev via pip
pip install lerev

# Register with OpenCode
lerev install

Write-Host "Lerev has been installed successfully."
