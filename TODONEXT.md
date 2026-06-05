# Savestock — 後續待辦事項 (TODONEXT)

> 最後更新：2026-06-05（第三次）
> 目前進度：Phase 1（ETL）✅ Phase 2（API）✅ Phase 3（Flutter）進行中

---

## 當前狀態快照

| 層級 | 狀態 | 說明 |
|------|------|------|
| ETL (`etl/fetch_data.py`) | ✅ 完成 | 14 檔預設股票，產業別警示閾值，ETL 寫入 Is_Default=1 |
| 資料庫 (`savestock.db`) | ✅ 完成 | Stock_Master 新增 Is_Default 欄位，14 預設=1 / 自選=0 |
| API (`backend/`) | ✅ 完成 | 9 支端點，含 lookup、watchlist refresh、TWSE 中文名稱查詢 |
| Flutter 首頁 | ✅ 完成 | 14 檔、產業篩選、雙欄 Grid（平板）、警示標記 |
| Flutter 導覽框架 | ✅ 完成 | BottomNavigationBar：預設清單 / 我的股票 |
| Flutter 我的股票 | ✅ 完成 | 開啟時即時從網路更新、左滑刪除 |
| Flutter 查詢股票 | ✅ 完成 | 純搜尋介面、輸入代號即時查詢、加入我的股票 |
| Flutter 模糊搜尋 | ✅ 完成 | debounce 300ms、候選清單、上市+ETF 限定（1362檔）|

---

## ✅ 已完成驗收（2026-06-05）

- [x] 0050 中文名稱、Chip 截斷、台積電中文搜尋、Unknown 標籤隱藏
- [x] 模糊搜尋：debounce + 候選清單，上市+ETF 限定，上櫃不顯示

---

## 🟠 P2 — Flutter 股票詳情頁（下一個大功能）

**檔案位置**：新增 `frontend/lib/screens/stock_detail_screen.dart`

- [ ] 點擊首頁或我的股票的卡片 → 進入個股詳情頁
- [ ] 顯示內容：
  - 股票名稱、代號、產業
  - 估算殖利率（大字顯示）
  - 近2年平均股利 / 最新收盤價
  - 近30日價格走勢圖（折線圖）
  - 今日警示說明（如有）
- [ ] 折線圖套件：在 `pubspec.yaml` 加入 `fl_chart: ^0.68.0`
- [ ] 呼叫 API：`GET /stocks/{stock_id}/prices?days=30`
- [ ] 在 `StockCard.onTap` 接上 Navigator.push

---

## 🟠 P3 — 體驗優化

- [ ] **My Stocks 排序**：依估算殖利率降序（目前 API 已支援，確認 Flutter 顯示順序）
- [ ] **首頁下拉更新**：加入 `RefreshIndicator` 包覆 ListView，下拉重新呼叫 API
- [ ] **自選股上限提示**：超過 3 檔時顯示友善說明，引導升級（目前只顯示錯誤訊息）
- [ ] **已在我的股票的標記**：查詢股票頁若該股票已加入，按鈕改為「已追蹤」並 disable

---

## 🟡 P4 — 後端補強

- [ ] **ETL 排程自動化**：目前需手動執行，需設定 Windows 工作排程器於每日 14:30 收盤後自動執行

  ```powershell
  schtasks /create /tn "SavestockETL" /tr "c:\Savestock\.venv\Scripts\python.exe c:\Savestock\etl\fetch_data.py" /sc daily /st 14:30
  ```

- [ ] **TWSE 名稱快取重整**：目前每次重啟 API 才重載 TWSE 清單，可加 24 小時 TTL
- [ ] **Stock_Master.Default_Drop_Threshold**：ETL 未寫入此欄位，可補充

---

## 🟡 P5 — 生產環境準備（後期）

- [ ] CORS `allow_origins=["*"]` 改為正式網域
- [ ] SQLite → PostgreSQL（`.env` 的 `DATABASE_URL` 改連線字串即可）
- [ ] API 部署（Railway / Render / AWS）
- [ ] Flutter 打包：Android APK / iOS IPA

---

## 啟動指令速查

```powershell
# 1. 啟動 API（每次開工都需要）
Start-Process -FilePath "c:\Savestock\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","main:app","--port","8000" -WorkingDirectory "c:\Savestock\backend" -WindowStyle Normal

# 2. 確認 API 正常
Invoke-RestMethod http://localhost:8000/health

# 3. 執行 ETL（手動更新股票資料）
cd c:\Savestock; .venv\Scripts\python.exe etl\fetch_data.py

# 4. 啟動 Flutter
cd c:\Savestock\frontend; flutter run -d chrome
```

---

## 關鍵檔案索引

| 檔案 | 說明 |
| --- | --- |
| `etl/fetch_data.py` | ETL 主程式，TARGET_STOCKS 定義預設 14 檔，寫入 Is_Default=1 |
| `backend/main.py` | FastAPI 入口 |
| `backend/database.py` | SQLAlchemy engine + get_db() |
| `backend/routers/stocks.py` | 股票端點 + _fetch_and_upsert + TWSE 名稱快取 |
| `backend/routers/users.py` | 用戶端點 + watchlist refresh（即時 yfinance 更新） |
| `frontend/lib/main.dart` | Flutter 入口，允許四向旋轉 |
| `frontend/lib/screens/app_shell.dart` | BottomNavigationBar 框架 |
| `frontend/lib/screens/home_screen.dart` | 首頁：14 檔、產業篩選 Chip、響應式佈局 |
| `frontend/lib/screens/my_stocks_screen.dart` | 我的股票：即時更新、左滑刪除 |
| `frontend/lib/screens/add_stock_screen.dart` | 查詢股票：輸入代號即時查詢並加入 |
| `frontend/lib/widgets/stock_card.dart` | 股票卡片（首頁與我的股票共用） |
| `frontend/lib/widgets/sector_badge.dart` | 產業標籤（Unknown 自動隱藏） |
| `frontend/lib/services/api_service.dart` | 所有 API 呼叫層 |
| `frontend/lib/services/user_service.dart` | UUID 生成 + user_id 本地儲存 |
| `database/init_sqlite.sql` | DB Schema（含 Is_Default 欄位） |

---

## 已知設計決策紀錄

| 決策 | 原因 |
| --- | --- |
| 預設股 `Is_Default=1`，自選股 `Is_Default=0` | 避免 lookup 新增的股票混入預設清單 |
| 自選股中文名稱從 TWSE openapi 抓取 | yfinance 台股名稱為英文，TWSE 才有正確中文名 |
| 我的股票開啟時呼叫 `/watchlist/refresh` | 確保顯示即時資料，非 DB 快照 |
| `engine.begin()` 作為 get_db context | SQLite 自動 commit/rollback，無需手動管理 transaction |
| Plan_Configs: Free=3, Premium=10（自選股上限） | 與 14 檔預設不重疊計算，邏輯更清晰 |
