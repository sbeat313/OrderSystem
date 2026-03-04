# 場地預定管理程式

此版本提供：

- SQLite 本地資料庫持久化（預設 `booking.db`）
- 場地由資料庫管理（預設建立 1~6 號場）
- 用途由資料庫管理並以下拉選單選擇（單月租、雙月租、臨租、月租球友續租、股東價、連假專案、寒暑假專案、過年專案）
- 管理員 / 一般使用者雙檢視（使用者端資訊遮蔽）
- 每日 / 每週 / 雙週顯示切換（每週與雙週會顯示借用開始-結束時間）
- 管理員檢視密碼保護（預設密碼 `admin123`，可用環境變數 `ADMIN_PASSWORD` 覆蓋）
- 提供場地/用途管理頁（新增/編輯/刪除）：`/options`
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

### 方法 C：Windows 開機自動啟動（設定一次即可）

1. 先在專案目錄中雙擊 `install_autostart.bat`（只要一次）。
2. 之後每次開機會自動在背景啟動，不用再手動點 `start_web.bat`。
3. 若要取消自動啟動，雙擊 `uninstall_autostart.bat`。

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
