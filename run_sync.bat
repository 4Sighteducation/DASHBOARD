@echo off
REM VESPA Dashboard Sync Script
REM Syncs data from Knack to Supabase

setlocal enabledelayedexpansion

REM Set working directory to script location
cd /d "%~dp0"

REM Create logs directory if it doesn't exist
if not exist "sync_logs" mkdir sync_logs

REM Generate timestamp for log file
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ("%time%") do (set mytime=%%a%%b)
set mytime=%mytime: =0%
set logfile=sync_logs\sync_%mydate%_%mytime%.log

echo ========================================== >> "%logfile%" 2>&1
echo VESPA Dashboard Sync Started >> "%logfile%" 2>&1
echo Date: %date% >> "%logfile%" 2>&1
echo Time: %time% >> "%logfile%" 2>&1
echo ========================================== >> "%logfile%" 2>&1
echo. >> "%logfile%" 2>&1

REM Check if Python is available
python --version >> "%logfile%" 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH >> "%logfile%" 2>&1
    exit /b 1
)

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment... >> "%logfile%" 2>&1
    call venv\Scripts\activate.bat >> "%logfile%" 2>&1
)

REM Run the sync script
echo Running sync_knack_to_supabase.py... >> "%logfile%" 2>&1
python sync_knack_to_supabase.py >> "%logfile%" 2>&1 2>&1
set sync_result=%errorlevel%

REM Check if sync was successful
if %sync_result% equ 0 (
    echo. >> "%logfile%" 2>&1
    echo ========================================== >> "%logfile%" 2>&1
    echo SYNC COMPLETED SUCCESSFULLY >> "%logfile%" 2>&1
    echo End Time: %time% >> "%logfile%" 2>&1
    echo ========================================== >> "%logfile%" 2>&1
    
    REM Keep only last 30 log files
    echo Cleaning up old logs... >> "%logfile%" 2>&1
    for /f "skip=30 delims=" %%f in ('dir /b /o-d sync_logs\sync_*.log 2^>nul') do (
        del "sync_logs\%%f" >> "%logfile%" 2>&1
    )
) else (
    echo. >> "%logfile%" 2>&1
    echo ========================================== >> "%logfile%" 2>&1
    echo ERROR: SYNC FAILED WITH EXIT CODE %sync_result% >> "%logfile%" 2>&1
    echo End Time: %time% >> "%logfile%" 2>&1
    echo ========================================== >> "%logfile%" 2>&1
    
    REM Send notification or alert here if needed
)

REM Copy latest sync report to a fixed location for monitoring
if exist "sync_report_*.txt" (
    for /f "delims=" %%f in ('dir /b /o-d sync_report_*.txt 2^>nul') do (
        copy "%%f" "sync_logs\latest_sync_report.txt" >nul 2>&1
        goto :done
    )
)
:done

endlocal
exit /b %sync_result%