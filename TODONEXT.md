# Savestock — 後續待辦事項 (TODONEXT)

> 最後更新：2026-06-10（MVP 完整上線 + UI 美化 + ETL bug 修復）
> 目前進度：Phase 1–3 ✅；P3 體驗優化 ✅；P4 後端補強 ✅；P5 部署 ✅；UI 美化 ✅；ETL bug 修復 ✅（聯邦銀近1年股利、永豐金股利圖）。**ETL 自動排程待設定**。

---

## 🚀 雲端部署現況與交接（2026-06-09）— 後續 AI 必讀

> 平台已定案 **Google Cloud Platform**（$300 試用折抵金，70 天試用期）。詳細架構見 `APP.md` 第 7 節。

### 已部署資源（GCP 專案 `savestock-app`，區域 `asia-east1`）

| 資源 | 服務 | 識別 / 設定 | 狀態 |
| --- | --- | --- | --- |
| 後端 API | Cloud Run | `savestock-api`；512Mi；min=0/max=2；允許未驗證 | ✅ 運行中 |
| 資料庫 | Neon PostgreSQL（免費方案） | `ep-floral-credit-aojbdxlt.c-2.ap-southeast-1.aws.neon.tech`；0.5GB；AWS Singapore | ✅ 運行中（25 檔資料已填入） |
| 容器倉庫 | Artifact Registry | `savestock-repo`（Docker） | ✅ |
| 容器建置 | Cloud Build | 遠端建置（本機無 Docker） | ✅ |

- **正式 API 網址**：`https://savestock-api-62102931839.asia-east1.run.app`（`/health`、`/stocks` 已驗證 200）
- **DB 連線**：Cloud Run 透過 `DATABASE_URL` 環境變數連 Neon（標準 TCP + SSL）；`DATABASE_URL` 透過 **GCP Secret Manager** 注入（secret `savestock-db-url`，version 4 為 active latest）。
- **Neon 密碼**：未寫入版控；存於 Secret Manager `savestock-db-url`（version 4）及本機 `.env`（已 gitignore）。Cloud Run 以 `--set-secrets="DATABASE_URL=savestock-db-url:latest"` 取得。
- **⚠️ Cloud SQL 已於 2026-06-11 刪除**，不再計費。
- **生產 schema**：`database/init_postgres.sql`（已匯入雲端）

### 已完成的 SQLite→PostgreSQL 改寫（commit `7615669`）
- `database/init_postgres.sql`（SERIAL/BOOLEAN/ON CONFLICT）
- `backend/database.py`：依 `DATABASE_URL` 前綴自動切換
- `backend/routers/stocks.py`：`Is_Default = TRUE`/`FALSE`（PostgreSQL 不接受 `boolean = integer`）
- `backend/requirements.txt`：補 `yfinance`、`requests`
- `backend/Dockerfile` + `.dockerignore`

### ✅ P5 部署（2026-06-10 全部完成）

1. ~~**雲端 DB 資料填充**~~ ✅ 14 檔預設股資料已填入，手機驗證回傳正常
2. ~~**Flutter App 改連雲端 API**~~ ✅ `api_service.dart`、`user_service.dart` 已改為 `https://savestock-api-62102931839.asia-east1.run.app`
3. ~~**CORS 收斂**~~ ✅ `allow_origins=["https://savestock.netlify.app"]`
4. ~~**Secret Manager**~~ ✅ `DATABASE_URL` 存入 `savestock-db-url`，Cloud Run 以 `--set-secrets` 注入
5. ~~**Flutter Web 打包部署**~~ ✅ 部署至 Netlify：`https://savestock.netlify.app`

### 🔴 剩餘待辦（按優先序）

