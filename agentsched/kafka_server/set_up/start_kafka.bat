@echo off
title Kafka Kraft Mode Starter

REM Set Kafka home directory
set KAFKA_HOME=D:\Zack\kafka

REM Change to Kafka directory
cd /d %KAFKA_HOME%

REM Check if meta.properties exists and extract cluster ID if it does
set CLUSTER_ID=
if exist \tmp\kraft-broker-logs\meta.properties (
    for /f "tokens=2 delims==" %%a in ('findstr /B "cluster.id" \tmp\kraft-broker-logs\meta.properties') do set CLUSTER_ID=%%a
    if not defined CLUSTER_ID (
        echo Failed to read existing Cluster ID. Generating a new one.
        for /f "delims=" %%i in ('.\bin\windows\kafka-storage.bat random-uuid') do set CLUSTER_ID=%%i
    ) else (
        echo Using existing Cluster ID: %CLUSTER_ID%
    )
) else (
    REM Generate new cluster ID if meta.properties doesn't exist
    for /f "delims=" %%i in ('.\bin\windows\kafka-storage.bat random-uuid') do set CLUSTER_ID=%%i
    echo Generated new Cluster ID: %CLUSTER_ID%
)

REM Format storage directory
echo Formatting storage directory...
set /p REFORMAT=Directory is already formatted. Do you want to reformat? (y/n): 
if /i "%REFORMAT%"=="y" (
    .\bin\windows\kafka-storage.bat format -t %CLUSTER_ID% -c .\config\kraft\server.properties --ignore-formatted
) else (
    echo Skipping format. Using existing directory.
)

if %ERRORLEVEL% neq 0 (
    echo Error during storage directory operation
    pause
    exit /b 1
)

echo Kafka storage directory operation completed.

REM Start Kafka in KRaft mode
echo Starting Kafka in KRaft mode...
start cmd /k ".\bin\windows\kafka-server-start.bat .\config\kraft\server.properties"

echo Kafka startup initiated in a new window.
pause