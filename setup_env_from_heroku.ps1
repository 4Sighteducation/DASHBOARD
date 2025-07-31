# PowerShell script to set up .env file from Heroku config

Write-Host "Setting up .env file..." -ForegroundColor Cyan

# Get existing values from heroku_backend/.env if it exists
$existing_env = @{}
if (Test-Path "heroku_backend\.env") {
    Get-Content "heroku_backend\.env" | ForEach-Object {
        if ($_ -match "^([^=]+)=(.*)$") {
            $key = $matches[1]
            $value = $matches[2]
            # Fix the KMACK typo
            if ($key -eq "KMACK_APP_ID") {
                $key = "KNACK_APP_ID"
            }
            $existing_env[$key] = $value
        }
    }
    Write-Host "Found existing values in heroku_backend\.env" -ForegroundColor Green
}

# Get Supabase values from Heroku
Write-Host "Getting Supabase credentials from Heroku..." -ForegroundColor Yellow
$supabase_url = heroku config:get SUPABASE_URL -a vespa-dashboard
$supabase_key = heroku config:get SUPABASE_KEY -a vespa-dashboard

# Merge all values
$env_content = @"
# Knack API Credentials
KNACK_APP_ID=$($existing_env['KNACK_APP_ID'])
KNACK_API_KEY=$($existing_env['KNACK_API_KEY'])

# Supabase Credentials
SUPABASE_URL=$supabase_url
SUPABASE_KEY=$supabase_key

# OpenAI (for AI features)
OPENAI_API_KEY=$($existing_env['OPENAI_API_KEY'])

# Flask Environment
FLASK_ENV=$($existing_env['FLASK_ENV'] ?? 'development')
"@

# Write to root .env file
$env_content | Out-File -FilePath ".env" -Encoding UTF8

Write-Host "`n.env file created successfully!" -ForegroundColor Green
Write-Host "You can now run: python sync_knack_to_supabase_optimized.py" -ForegroundColor Yellow

# Show what was created
Write-Host "`nCreated .env with:" -ForegroundColor Cyan
Get-Content ".env" | Select-String -Pattern "^[A-Z_]+=" | ForEach-Object {
    $line = $_.Line
    if ($line -match "^([^=]+)=") {
        $key = $matches[1]
        Write-Host "  ✓ $key" -ForegroundColor Green
    }
}