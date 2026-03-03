# 場地預定管理程式

這是一個使用 Python 撰寫的場地預定系統，提供：

- CLI 終端機互動管理（新增 / 查詢 / 取消）
- Web 表單輸入（瀏覽器新增預約）
- 月曆視圖顯示每月預約資訊
- 同場地時段衝突檢查

## 1) CLI 版本

```bash
python booking_manager.py
```

## 2) Web 版本（含月曆）

```bash
python web_booking_app.py
```

啟動後開啟 `http://localhost:8000`。

## 時間格式

請使用：`YYYY-MM-DD HH:MM`，例如 `2026-04-01 09:30`。

## 測試

```bash
python -m unittest discover -s tests
```
