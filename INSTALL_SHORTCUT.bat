@echo off
echo.
echo  ============================================
echo   NexLoad - Create Desktop App Shortcut
echo  ============================================
echo.

:: Run the PowerShell shortcut creator
powershell.exe -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"

echo.
echo  Done! Check your Desktop for the NexLoad icon.
echo.
pause
