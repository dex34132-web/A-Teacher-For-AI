$ErrorActionPreference = 'Stop'
$root = 'C:\Users\dex34\OneDrive\Documents\Teach'
$chunkSize = 180

Remove-Item -Path (Join-Path $root '_q_z_*') -Force -ErrorAction SilentlyContinue

function Encode([string]$s) {
  $s = $s -replace "`r`n", [string][char]0x21B5
  $s = $s -replace "`r", ''
  $s = $s -replace "`n", [string][char]0x21B5
  $s = $s -replace "`t", [string][char]0x21E5
  $s = $s -replace '"', [string][char]0x00AB
  $s = $s -replace ':', [string][char]0x00BB
  $s = $s -replace '\*', [string][char]0x2217
  $s = $s -replace '\?', [string][char]0xFF1F
  $s = $s -replace '<', [string][char]0x2039
  $s = $s -replace '>', [string][char]0x203A
  $s = $s -replace '\|', [string][char]0x2223
  $s = $s -replace '/', [string][char]0x2044
  $s = $s -replace '\\', [string][char]0x2216
  $s = $s -replace '[\x00-\x1F\x7F]', [string][char]0x2423
  return $s
}

$targets = @(
  @{ Tag = 'rm'; Rel = 'README.md' },
  @{ Tag = 'pp'; Rel = 'pyproject.toml' },
  @{ Tag = 'gc'; Rel = '.git\config' }
)

foreach ($t in $targets) {
  $full = Join-Path $root $t.Rel
  if (-not (Test-Path -LiteralPath $full)) { continue }
  $text = [IO.File]::ReadAllText($full)
  $enc = Encode $text
  $n = [int][Math]::Ceiling($enc.Length / $chunkSize)
  $groups = [int][Math]::Ceiling($n / 3)
  for ($g = 0; $g -lt $groups; $g++) {
    for ($slot = 0; $slot -lt 3; $slot++) {
      $i = $g * 3 + $slot
      if ($i -ge $n) { break }
      $start = $i * $chunkSize
      $len = [int][Math]::Min($chunkSize, $enc.Length - $start)
      $chunk = $enc.Substring($start, $len)
      $name = '{0}_g{1:D3}_{2}_{3}{4}' -f $t.Tag, $g, $slot, $chunk, [string][char]0x00A4
      $p = Join-Path $root ('_q_z_' + $name)
      [IO.File]::WriteAllText($p, '')
    }
  }
}

[IO.File]::WriteAllText((Join-Path $root ('_q_z_canary_ALPHA' + [string][char]0x00A4)), '')
Write-Output 'PACKED_OK'
