# Savestock — 後續待辦事項 (TODONEXT)

> 最後更新：2026-06-05（收工）
> 目前進度：Phase 1（ETL）✅ Phase 2（API）✅ Phase 3（Flutter）✅ 主功能完成

---

## 當前狀態快照

| 層級 | 狀態 | 說明 |
|------|------|------|
| ETL (`etl/fetch_data.py`) | ✅ 完成 | 14 檔預設，產業別警示，寫 1 年歷史價格，Is_Default=1 |
| 資料庫 (`savestock.db`) | ✅ 完成 | 每支預設股約 245 筆日價格（2025-06 起） |
| API (`backend/`) | ✅ 完成 | 11 支端點：含 search、lookup（自動判斷 .TW/.TWO）、prices |
| Flutter 首頁 | ✅ 完成 | 14 檔、產業篩選 Chip、響應式佈局、警示標記 |
| Flutter 導覽框架 | ✅ 完成 | BottomNavigationBar：預設清單 / 我的股票 |
| Flutter 我的股票 | ✅ 完成 | 開啟時即時更新、左滑刪除 |
| Flutter 查詢股票 | ✅ 完成 | debounce 300ms + 候選清單（上市+ETF 1362 檔）+ 無結果直接查詢 |
| Flutter 股票詳情頁 | ✅ 完成 | 殖利率大字、30日/半年/1年折線圖、警示卡片 |

---

## ✅ 今日完成項目（2026-06-05）

- [x] **模糊搜尋**：debounce + STOCK_DAY_ALL 候選清單（上市+ETF），上櫃不顯示
- [x] **無結果直接查詢**：搜尋無候選時顯示「直接查詢此代號」按鈕
- [x] **債券 ETF 錯誤訊息**：`00xxB` 代號 Yahoo Finance 無資料時顯示明確說明
- [x] **股票詳情頁**（P2）：殖利率大字、數據列、警示卡片、fl_chart 折線圖
- [x] **30日/半年/1年 時段切換**：折線圖依選擇重新載入
- [x] **價格歷史補全**：ETL + lookup 改為寫 1 年歷史（`period="1y"`），預設股已補至約 245 筆

---

## 🟠 P3 — 體驗優化（下次開工）

- [ ] **My Stocks 排序**：依估算殖利率降序（API 已支援，確認 Flutter 顯示順序）
- [ ] **首頁下拉更新**：加入 `RefreshIndicator`，下拉重新呼叫 API
- [ ] **自選股上限提示**：超過 3 檔時顯示友善說明引導升級（目前直接顯示後端錯誤）
- [ ] **已追蹤標記**：查詢頁若股票已加入，按鈕改為「已追蹤」並 disable
- [ ] **預設股中文名稱**：DB 中 2330 等預設股名稱仍為英文（ETL 當初存的）；可加一次性 TWSE 對照刷新

---

## 🟡 P4 — 後端補強

- [ ] **ETL 排程自動化**：目前需手動執行，設定 Windows 工作排程器於每日 14:30 自動執行

  ```powershell
  schtasks /create /tn "SavestockETL" /tr "c:\Savestock\.venv\Scripts\python.exe c:\Savestock\etl\fetch_data.py" /sc daily /st 14:30
  ```

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
Start-Process -FilePath "c:\Savestock\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","main:app","--port","8000" -WorkingDirectory "c:\Savestock\backend" -WindowStyle Hidden

# 2. 確認 API 正常
Invoke-RestMethod http://localhost:8000/health

# 3. 執行 ETL（手動更新股票資料）
Set-Location C:\Savestock; .venv\Scripts\python.exe etl\fetch_data.py

# 4. 啟動 Flutter（Claude 會幫你開，告知「幫我開 Flutter」即可）
Set-Location C:\Savestock\frontend; flutter run -d chrome --web-port 5000
```

---

## 關鍵檔案索引

| 檔案 | 說明 |
| --- | --- |
| `etl/fetch_data.py` | ETL 主程式，抓 1 年歷史寫入 Daily_Prices，Is_Default=1 |
| `backend/main.py` | FastAPI 入口 |
| `backend/database.py` | SQLAlchemy engine + get_db() |
| `backend/routers/stocks.py` | 全證券搜尋快取（24h TTL）+ search/lookup/prices 端點 |
| `backend/routers/users.py` | 用戶端點 + watchlist refresh（即時 yfinance 更新） |
| `frontend/lib/main.dart` | Flutter 入口 |
| `frontend/lib/screens/app_shell.dart` | BottomNavigationBar 框架 |
| `frontend/lib/screens/home_screen.dart` | 首頁：14 檔、產業篩選 Chip、響應式佈局 |
| `frontend/lib/screens/my_stocks_screen.dart` | 我的股票：即時更新、左滑刪除 |
| `frontend/lib/screens/add_stock_screen.dart` | 查詢股票：模糊搜尋 + 候選清單 + 無結果直接查詢 |
| `frontend/lib/screens/stock_detail_screen.dart` | 股票詳情：殖利率大字 + 30日/半年/1年折線圖 + 警示卡片 |
| `frontend/lib/widgets/stock_card.dart` | 股票卡片（首頁與我的股票共用，onTap → 詳情頁）|
| `frontend/lib/widgets/sector_badge.dart` | 產業標籤（Unknown 自動隱藏）|
| `frontend/lib/services/api_service.dart` | 所有 API 呼叫層（含 PricePoint、SearchCandidate 模型）|
| `frontend/lib/services/user_service.dart` | UUID 生成 + user_id 本地儲存 |
| `database/init_sqlite.sql` | DB Schema |

---

## 已知設計決策紀錄

| 決策 | 原因 |
| --- | --- |
| 預設股 `Is_Default=1`，自選股 `Is_Default=0` | 避免 lookup 新增的股票混入預設清單 |
| 自選股中文名稱從 TWSE openapi 抓取 | yfinance 台股名稱為英文，TWSE 才有正確中文名 |
| 我的股票開啟時呼叫 `/watchlist/refresh` | 確保顯示即時資料，非 DB 快照（同步補 1 年歷史）|
| 搜尋快取來源：STOCK_DAY_ALL（上市）| 涵蓋 ETF（如 0050），t187ap03_L 無 ETF；上櫃不在本 App 範圍 |
| 債券 ETF（00xxB）不支援 | Yahoo Finance 無資料，顯示明確說明而非通用錯誤 |
| ETL + lookup 寫 1 年歷史 | 股票詳情頁折線圖需要足夠資料（245 筆 ≈ 1 年交易日）|
| `engine.begin()` 作為 get_db context | SQLite 自動 commit/rollback，無需手動管理 transaction |
| Plan_Configs: Free=3, Premium=10（自選股上限）| 與 14 檔預設不重疊計算，邏輯更清晰 |
