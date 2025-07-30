# Supabase Setup Guide for VESPA Dashboard

## Step 1: Get Your Supabase Credentials

1. Go to your Supabase project dashboard: https://app.supabase.com/project/vespadashboard
2. Click on **Settings** (gear icon) in the left sidebar
3. Click on **API** under Configuration
4. You'll need two values:
   - **Project URL**: This is your `SUPABASE_URL` (looks like `https://xxxxx.supabase.co`)
   - **anon public key**: This is your `SUPABASE_KEY` (a long string starting with `eyJ...`)

## Step 2: Add Environment Variables to Heroku

### Option A: Using Heroku CLI
```bash
heroku config:set SUPABASE_URL="your-project-url-here" -a your-heroku-app-name
heroku config:set SUPABASE_KEY="your-anon-public-key-here" -a your-heroku-app-name
```

### Option B: Using Heroku Dashboard
1. Go to your Heroku app dashboard
2. Click on **Settings** tab
3. Click **Reveal Config Vars**
4. Add two new variables:
   - Key: `SUPABASE_URL` | Value: Your Supabase project URL
   - Key: `SUPABASE_KEY` | Value: Your Supabase anon public key

## Step 3: Verify Connection

After adding the environment variables and deploying:

1. Check your Heroku logs:
   ```bash
   heroku logs --tail -a your-heroku-app-name
   ```

2. Look for: `Supabase connected successfully to https://xxxxx.supabase.co`

## Step 4: Create Initial Schema

Once connected, we'll run the schema creation script to set up all the required tables.

## Security Notes

- The `anon public` key is safe to use in server-side applications
- For production, consider using Row Level Security (RLS) policies
- Never expose the `service_role` key in client-side code

## Troubleshooting

If you see "Supabase connection failed" in the logs:
1. Double-check your environment variables are set correctly
2. Ensure there are no extra spaces or quotes in the values
3. Verify your Supabase project is active (not paused)