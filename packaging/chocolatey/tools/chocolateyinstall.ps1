$ErrorActionPreference = 'Stop'

$packageName = 'lerev'
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Install lerev.exe
Install-ChocolateyPackage -PackageName $packageName `
    -FileType 'exe' `
    -File "$toolsDir\lerev.exe" `
    -SilentArgs 'install'

Write-Host "Lerev has been installed successfully."
Write-Host "Restart OpenCode to use Lerev tools."
