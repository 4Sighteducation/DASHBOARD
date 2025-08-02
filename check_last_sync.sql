-- Check last sync status
SELECT 
    id,
    sync_type,
    status,
    started_at,
    completed_at,
    EXTRACT(EPOCH FROM (completed_at - started_at))/60 as duration_minutes,
    error_message,
    metadata
FROM sync_logs
ORDER BY started_at DESC
LIMIT 5;

-- Get today's sync summary
SELECT 
    DATE(started_at) as sync_date,
    COUNT(*) as sync_count,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))/60) as avg_duration_minutes
FROM sync_logs
WHERE started_at >= CURRENT_DATE
GROUP BY DATE(started_at);