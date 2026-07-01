@echo off
title Downloading FFmpeg for NexLoad
color 0B
echo.
echo  ==========================================
echo    NexLoad — FFmpeg Auto-Setup
echo  ==========================================
echo.
echo  Checking if ffmpeg already exists...

if exist "%~dp0ffmpeg\bin\ffmpeg.exe" (
    echo  [OK] FFmpeg already installed!
    goto :done
)

echo  Downloading FFmpeg (about 80MB)...
echo  Please wait...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip';" ^
  "$zip = '%~dp0ffmpeg-temp.zip';" ^
  "$out = '%~dp0ffmpeg-extract';" ^
  "Write-Host '  Downloading...' -ForegroundColor Cyan;" ^
  "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
  "Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing;" ^
  "Write-Host '  Extracting...' -ForegroundColor Cyan;" ^
  "Expand-Archive -Path $zip -DestinationPath $out -Force;" ^
  "$folder = Get-ChildItem $out -Directory | Select-Object -First 1;" ^
  "Move-Item -Path $folder.FullName -Destination '%~dp0ffmpeg' -Force;" ^
  "Remove-Item $zip -Force;" ^
  "Remove-Item $out -Recurse -Force;" ^
  "Write-Host '  Done!' -ForegroundColor Green;"

if exist "%~dp0ffmpeg\bin\ffmpeg.exe" (
    echo.
    echo  [SUCCESS] FFmpeg installed to: %~dp0ffmpeg\bin\
    goto :done
) else (
    echo.
    echo  [ERROR] Download failed. Check internet connection.
    pause
    exit /b 1
)

:done
echo.
echo  ==========================================
echo    FFmpeg is ready! 4K/8K download enabled
echo  ==========================================
echo.
pause
