@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0START-LOCAL.ps1" %*
if errorlevel 1 (
  echo.
  echo Error al iniciar. Revisa storage\runtime\*.error.log
  pause
  exit /b 1
)
echo.
echo Esperando a la consola web...
powershell.exe -NoProfile -Command "$d=(Get-Date).AddSeconds(60); while((Get-Date) -lt $d -and -not (Test-NetConnection 127.0.0.1 -Port 3001 -WarningAction SilentlyContinue -InformationLevel Quiet)){Start-Sleep 1}"
start "" http://127.0.0.1:3001
pause
