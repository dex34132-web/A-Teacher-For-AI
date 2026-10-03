$ErrorActionPreference = 'Stop'

$packageName = 'school'
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Install school.exe
Install-ChocolateyPackage -PackageName $packageName `
    -FileType 'exe' `
    -File "$toolsDir\school.exe" `
    -SilentArgs 'install'

Write-Host "School has been installed successfully."
Write-Host "Restart OpenCode to use School tools."