1. **ETL 自動排程（Cloud Scheduler）**：每日盤後自動更新股票資料。Cloud Scheduler 已啟用，待建立工作（詳見下方指令）。
   ```bash
   gcloud scheduler jobs create http savestock-etl-daily \
     --location=asia-east1 \
     --schedule="0 15 * * 1-5" \
     --uri="https://savestock-api-62102931839.asia-east1.run.app/stocks/refresh" \
     --http-method=POST \
     --time-zone="Asia/Taipei"
   ```
   > ✅ `/stocks/refresh` 會對每檔預設股呼叫 `_fetch_and_upsert`，包含 Dividends、Listing_Months、股價、殖利率全部欄位，與 ETL 口徑一致。使用者在 App 下拉更新即等同全量更新，不需要另跑 ETL。

### 💰 成本提醒
- 試用期內全部由 $300 折抵金支付。
- 試用後預估 **~$10–15/月**（Cloud SQL `db-f1-micro` ~$7–10 為最大固定成本）。
- **Cloud SQL 是持續計費資源**：長時間不開發可先 `gcloud sql instances patch savestock-db --activation-policy=NEVER` 停用省折抵金，要用時改 `ALWAYS`。
- 試用期結束前評估是否改採 Local-First（最小雲端 DB 只存 Users/Subscriptions + 裝置端 sqflite）。

### 🔑 常用部署指令
```powershell
# ── 前端 Flutter Web → Netlify ──────────────────────────────
# 1. 打包
Set-Location C:\Savestock\frontend; flutter build web --release
# 2. 部署（Netlify CLI，site ID 固定）
Set-Location C:\Savestock\frontend\build\web
netlify deploy --prod --dir=. --site=ebec3bc6-8ea5-4131-98b0-e08c54aaaac8

# ── 後端 FastAPI → Cloud Run ────────────────────────────────
# 重新 build + 部署（改後端後）
gcloud builds submit "C:\Savestock\backend" --tag=asia-east1-docker.pkg.dev/savestock-app/savestock-repo/savestock-api:latest --project=savestock-app
# deploy 指令含密碼，需在 Google Cloud SDK Shell 手動執行（見 APP.md 第 7 節）

# 看 Cloud Run 錯誤 log
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=savestock-api AND severity>=ERROR" --project=savestock-app --limit=20 --format="value(textPayload)"

# ── Neon 資料同步（本機 ETL → 雲端，不需 Proxy）────────────
# 方法 1：直接設定環境變數（密碼存於 Secret Manager / .env）
# $env:DATABASE_URL = "postgresql+psycopg2://neondb_owner:【密碼】@ep-floral-credit-aojbdxlt.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
# Set-Location C:\Savestock; .venv\Scripts\python.exe etl\fetch_data.py
# 方法 2：修改 .env（把 SQLite 那行加 # 改成 Neon 那行），再直接跑 ETL
# 密碼查詢：gcloud secrets versions access latest --secret="savestock-db-url" --project=savestock-app
```

---

## ⚠️ 技術債：ETL 與後端股利計算邏輯並行維護

> **狀態：已知，暫不重構，下次動到股利計算時必讀**

ETL（`etl/fetch_data.py`）與後端（`backend/routers/stocks.py`）各自獨立實作了股利計算邏輯，目前已人工對齊，但未來若任一邊修改，**兩邊都必須同步更新**。

| 邏輯 | ETL | 後端 |
|------|-----|------|
| 近1年股利（`dividend_1y`） | `fetch_stock_data()` 內 for 迴圈 | `_dividend_1y()` |
| 2年/5年均股利 | `_calc_avg()` | `_total_div_series()` |
| Dividends 表寫入 | `save_to_db()` 第 3 段 | `_upsert_dividends()` |

**根因（已發生過的事故）**：
- 2026-06-10：ETL `save_to_db` 從未寫 Dividends 表 → 新增 11 檔無股利圖（已修）
- 2026-06-10：ETL `dividend_1y` 只算現金，漏掉 `Stock Splits` 配股 → 聯邦銀 1.05 顯示 0.35（已修）

**修復方式**：對齊後端口徑後，呼叫 `POST /stocks/refresh` 一次修正 Cloud SQL（不需 Proxy）。

---

## ✅ 今日完成項目（2026-06-10 第二次）

