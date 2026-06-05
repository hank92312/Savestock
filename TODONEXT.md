# Savestock — 後續待辦事項 (TODONEXT)

> 最後更新：2026-06-05（第二次）
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

---

## 🔴 優先待辦 — 待驗收清單

> 2026-06-05：backend 兩項已用 API 實測通過（見下方修復紀錄），前端兩項待目視確認。

- [x] **0050 中文名稱** — lookup `0050` 回傳「元大台灣50」（API 實測通過）
  - 修復：`_fetch_and_upsert` 抓取後 `dropna(["Close","Volume"])`，剔除當日未收盤 NaN 列（原本 `int(NaN)` → 500）
  - 仍需目視：進「查詢股票」輸入 `0050` → 確認畫面顯示中文名
- [ ] **Chip 截斷修正** — 改用 `SingleChildScrollView + Row`，首頁篩選 Chip 應從一開始就正確顯示全名
  - 驗收方式：重新開啟 App，確認「全部 ETF 金融 食品 營建 電信」完整顯示
- [x] **中文名稱搜尋** — lookup `台積電` 找到 2330（API 實測通過）
  - 修復：TWSE openapi 端點 `t51sb01`（已失效，回 HTML）→ 換成 `t187ap03_L`（本國上市公司基本資料）
  - 注意：第一次中文搜尋會多等 1–2 秒（TWSE 快取載入）
  - 仍需目視：查詢股票輸入「台積電」→ 確認能找到 2330 並顯示資料
- [ ] **Unknown 標籤隱藏** — 自選股（sector=Unknown）不顯示產業標籤
  - 驗收方式：我的股票頁確認無 Unknown 灰色標籤

### ⚠️ 本次發現、暫未處理（範圍外）

- **預設股名稱仍為英文**：2330 等預設股 lookup 會保留 DB 既有英文名（ETL 當初存的）。可日後用 TWSE 統一刷成中文名。

---

## ✅ 任意台股模糊搜尋（已完成，待前端目視驗收）

**後端 API 實測通過（2026-06-05）：**
- `GET /stocks/search?q=005` → 0050.TW 元大台灣50、0051…（代號前綴，排序正確）
- `GET /stocks/search?q=台積` → 2330.TW 台積電（中文模糊）
- `GET /stocks/search?q=中光` → 5371.TWO 中光電（上櫃 `.TWO` 正確）
- `GET /stocks/search?q=6147` → 6147.TWO 頎邦（上櫃代號）
- `lookup` 已改用快取決定 `.TW`/`.TWO`，移除舊有硬補 `.TW`

**資料來源（快取 24h TTL）：**
- 上市＋ETF：`STOCK_DAY_ALL`（1362 檔）；非交易日退回 `t187ap03_L`
- 上櫃：TPEx `tpex_mainboard_daily_close_quotes`（`verify=False`，此環境 SSL 憑證問題）

**前端已改寫（待目視驗收）：**
- 輸入 debounce 300ms → `searchStocks()` → `_CandidateList` ListView
- 點選候選 → `lookupStock()` → 顯示 StockCard + 加入按鈕
- 搜尋列移除「查詢」按鈕，改為 suffix spinner 顯示載入狀態

**驗收條件：**
- [ ] 輸入 `005` → 即時顯示「0050 元大台灣50」等候選清單
- [ ] 輸入 `台積` → 出現「2330 台積電」
- [ ] 輸入 `中光` → 出現「5371 中光電」（上櫃）
- [ ] 點選任一候選 → 顯示 StockCard + 可加入我的股票

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
