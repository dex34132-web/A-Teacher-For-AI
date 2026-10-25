$ErrorActionPreference = 'Stop'

$packageName = 'toolio'
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Install toolio.exe
Install-ChocolateyPackage -PackageName $packageName `
    -FileType 'exe' `
    -File "$toolsDir\toolio.exe" `
    -SilentArgs 'install'

Write-Host "Toolio has been installed successfully."
Write-Host "Restart OpenCode to use Toolio tools."
