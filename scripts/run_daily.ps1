$ErrorActionPreference = 'Stop'

$root = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$venv = Join-Path $root '.venv\\Scripts\\Activate.ps1'
$req = Join-Path $root 'requirements.txt'
$py = Join-Path $root 'scripts\\generate_daily.py'

if (Test-Path $venv) { . $venv }

if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
  throw "pip non disponibile nel PATH"
}

pip install -r $req

python $py

