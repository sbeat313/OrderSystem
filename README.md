# 場地預定管理程式

這是一個使用 Python 撰寫的簡易 CLI 場地預定系統，支援：

- 新增預約
- 檢查同場地時段衝突
- 查詢全部或指定場地預約
- 取消預約

## 執行方式

```bash
python booking_manager.py
```

時間格式請使用：`YYYY-MM-DD HH:MM`，例如 `2026-04-01 09:30`。

## 測試

```bash
python -m unittest discover -s tests
```
