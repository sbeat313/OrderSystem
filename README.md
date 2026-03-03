# 場地預定管理程式

此版本提供：

- SQLite 本地資料庫持久化（預設 `booking.db`）
- 場地由資料庫管理（預設建立 1~6 號場）
- 管理員 Web 檢視（顯示預約人與用途）
- 一般使用者 Web 檢視（資訊遮蔽）
- CLI 管理模式

## 啟動 Web

```bash
python web_booking_app.py
```

開啟 `http://localhost:8000`。

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
