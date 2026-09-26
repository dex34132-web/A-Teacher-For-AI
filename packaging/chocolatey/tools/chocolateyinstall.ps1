$ErrorActionPreference = 'Stop'

$packageName = 'teacher'
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Install teacher.exe
Install-ChocolateyPackage -PackageName $packageName `
    -FileType 'exe' `
    -File "$toolsDir\teacher.exe" `
    -SilentArgs 'install'

Write-Host "Teacher has been installed successfully."
Write-Host "Restart OpenCode to use Teacher tools."
