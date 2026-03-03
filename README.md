# 場地預定管理程式

此版本提供：

- SQLite 本地資料庫持久化（預設 `booking.db`）
- 場地由資料庫管理（預設建立 1~6 號場）
- 用途由資料庫管理並以下拉選單選擇（單月租、雙月租、臨租、月租球友續租、股東價、連假專案、寒暑假專案、過年專案）
- 管理員 / 一般使用者雙檢視（使用者端資訊遮蔽）
- 每日 / 每週顯示切換
- 管理員檢視密碼保護（預設密碼 `admin123`，可用環境變數 `ADMIN_PASSWORD` 覆蓋）
- CLI 管理模式

## Python 版本

建議使用 **Python 3.8+**。

## 啟動 Web

### 方法 A：命令列

```bash
python web_booking_app.py
```

### 方法 B：Windows 直接雙擊

直接雙擊 `start_web.bat`。

> 若啟動失敗，視窗會停留並顯示錯誤訊息，不會立刻關閉。

啟動後開啟 `http://localhost:8000`。

## 啟動 CLI

```bash
python booking_manager.py
```

## 資料庫

- 預設資料庫檔案：`booking.db`
- 首次啟動會自動建立資料表與場地資料（1號場~6號場）

## 測試

```bash
python -m unittest discover -s tests
```
