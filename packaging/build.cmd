@echo off
REM Portable exe build (bypasses PowerShell execution policy).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
