# PowerShell script to check Heroku app status
Write-Host "Checking Heroku app status..." -ForegroundColor Green

# Check config vars
Write-Host "`nChecking environment variables:" -ForegroundColor Yellow
heroku config -a vespa-dashboard | Select-String "SUPABASE"

# Check recent logs
Write-Host "`nChecking recent logs for Supabase connection:" -ForegroundColor Yellow
heroku logs --tail -n 50 -a vespa-dashboard | Select-String "Supabase"

# Check app health
Write-Host "`nChecking app health endpoint:" -ForegroundColor Yellow
$response = Invoke-WebRequest -Uri "https://vespa-dashboard.herokuapp.com/health" -UseBasicParsing
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10

Write-Host "`nDone!" -ForegroundColor Green