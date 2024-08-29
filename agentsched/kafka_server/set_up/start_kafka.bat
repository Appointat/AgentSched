@echo off
title Kafka Kraft Mode Starter

REM Set Kafka home directory
set KAFKA_HOME=D:\kafka

REM Change to Kafka directory
cd /d %KAFKA_HOME%

echo Kafka storage directory formatted successfully.

REM Start Kafka in KRaft mode
echo Starting Kafka in KRaft mode...
start cmd /k ".\bin\windows\kafka-server-start.bat .\config\kraft\server.properties"

echo Kafka startup initiated in a new window.
pause