- [x] **ETL bug 修復（股利口徑）**：`etl/fetch_data.py` 兩處邏輯對齊後端：
  - `dividend_1y` 納入配股（`(ratio-1)*10`）→ 聯邦銀 0.35 → 1.05 修正
  - `save_to_db` 補寫 Dividends 表 → 永豐金等 11 新增股股利圖有資料
- [x] **Cloud SQL 修復驗證**：`POST /stocks/refresh` 重跑後驗證 2838=1.05 ✅、抽查 2884/00713/9917/2633/5880 股利列數正常 ✅
- [x] **預設股 14 → 25 檔**：新增 11 檔；以台灣高鐵（2633）替換光寶科（2301）；已同步 Cloud SQL
- [x] **股利直條圖加「近5年」選項**：不足5年顯示提示文字
- [x] **onboarding 加第 4 頁（搜尋功能說明）**（4頁→5頁）
- [x] **首頁問號圖示改 TextButton.icon「使用教學」**：手機上直觀可見
- [x] **UI 美化**：卡片陰影（`AppTheme.cardDecoration`）、產業標籤改膠囊型、殖利率高亮膠囊（依高低分色）
- [x] **Netlify 部署修復**：從手動上傳改用 Netlify CLI（`flutter_bootstrap.js 404` 問題根治）

---

## ✅ 今日完成項目（2026-06-10）

- [x] **Flutter App baseUrl 切換雲端**：`api_service.dart`、`user_service.dart` 全改為 `https://savestock-api-62102931839.asia-east1.run.app`
- [x] **CORS 收斂**：`backend/main.py` `allow_origins=["https://savestock.netlify.app"]`
- [x] **Secret Manager**：`DATABASE_URL` 存入 GCP Secret Manager（`savestock-db-url` version 2 active）；`database.py` 加 `.strip()` 防換行；Cloud Run 以 `--set-secrets` 注入，不再明文寫入環境變數
- [x] **tools/ gitignore**：避免本機工具二進位檔進版控
- [x] **PostgreSQL 相容性修正**（`routers/users.py`）：
  - `RETURNING User_ID` + `result.fetchone()[0]`（取代 SQLite 的 `lastrowid`）
  - 所有 row 存取改 `r._mapping.get("欄位名")`（PostgreSQL text() 欄位名折小寫）
  - `Is_Default = FALSE` 取代整數 `0`（PostgreSQL boolean 嚴格型別）
- [x] **Flutter Web 部署 Netlify**：打包 `frontend/build/web`，部署至 `https://savestock.netlify.app`
- [x] **手機端對端驗證**：首頁 14 檔、詳情頁圖表、搜尋、自選加入/移除全部正常
- [x] **架構決策**：維持現有 Cloud SQL MVP 試運行（保留跨裝置同步能力）；localStorage 方案保留為未來選項

---

## ✅ 今日完成項目（2026-06-09）

- [x] **股利圖改堆疊直條圖**：`_DividendChart` 由 `LineChart` → `BarChart`，現金（淺藍 `#4FC3F7`）＋股票（深紫 `#7E57C2`）堆疊；加雙色圖例；tooltip 顯示「現金 X ＋股票 Y ＝合計 Z」；標題改「歷年股利分配」；前端單檔修改，後端不動；視覺驗證通過（2883 三筆分色正確）。
- [x] **全功能驗收通過**：教學導覽（4頁/略過/❓重看）、首頁搜尋、雙殖利率（2838/00961）、圖表 tooltip、免費上限 5 — 全項確認正常。

---

## ✅ 今日完成項目（2026-06-08）

