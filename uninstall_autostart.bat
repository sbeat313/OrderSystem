@echo off
setlocal

set "TARGET_VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\OrderSystem_AutoStart.vbs"

if exist "%TARGET_VBS%" (
  del /f /q "%TARGET_VBS%"
  echo 已取消開機自動啟動。
) else (
  echo 尚未設定開機自動啟動。
)

endlocal
