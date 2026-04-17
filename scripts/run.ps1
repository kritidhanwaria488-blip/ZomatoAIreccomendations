param(
  [Parameter(Mandatory = $true, Position = 0)]
  [ValidateSet("hello", "ingest")]
  [string]$Command
)

$ErrorActionPreference = "Stop"

function Resolve-Python {
  $candidates = @("python", "python3", "py")
  foreach ($c in $candidates) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($null -ne $cmd) { return $cmd.Source }
  }
  return $null
}

$python = Resolve-Python
if (-not $python) {
  Write-Host "Could not find Python on PATH." -ForegroundColor Red
  Write-Host "Install Python 3.10+ and/or disable the Microsoft Store python alias." -ForegroundColor Yellow
  exit 1
}

& $python -m restaurant_rec $Command