- [x] **詳情頁加入「加入我的股票」鈕**：AppBar 智慧書籤鈕（未追蹤→加入圖示、已追蹤→實心書籤、載入中→spinner）
- [x] **跨頁同步修正**：新增 `WatchlistNotifier` 單例（ChangeNotifier）；任何地方加股後 `markDirty()`，My Stocks 監聽並輕量 `_loadList()` 重抓，免按網頁重新整理才出現
- [x] **本機 user 升 Premium（上限 20）**：DB 全 user 改 Premium_Tier_1=20
- [x] **股票名稱中文修正**：`_resolve_chinese_name` 優先用 TWSE 批次快取（可靠）再退即時 mis API；既有英文名下次 refresh 自動升級
- [x] **價格顯示到小數第 2 位**：卡片/詳情 `toStringAsFixed(1)`→`(2)`
- [x] **近一年殖利率為主基準**：卡片/清單主顯示改 `Dividend_1Y`/`yield1y`；詳情頁並列近1年＋近2年平均；不滿1年顯示「近X月股利」並標註
- [x] **股利折線圖**：價格圖下方新增股利圖（半年/1年/2年切換）— *下次將改為直條圖（見上）*
- [x] **配股（股票股利）納入殖利率**：yfinance `Stock Splits` 欄＝配股，面額還原 (ratio−1)×10；`_total_div_series()` 合併現金＋配股；`Dividends` 表改 `Cash_Dividend`/`Stock_Dividend` 分欄；端點回傳 cash/stock/total；已重算全部 26 檔（2838 聯邦銀殖利率 ~1.5%→5.06%）
  - 標註：詳情頁 `_YieldHeader` 加方法說明（配股按面額還原）
  - 已知限制：yfinance 偶把單次配股拆成多列（2838 2024-07），略灌水**近2年平均**；近1年（主指標）正確。已記入 APP.md。
- [x] **start.bat / stop.bat / .gitignore**：一鍵啟動/停止；DB 已 gitignore

> ⚠️ 部署提醒：股利資料只在本地 `savestock.db`（gitignore）。新環境需跑 ETL 或對各股呼叫 refresh 端點回填 `Dividends` 表並重算彙總值。

---

## ⭐ 下次開工優先

### 1. 待決小項
- [ ] **My Stocks 分頁自動刷新**：目前用 `IndexedStack` 保活，從首頁搜尋加入後切到「我的股票」需手動按 🔄 才更新。是否要做「切到該分頁時自動刷新」？（已向使用者提出，待回覆）

### 3. 雙殖利率 ✅ 已實作（2026-06-06）
詳情頁並列「近一年殖利率」與「2年平均殖利率」；排序/警示仍用保守 2 年平均（baseline）。
- [x] `Stock_Master.Dividend_1Y`（近12月現金股利）+ ETL/後端寫入、回應加 `dividend_1y`/`yield_1y`
- [x] 詳情頁 `_YieldHeader` 雙欄，依 `listingMonths` 切標籤：≥2年=2年平均；1–2年=上市以來年化；<1年=僅年化(涵蓋X月)+紅字；無配息=「—」
- 實測對照亮點：聯邦銀 2年 7.86% vs 近一年 1.62%（揭露被灌水的高息陷阱）

### 3b. 首頁即時刷新 ✅ 已修（2026-06-06）
- 首頁「更新」按鈕原本只重讀 DB 快照、盤中價不動 → 新增 `POST /stocks/refresh` 即時抓 yfinance；按鈕與下拉改走即時（開啟仍快速讀 DB）。
- 順帶：`_fetch_and_upsert` 改用各股儲存的產業跌幅閾值（取代寫死 3%），即時刷新警示與 ETL 一致。

### 3c. 首頁 AppBar UX ✅ 已修（2026-06-06）
- 「更新」按鈕改為圖示+文字（手機無 hover tooltip 也看得懂）。
- 警示徽章改可點（+下拉箭頭），點擊以底部彈窗列出所有警示股票（重用 StockCard，可點進詳情）。

### 4. 主要方向
- [ ] **P5 部署**：先定**後端託管平台**（比較表見下方 P5 區），再展開部署工作。

---

## 當前狀態快照

