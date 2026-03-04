@echo off
setlocal

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET_VBS=%STARTUP_DIR%\OrderSystem_AutoStart.vbs"
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"

if not exist "%STARTUP_DIR%" (
  echo 找不到 Windows 啟動資料夾：%STARTUP_DIR%
  exit /b 1
)

(
  echo Set WshShell = CreateObject^("WScript.Shell"^)
  echo WshShell.CurrentDirectory = "%APP_DIR%"
  echo WshShell.Run "cmd /c ""cd /d %APP_DIR% ^&^& python web_booking_app.py""", 0, False
) > "%TARGET_VBS%"

if errorlevel 1 (
  echo 設定開機自動啟動失敗。
  exit /b 1
)

echo 已設定開機自動啟動。
echo 開機後會自動啟動預約系統（背景執行，不需再點 start_web.bat）。
echo 如需取消，請執行 uninstall_autostart.bat。

endlocal
