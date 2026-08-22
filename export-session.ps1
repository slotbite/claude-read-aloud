# Export opencode session
$sessionId = "ses_fd88269f8ffeUm0uwPKZK1jnRu"
$output = opencode export $sessionId 2>&1
$output | Out-File -FilePath "$env:TEMP\opencode-export.json" -Encoding utf8
Write-Host "Exported to $env:TEMP\opencode-export.json"
