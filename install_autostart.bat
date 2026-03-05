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

for /f "delims=" %%I in ('where pythonw.exe 2^>nul') do (
  set "PYTHONW_EXE=%%I"
  goto :got_pythonw
)

:got_pythonw
if defined PYTHONW_EXE (
  set "RUN_LINE=%PYTHONW_EXE% %APP_DIR%\web_booking_app.py"
) else (
  set "RUN_LINE=pythonw %APP_DIR%\web_booking_app.py"
)

(
  echo Set WshShell = CreateObject^("WScript.Shell"^)
  echo WshShell.CurrentDirectory = "%APP_DIR%"
  echo WshShell.Run """%RUN_LINE%""", 0, False
) > "%TARGET_VBS%"

if errorlevel 1 (
  echo 設定開機自動啟動失敗。
  exit /b 1
)

echo 已設定開機自動啟動。
echo 開機後會自動以背景模式啟動預約系統（不顯示 Command Line 視窗）。
echo 如需取消，請執行 uninstall_autostart.bat。

endlocal
