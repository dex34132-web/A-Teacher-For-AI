$ErrorActionPreference = 'Stop'

$packageName = 'lerev'
$url = ''

# Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python is required but not found. Installing Python..."
    choco install python312 -y
}

# Install via pip
pip install lerev

# Register with OpenCode
lerev install
