@echo off
title NexLoad Server
color 0A
echo.
echo  ==========================================
echo    NexLoad Server v3.0 - Starting...
echo  ==========================================
echo.
echo  Installing / updating dependencies...
echo.
pip install flask flask-cors yt-dlp --quiet --upgrade
echo.
echo  ==========================================
echo    Server is running!
echo    Keep this window OPEN while using app
echo  ==========================================
echo.
python server.py
pause
