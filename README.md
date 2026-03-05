# 場地預定管理程式

這是一個以 **Python + SQLite** 實作的場地預約系統，提供：

- Web 介面（預約檢視、管理員模式、場地/用途設定、費用統計）
- CLI 管理模式
- SQLite 本地資料庫持久化（預設 `booking.db`）

## 功能概覽

- 場地由資料庫管理（首次啟動預設建立 1~6 號場）
- 用途由資料庫管理並以下拉選單選擇（單月租、雙月租、臨租、月租球友續租、股東價、連假專案、寒暑假專案、過年專案）
- 管理員 / 一般使用者雙檢視（使用者端資訊遮蔽）
- 每日 / 每週 / 雙週顯示切換
- 管理員檢視密碼保護（預設密碼 `admin123`，可用環境變數 `ADMIN_PASSWORD` 覆蓋）
- 場地/用途管理頁：`/options`
- 費用統計頁：`/reports`

## 執行環境

- 建議 Python 版本：**3.8+**
- 不需額外安裝第三方套件（使用 Python 標準函式庫）

## 快速啟動

### 1) 啟動 Web 介面

```bash
python web_booking_app.py
```

啟動後開啟：`http://localhost:8000`

### 2) 啟動 CLI 模式

```bash
python booking_manager.py
```

## Windows 便捷啟動

- 直接雙擊 `start_web.bat` 啟動 Web。
- 若啟動失敗，視窗會停留並顯示錯誤訊息，不會立刻關閉。

### 開機自動啟動（設定一次）

1. 在專案目錄中雙擊 `install_autostart.bat`。
2. 後續每次開機會自動於背景啟動，不需手動執行 `start_web.bat`。
3. 若要取消，雙擊 `uninstall_autostart.bat`。

## 環境變數

- `ADMIN_PASSWORD`：覆蓋管理員密碼。

範例（macOS / Linux）：

```bash
ADMIN_PASSWORD=your_password python web_booking_app.py
```

範例（Windows PowerShell）：

```powershell
$env:ADMIN_PASSWORD="your_password"
python web_booking_app.py
```

## 資料庫

- 預設資料庫檔案：`booking.db`
- 首次啟動會自動建立資料表與預設場地資料

## 測試

```bash
python -m unittest discover -s tests
```
