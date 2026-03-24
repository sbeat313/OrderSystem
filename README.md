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
- 額外收入登記頁：`/extra-income`
- 穿線項目設定頁：`/string-items`

## 主要頁面與用途

| 路徑 | 用途 | 權限 |
|---|---|---|
| `/` | 主排程頁，檢視每日/每週/雙週場地預約 | 一般 / 管理員 |
| `/options` | 系統設定（管理員密碼、登入時效） | 管理員 |
| `/purposes` | 用途與價格設定 | 管理員 |
| `/reports` | 預約費用與額外收入報表、匯出 Excel | 管理員 |
| `/extra-income` | 額外收入登記與查詢（含球拍穿線欄位） | 管理員 |
| `/string-items` | 穿線項目與金額維護 | 管理員 |

## API 路由摘要

### 查詢類（GET）

- `GET /api/venues`：取得場地列表
- `GET /api/purposes`：取得用途與價格
- `GET /api/bookings?date=YYYY-MM-DD`：取得指定日期預約

### 新增類（POST）

- `POST /api/admin/login`：管理員登入驗證
- `POST /api/bookings`：新增預約（支援單一 `venue_id` 或多選 `venue_ids`）
- `POST /api/venues`、`POST /api/purposes`：新增場地/用途
- `POST /api/string-items`：新增穿線項目
- `POST /api/extra-incomes`：新增額外收入
- `POST /api/reports/fees`：取得報表資料（含分頁）
- `POST /api/reports/fees/export`：匯出 Excel

### 更新與刪除（PUT / DELETE）

- `PUT/DELETE /api/bookings`：修改 / 取消預約
- `PUT/DELETE /api/venues`：修改 / 刪除場地
- `PUT/DELETE /api/purposes`：修改 / 刪除用途
- `PUT/DELETE /api/string-items`：修改 / 刪除穿線項目
- `PUT/DELETE /api/extra-incomes`：修改 / 刪除額外收入

> 除登入、公開查詢類 API 外，管理操作需帶入 `admin_password`。

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

### 主要資料表

- `venues`：場地主檔
- `purposes`：用途與預設價格
- `bookings`：預約資料（含 `rental_group_id`、`created_at`）
- `string_items`：穿線項目與金額
- `extra_incomes`：額外收入（含球拍/磅數/收款狀態等）
- `settings`：系統設定（管理員密碼、登入時效等）

## 測試

```bash
python -m unittest discover -s tests
```

## 程式碼最佳化重點（2026-03）

- **資料庫 schema 升級流程共用化**：啟動時的欄位補齊改為統一檢查函式，降低重複 SQL 與維護成本。
- **額外收入輸入驗證集中化**：新增/更新額外收入共用同一套驗證邏輯，確保兩條 API 路徑的資料規則一致。
- **可讀性提升**：將重複的輸入清理與型別轉換收斂到單一函式，未來調整規則時只需改一處。
- **報表資料流程共用化**：報表查詢與匯出改用同一份彙整流程，避免兩條路徑計算邏輯分歧。
- **HTTP JSON 解析共用化**：`POST/PUT/DELETE` 採用一致的 JSON 解析與錯誤訊息，減少重複程式碼。
