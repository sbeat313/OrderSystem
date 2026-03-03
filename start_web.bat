@echo off
cd /d %~dp0
python web_booking_app.py
if errorlevel 1 (
  echo.
  echo 啟動失敗，請檢查上方錯誤訊息。
  pause
)