| 層級 | 狀態 | 說明 |
|------|------|------|
| ETL (`etl/fetch_data.py`) | ✅ 完成 | 14 檔預設，產業別警示，寫 1 年歷史價格，Is_Default=1 |
| 資料庫 (`savestock.db`) | ✅ 完成 | 每支預設股約 245 筆日價格（2025-06 起） |
| API (`backend/`) | ✅ 完成 | 12 支端點：search、lookup（自動判斷 .TW/.TWO）、prices、自選 CRUD/refresh（皆殖利率排序）|
| Flutter 首頁 | ✅ 完成 | 14 檔、產業篩選、響應式、警示、下拉刷新、🔍搜尋、❓教學 |
| Flutter 教學導覽 | ✅ 完成 | 首次自動顯示 + 可重看（殖利率/用法/警示/免責）|
| Flutter 導覽框架 | ✅ 完成 | BottomNavigationBar：預設清單 / 我的股票 |
| Flutter 我的股票 | ✅ 完成 | 開啟即時更新、刪除鈕 + 左滑刪除、殖利率排序 |
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

## ✅ 今日完成項目（2026-06-06）

- [x] **直接查詢 view 提交**：補提交先前未 commit 的「無候選時直接查詢」改動
- [x] **首頁下拉更新**：`RefreshIndicator` + `AlwaysScrollableScrollPhysics`（含空清單/分產業狀態皆可下拉）
- [x] **已追蹤標記**：查詢頁 initState 載入自選清單；查到已追蹤的股票時，按鈕改「已追蹤」並 disable + banner
- [x] **自選股上限提示**：`addToWatchlist` 收到 403 時改回傳友善訊息並引導升級（沿用後端實際檔數）
- [x] **滑鼠拖曳捲動**：自訂 `ScrollBehavior` 加入 mouse，修正 web 下拉刷新失效
- [x] **圖表 tooltip 日期**：折線圖滑過時顯示 `YYYY/MM/DD` + 股價
- [x] **新上市股股利年化**：新增 `Stock_Master.Listing_Months`；上市 <24 月改用「上市迄今全部股利 ÷ 上市年數」年化，詳情頁標籤改「上市迄今平均股利」並註明資料涵蓋約 X 個月（ETL + 後端 + 前端全串通，已重跑 ETL）
- [x] **我的股票刪除鈕**：每列加永遠可見的刪除按鈕（左滑為觸控手勢，web 滑鼠難觸發）
- [x] **My Stocks 排序**：`/watchlist/refresh` 回傳前依估算殖利率降序排序（與 GET /watchlist 一致）
- [x] **預設股中文名稱**：經查 DB 已是正確中文（元大高股息、中華電信…），此項早已解決（過時項目，移除）
- [x] **App 內教學導覽（onboarding）**：首次自動顯示 + 首頁 ❓ 可重看（4 頁：殖利率→用法→警示→免責；`shared_preferences` 記旗標）
- [x] **免費方案自選上限統一為 5**：schema 兩份種子 + 後端無授權 fallback + 前端文案 + 現有 DB 全部改 5
- [x] **首頁放大鏡搜尋**：AppBar 加 🔍 入口，重用 `AddStockScreen`（搜尋上市+ETF → 一鍵加入我的股票）
- [x] **Default_Drop_Threshold 寫入**：ETL 依產業別寫入小數閾值
- [x] **ETL 排程**：決定延後至 P5 部署一起做

## 🟠 P3 — 體驗優化（剩餘）

- 目前 P3 已清空 ✅

---

## 🟡 P4 — 後端補強

- [x] **Stock_Master.Default_Drop_Threshold**：ETL 已依產業別寫入小數閾值（營建0.06/ETF0.04/金融0.025/食品0.03/電信0.025）
- [~] **ETL 排程自動化**：**決定延後到 P5 部署一起做**（本機 Windows 排程只在本電腦開機時有效、價值有限）。部署後改在伺服器（Linux cron / 雲端排程）設定，指向正式 DB。
  - 本機暫時方案（如需展示時手動啟用）：
    ```powershell
    schtasks /create /tn "SavestockETL" /tr "c:\Savestock\.venv\Scripts\python.exe c:\Savestock\etl\fetch_data.py" /sc daily /st 14:30
    ```

---

## 🟡 P5 — 生產環境準備（後期）

