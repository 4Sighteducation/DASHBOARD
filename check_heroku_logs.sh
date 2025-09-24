#!/bin/bash

# Check Heroku logs for the calculate_national_averages.py script

echo "=== Checking recent scheduler logs for calculate_national_averages.py ==="
echo ""

# Check logs from the last 24 hours for the scheduler job
echo "1. Recent scheduler execution logs:"
heroku logs --app vespa-dashboard-9a1f84ee5341 --dyno scheduler --tail -n 1000 | grep -A 10 -B 2 "calculate_national"

echo ""
echo "=== Checking for errors in the last 24 hours ==="
echo ""

# Check for any errors related to the script
echo "2. Error logs:"
heroku logs --app vespa-dashboard-9a1f84ee5341 --tail -n 2000 | grep -i "error" | grep -i "national"

echo ""
echo "=== Checking for successful completions ==="
echo ""

# Check for successful runs
echo "3. Success messages:"
heroku logs --app vespa-dashboard-9a1f84ee5341 --tail -n 2000 | grep -E "(National average calculation task completed|Successfully created/updated|National averages)"

echo ""
echo "=== Checking Object_120 updates ==="
echo ""

# Check for Object_120 related messages
echo "4. Object_120 updates:"
heroku logs --app vespa-dashboard-9a1f84ee5341 --tail -n 2000 | grep -i "object_120"

echo ""
echo "=== Last 50 lines from today's run (midnight UTC) ==="
echo ""

# Get logs from around midnight UTC today
echo "5. Today's midnight run (filtering for 00:00-00:05 UTC):"
heroku logs --app vespa-dashboard-9a1f84ee5341 --tail -n 3000 | grep -E "2025-09-24T00:0[0-5]" | head -50

echo ""
echo "=== Checking for API rate limits or authentication issues ==="
echo ""

# Check for Knack API issues
echo "6. Knack API issues:"
heroku logs --app vespa-dashboard-9a1f84ee5341 --tail -n 2000 | grep -E "(401|403|429|rate limit|authentication|unauthorized)"

echo ""
echo "To see full logs in real-time, run:"
echo "heroku logs --app vespa-dashboard-9a1f84ee5341 --tail"
echo ""
echo "To see just today's scheduler run:"
echo "heroku logs --app vespa-dashboard-9a1f84ee5341 --dyno scheduler.1 --tail"
