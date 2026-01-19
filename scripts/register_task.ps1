param(
  [string]$Time = "15:00"
)

$ErrorActionPreference = 'Stop'

$root = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$python = (Get-Command python).Source
$venv = Join-Path $root '.venv\\Scripts\\Activate.ps1'
$script = Join-Path $root 'scripts\\run_daily.ps1'

if (-not (Test-Path $script)) { throw "Script non trovato: $script" }

$taskName = 'AiSiteDaily'

# Create task action
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`""

# Create trigger at specific time daily
$trigger = New-ScheduledTaskTrigger -Daily -At (Get-Date $Time)

# Register task
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Description 'Genera articolo giornaliero per Ai-site' -Force | Out-Null

Write-Host "Task '$taskName' registrato alle $Time ogni giorno."

