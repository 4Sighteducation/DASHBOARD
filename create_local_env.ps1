# PowerShell script to create .env from Heroku config

Write-Host "Creating local .env file from Heroku config..." -ForegroundColor Cyan

# Get values from Heroku
$knack_app_id = heroku config:get KNACK_APP_ID -a vespa-dashboard
$knack_api_key = heroku config:get KNACK_API_KEY -a vespa-dashboard
$supabase_url = heroku config:get SUPABASE_URL -a vespa-dashboard
$supabase_key = heroku config:get SUPABASE_KEY -a vespa-dashboard

# Create .env file
$env_content = @"
# Auto-generated from Heroku config
KNACK_APP_ID=$knack_app_id
KNACK_API_KEY=$knack_api_key
SUPABASE_URL=$supabase_url
SUPABASE_KEY=$supabase_key
"@

# Write to file
$env_content | Out-File -FilePath ".env" -Encoding UTF8

Write-Host ".env file created successfully!" -ForegroundColor Green
Write-Host "You can now run: python sync_knack_to_supabase_optimized.py" -ForegroundColor Yellow