$taskName = 'AiSiteDaily'
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
  Write-Host "Task '$taskName' rimosso."
} else {
  Write-Host "Task '$taskName' non trovato."
}