### 已定決策（2026-06-06 討論）
- **發佈形式**：**Web 優先**先上線驗證，之後再評估 Android/iOS
- **帳號系統**：先**維持訪客 UUID**（缺點：換機/重裝會遺失自選股、無法跨裝置同步；上線後可再升級登入）
- **介紹/教學**：做 **App 內教學導覽（onboarding）**，不另架行銷網頁

### ✅ App 內教學導覽（onboarding）— 已完成
- [x] 首次開啟自動顯示 + 首頁 ❓ 可隨時再看（4 頁：殖利率→用法→警示→免責；`shared_preferences` 記旗標）
- 內容大綱：
  1. 什麼是存股／**殖利率**（= 年配息 ÷ 股價，白話解釋）
  2. App 怎麼用（預設清單看達標股 → 加自選 → 詳情折線圖 → 警示）
  3. **警示**在防什麼（暴跌／爆量＝避開高殖利率陷阱）
  4. ⚠️ **免責聲明**（非投資建議）— 金融類 App 必備

### 後端託管方案比較（✅ 已定案：GCP — 見本文件最上方「雲端部署現況」；下表保留作歷史參考）

| 平台 | 月成本 | 管理／維運方式 | ETL 排程 | 優點 | 缺點 / 注意 |
|------|--------|----------------|----------|------|-------------|
| **Render** | 免費層(會休眠、Postgres 90 天到期)；穩定約 **$14**（Web $7 + DB $7） | 連 GitHub 自動部署，平台代管 OS/憑證/Postgres | ✅ 內建 Cron Jobs | 一站式最省心、含託管 Postgres、HTTPS 自動 | 免費層冷啟動慢；穩定要付費 |
| **Railway** | 用量計費（$5 額度起跳） | 同樣連 GitHub 自動部署，平台代管 | ✅ 有 cron | 設定簡單、UI 直覺 | 用量大時費用較難預估 |
| **Fly.io** | 有免費額度；小規模約 $5–10 | CLI 部署，貼近容器，需懂一點 Docker | ✅ 可排程（machines/cron） | 全球節點、彈性大 | 學習曲線略高 |
| **自架 VPS**（Linode/DO/Vultr） | **最省 ~$5 全包** | 全自己來：nginx、TLS 憑證、OS 更新、防火牆、備份 | ✅ 系統 cron 最簡單 | API+DB+ETL 一台搞定、成本最低、完全掌控 | 維運與資安都自負；初期設定較費工 |

> 評估建議：**省心選 Render**（內建 Cron 正好解決 ETL 排程）；**省錢且願維運選自架 VPS**。取捨＝省心 vs 省錢。

### 部署工作項（決定平台後再展開）
- [ ] CORS `allow_origins=["*"]` 改為正式網域（Web 上線必做）
- [ ] **SQLite → PostgreSQL**：⚠️ 不只是改連線字串！現有 SQL 有 SQLite 專屬語法（`AUTOINCREMENT`、`datetime('now','localtime')`），schema 需改寫相容 Postgres
- [ ] 前端正式網址：`api_service.dart`、`user_service.dart` 寫死的 `http://localhost:8000` 改為正式 API（並需 HTTPS）
- [ ] **ETL 伺服器排程**（從 P4 移入）：部署後在伺服器/平台 cron 設每日執行，指向正式 DB
- [ ] Flutter Web 打包並部署（之後若要手機版再做 Android APK / iOS IPA）

### ⚠️ 上線前須評估的風險
- [ ] **資料來源授權**：`yfinance`（爬 Yahoo 財經）個人測試可，**公開／商用可能違反服務條款**；公開發佈前評估改用合法資料源（證交所官方 API / 付費資料商）
- [ ] **無真正帳號**：訪客 UUID 模式下資料綁裝置，換機即失（已知取捨）

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
| Plan_Configs: **Free=5**（自選股上限，已統一 schema/後端/前端）| 與 14 檔預設不重疊計算 |
| 首頁放大鏡搜尋重用 `AddStockScreen` | 搜尋+一鍵加入邏輯已存在，避免重造 |
