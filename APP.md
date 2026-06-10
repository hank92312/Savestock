# 專案架構文件：Savestock（長線存股防護系統）

> 最後更新：2026-06-10
> 本文件為專案的單一入口參考：看完即可掌握整體內容與架構。
> 細部待辦與部署決策見 [TODONEXT.md](TODONEXT.md)。
> 雲端部署現況見 [第 7 節](#7-雲端部署現況gcp)。

---

## 1. 專案概述

* **專案名稱**：Savestock
* **核心目標**：以「儲蓄股利」為主的存股追蹤系統，強調長期投資與風險對抗，而非短期獲利。
* **目標受眾**：存股族、價值投資者、理財新手。
* **核心理念**：用「平均股息」計算真實殖利率，並以「絕對數值 + 產業分級」觸發暴跌／爆量警示，協助使用者避開**高殖利率陷阱**。
* **發佈方向（已定）**：**Web 優先**上線；帳號採**訪客 UUID**；含 **App 內教學導覽**。

---

## 2. 技術架構

| 層 | 技術 | 說明 |
| --- | --- | --- |
| 前端 | **Flutter (Dart)** | 跨平台 UI、財經折線圖（fl_chart）、互動 |
| 後端 | **Python FastAPI** | RESTful API，供 Flutter 呼叫 |
| ETL | **Python（yfinance + SQLAlchemy）** | 抓盤後資料、算股利/殖利率/警示、寫入 DB |
| 資料庫 | **SQLite**（本機開發）／**PostgreSQL 15**（生產：GCP Cloud SQL） | 透過 SQLAlchemy `DATABASE_URL` 切換；生產 schema 見 `database/init_postgres.sql` |
| 雲端 | **GCP Cloud Run + Cloud SQL** | FastAPI 容器化部署，見第 7 節 |
| 本地儲存 | shared_preferences | 用戶 UUID、教學導覽看過旗標 |

### 資料流
```
Yahoo 財經 ──(yfinance)──> ETL 批次運算 ──> savestock.db
                                                  │
                                          FastAPI 讀取/即時補抓
                                                  │
                                         Flutter App（呼叫 API 顯示）
```

---

## 3. 系統元件詳解

### 3.1 ETL（`etl/fetch_data.py`）
* 固定追蹤 **14 檔預設股**（清單寫死於 `TARGET_STOCKS`，不依賴 yfinance 的 sector 欄位）。
* 每檔抓 **1 年歷史收盤價**（約 245 筆）寫入 `Daily_Prices`，`Is_Default=1`。
* 計算並寫入 `Stock_Master`：平均股利、`Listing_Months`（上市月數）、`Default_Drop_Threshold`（產業閾值）。
* 目前**手動執行**；伺服器自動排程留待 P5 部署。

### 3.2 後端 API（`backend/`）
* 入口 `main.py`（CORS `allow_origins=["https://savestock.netlify.app"]`）、`database.py`（`engine` + `get_db()`，以 `engine.begin()` 自動 commit/rollback；`.strip()` 防 Secret Manager 換行）。
* 路由：`routers/stocks.py`、`routers/users.py`。

| Method | 路徑 | 說明 |
| --- | --- | --- |
| GET | `/` `/health` | 歡迎訊息／健康檢查 |
| GET | `/stocks/` | 預設清單（DB 快照，依殖利率**降序**；開啟時快速載入用） |
| POST | `/stocks/refresh` | 即時抓 yfinance 更新所有預設股並回傳（首頁「更新」按鈕/下拉用） |
| GET | `/stocks/search?q=&limit=` | 模糊搜尋候選（上市＋ETF，上櫃不列） |
| GET | `/stocks/lookup/{id}` | 即時查任意台股（代號或中文名）；自動判斷 `.TW/.TWO`，抓取並寫入 DB |
| GET | `/stocks/{id}` | 單一股票（DB 快照） |
| GET | `/stocks/{id}/prices?days=` | 歷史收盤價（1–365 日） |
| GET | `/stocks/{id}/dividends?months=` | 現金股利發放紀錄（6/12/24 月，供股利折線圖） |
| POST | `/users/` | 以 UUID 建立用戶 |
| GET | `/users/{uid}/watchlist` | 自選清單（DB，依殖利率降序） |
| POST | `/users/{uid}/watchlist` | 加入自選（檢查方案上限，超過回 403） |
| DELETE | `/users/{uid}/watchlist/{sid}` | 移除自選 |
| POST | `/users/{uid}/watchlist/refresh` | 即時刷新自選並回傳（依殖利率降序） |

* **搜尋快取**：來源 TWSE `STOCK_DAY_ALL`（含 ETF 如 0050），24h TTL；上櫃不在範圍。
* **自選股共用補抓**：`_fetch_and_upsert()` 供 lookup 與 watchlist/refresh 共用（即時 yfinance 更新、補 1 年歷史、自選股以 3% 跌幅＋2.5× 量警示）。

### 3.3 資料庫 Schema（`database/init_sqlite.sql`）
| 表 | 重點欄位 |
| --- | --- |
| `Plan_Configs` | `Tier_ID`, `Tier_Name`, `Max_Total_Stocks` |
| `Users` | `User_ID`, `Email`, `OAuth_Provider`, `UUID` |
| `User_Licenses` | `User_ID`, `Tier_ID`, `Purchase_Date` |
| `Stock_Master` | `Stock_ID`, `Name`, `Sector`, `Avg_Dividend_2Y`, `Dividend_1Y`, `Default_Drop_Threshold`, **`Listing_Months`**, `Last_Updated`,（實際 DB 另有 `Is_Default`） |
| `User_Stocks` | `User_ID`, `Stock_ID`, `Status`, `Is_Default`, `Custom_Drop_Threshold` |
| `Daily_Prices` | `Stock_ID`, `Date`, `Close_Price`, `Volume`, `Alert_Flag`, `Alert_Reason` |
| `Dividends` | `Stock_ID`, `Ex_Date`, `Cash_Dividend`, `Stock_Dividend`（現金＋股票股利歷史，供股利折線圖；`_fetch_and_upsert` 寫入） |
| `User_Preferences` | `Push_Enabled`, `Email_Enabled`（推播/郵件，尚未接線） |

> 免費方案自選上限＝**5 檔**（已統一：schema 種子、後端無授權 fallback、前端文案皆為 5）。

### 3.4 前端 Flutter（`frontend/lib/`）
| 檔案 | 角色 |
| --- | --- |
| `main.dart` | 入口；`MaterialApp` + 自訂 `ScrollBehavior`（讓 web/桌機滑鼠可拖曳捲動） |
| `screens/onboarding_screen.dart` | **教學導覽**（首次自動顯示、❓可重看；殖利率→用法→警示→免責） |
| `screens/app_shell.dart` | 底部導覽（預設清單／我的股票）＋首次啟動導覽判斷 |
| `screens/home_screen.dart` | 預設清單、產業篩選 Chip、響應式佈局、下拉刷新、❓教學入口 |
| `screens/my_stocks_screen.dart` | 自選清單、開啟即時刷新、刪除鈕（＋左滑刪除）、外部加入即時同步 |
| `screens/add_stock_screen.dart` | 模糊搜尋＋候選清單＋無結果直接查詢＋已追蹤標記 |
| `screens/stock_detail_screen.dart` | 殖利率大字（近1年＋近2年並列）、數據卡（兩種股利＋新上市提示）、AppBar「加入我的股票」書籤鈕、收盤價折線圖＋股利折線圖（半年/1年/2年）、警示卡 |
| `services/watchlist_notifier.dart` | 加入自選後跨畫面即時通知「我的股票」重抓清單（singleton ChangeNotifier） |
| `widgets/stock_card.dart`, `widgets/sector_badge.dart` | 共用股票卡、產業標籤 |
| `services/api_service.dart`, `services/user_service.dart` | API 呼叫層、UUID 與 user_id 本地管理 |
| `models/stock.dart` | `Stock`（含 `listingMonths` / `isNewListing`） |
| `theme/app_theme.dart` | 全域樣式 |

---

## 4. 核心計算邏輯

### 股利口徑（重要）
* **股利＝現金股利＋股票股利（配股）**。台股配股記於 yfinance `actions` 的「Stock Splits」欄，配股 X 元對應配股比 (1+X/10)，故 **股票股利(元) =（配股比−1）×10**（面額還原；僅計配股 ratio>1，減資不計）。
* 早期只計現金股利會嚴重低估含配股個股（如聯邦銀 2838：純現金殖利率 ~1.5% → 含配股 ~5%），已修正。
* ⚠️ yfinance 偶有將單次配股拆成多列的資料瑕疵（如 2838 2024-07 重複），會略為高估近2年平均；近一年（主要指標）不受影響。

### 基準股利（年化平均）
* **上市 ≥ 2 年**：近 2 年股利合計 ÷ 2。
* **上市 < 2 年（`Listing_Months` < 24）**：上市迄今全部股利 ÷ 上市年數（年化）；前端標示「上市迄今平均」並提醒涵蓋約 X 個月。

### 殖利率
* **清單顯示與排序**：以**近一年殖利率**（`Dividend_1Y ÷ 最新收盤價`）為主，清單與自選皆依此**降序**排列；卡片股利欄顯示「近1年股利」（不滿 12 月標「近 X 月股利」）。
* **詳情頁**：同時並列**近一年殖利率**與**近2年平均殖利率**（2 年平均為保守參考，揭露配息陷阱）；數據卡同時顯示近1年股利與近2年平均股利，不滿 1/2 年改標「近 X 月／上市迄今平均」並加邊界提示。

### 異常警示（防高殖利率陷阱）
1. **單日暴跌**（依產業分級閾值）：

   | 產業 | 閾值 |
   | --- | --- |
   | 營建 Construction | 6% |
   | 半導體 Semiconductor | 5% |
   | ETF | 4% |
   | 食品 Food | 3% |
   | 金融 Finance／電信 Telecom | 2.5% |
   | 其他（預設） | 4% |

2. **交易量異常**：當日量 ≥ 近 20 日均量的 **2.5 倍**。
3. 觸發時於 `Daily_Prices` 寫入紅色警示備註（含跌幅／爆量倍數）。

---

## 5. 功能模組

* **權限與額度**：訪客模式（UUID 綁裝置，換機/重裝會遺失）；方案上限由 `Plan_Configs.Max_Total_Stocks` 驅動，超過回 403 並引導升級。買斷/登入為未來規劃。
* **資料計算**：見第 4 節。
* **異常警示**：見第 4 節。
* **通知系統（規劃中）**：FCM 推播 / Email，`User_Preferences` 已備欄位，尚未接線。

---

## 6. 開發進度

### ✅ 已完成
* 資料庫、ETL（產業別警示、1 年歷史、新上市年化、產業閾值寫入）。
* 後端 12 支端點（搜尋/lookup/prices/自選 CRUD/refresh，清單與自選皆殖利率排序）。
* Flutter 全畫面：首頁、我的股票、查詢、詳情、**教學導覽**。
* 體驗優化（P3）：下拉刷新、已追蹤標記、上限友善提示、滑鼠拖曳、圖表日期、刪除鈕。
* 詳情頁「加入我的股票」書籤鈕＋跨畫面即時同步；股票名稱統一中文（搜尋快取優先）；股價顯示至小數點 2 位。

### ⏳ 待辦
* **ETL 自動排程**：Cloud Scheduler 每日盤後觸發（詳見 TODONEXT）。
* 通知系統接線（`User_Preferences` 已備欄位）。
* 評估試用期後是否續用 Cloud SQL（~$9/月）或改 Local-First 架構。

---

## 7. 雲端部署現況（GCP）

> 平台已定案：**Google Cloud Platform**（使用 $300 試用折抵金，70 天試用期）。

### 7.1 已部署資源（GCP 專案：`savestock-app`，區域 `asia-east1`）

| 資源 | 服務 | 識別 / 設定 |
| --- | --- | --- |
| 後端 API | **Cloud Run** | 服務名 `savestock-api`；512Mi；min=0 / max=2 instances；允許未驗證存取 |
| 資料庫 | **Cloud SQL (PostgreSQL 15)** | 實例 `savestock-db`；`db-f1-micro`；10GB SSD；**無自動備份**（省成本） |
| 容器倉庫 | **Artifact Registry** | `savestock-repo`（Docker 格式） |
| 容器建置 | **Cloud Build** | 遠端建置（本機未裝 Docker）；image tag `savestock-api:latest` |

* **正式 API 網址**：`https://savestock-api-62102931839.asia-east1.run.app`
* **前端網址**：`https://savestock.netlify.app`（Flutter Web，Netlify 靜態托管）
* **DB 連線**：Cloud Run 透過 Unix socket 連 Cloud SQL（`--add-cloudsql-instances`），`DATABASE_URL` 由 **GCP Secret Manager**（`savestock-db-url`）注入（`--set-secrets`），不寫入環境變數明文。
* **容器化檔案**：`backend/Dockerfile`（python:3.11-slim + libpq）、`backend/.dockerignore`。
* **健康檢查**：`/health` 已驗證回 `{"status":"healthy"}`；`/stocks` 已驗證回 200（空陣列，待資料填充）。

### 7.2 SQLite → PostgreSQL 改寫重點（已完成）

* 新增 `database/init_postgres.sql`（`SERIAL` 主鍵、`BOOLEAN` 型別、`ON CONFLICT DO NOTHING` 種子）。
* `backend/database.py`：依 `DATABASE_URL` 前綴自動切換（SQLite 才加 `check_same_thread`）。
* `backend/routers/stocks.py`：布林比較改 `Is_Default = TRUE`、寫入改 `FALSE`（PostgreSQL 不接受 `boolean = integer`）。
* `backend/requirements.txt`：補上 `yfinance`、`requests`（Cloud Run 容器缺套件會啟動失敗）。

### 7.3 P5 部署完成狀況（2026-06-10）

| 項目 | 狀態 |
| --- | --- |
| 雲端 DB 資料填充（14 檔預設股） | ✅ 完成 |
| Flutter App baseUrl 換雲端 API | ✅ `api_service.dart`、`user_service.dart` 已改 |
| CORS 收斂 | ✅ `allow_origins=["https://savestock.netlify.app"]` |
| Secret Manager（DATABASE_URL） | ✅ `savestock-db-url` version 2 active |
| Flutter Web 部署 Netlify | ✅ `https://savestock.netlify.app` |
| 手機端對端驗證 | ✅ 全功能通過 |
| **ETL 自動排程（Cloud Scheduler）** | 🔴 **待辦**（見 TODONEXT） |

### 7.4 成本提醒

* 試用期內全部由 $300 折抵金支付。
* 試用後預估 **約 $10–15/月**（最大固定成本為 Cloud SQL `db-f1-micro` ~$7–10；Cloud Run 低流量近乎免費）。
* 試用期結束前須評估是否續用或改採「最小雲端 DB（只存 Users/Subscriptions）＋ 裝置端 sqflite」的 Local-First 架構（討論見對話紀錄，尚未實作）。

### 7.5 風險

* `yfinance`（爬 Yahoo）公開/商用可能違反服務條款，上線前須評估合法資料源。
* 訪客 UUID 模式資料綁裝置，換機/重裝遺失。

---

## 8. 關鍵設計決策

| 決策 | 原因 |
| --- | --- |
| 預設股 `Is_Default=1`、自選股 `Is_Default=0` | 避免 lookup 新增股混入預設清單 |
| 股票中文名優先取 TWSE 搜尋快取（批次、穩定），次為即時 mis API，最後才 yfinance 英文 | 即時 mis API 偶爾失敗會退回英文名並寫入 DB；既有英文名於下次更新自動升級為中文 |
| 我的股票開啟即 `refresh` | 顯示即時資料而非 DB 快照 |
| 搜尋快取用 STOCK_DAY_ALL | 涵蓋 ETF；上櫃不在範圍 |
| 債券 ETF（00xxB）不支援 | Yahoo 無資料，顯示明確說明 |
| 新上市 < 24 月股利年化 | 固定 ÷2 會低估新上市股 |
| 清單顯示／排序改用近一年殖利率 | 反映最新配息水準；近2年平均保留於詳情頁作保守參考 |
| 殖利率／股利併計股票股利，配股按面額還原 | 只算現金會大幅低估含配股個股（聯邦銀等）；面額還原為台股配息表慣例、較保守，並於詳情頁加註說明 |
| 股利歷史存 DB（`Dividends` 表，現金/配股分欄）而非每次即時抓 | 詳情頁股利圖讀 DB 快、與價格圖一致，tooltip 可拆解現金／配股；`_fetch_and_upsert` 順手寫入 |
| 殖利率降序排序（清單與自選一致） | refresh 端點亦於回傳前排序 |
| 刪除用「常駐按鈕＋左滑」 | 左滑為觸控手勢，web 滑鼠難觸發 |
| 自訂 ScrollBehavior 加 mouse | 讓 web/桌機滑鼠可拖曳捲動/下拉 |

---

## 9. 啟動指令速查

```powershell
# 1. 啟動本機 API（開發用）
Start-Process -FilePath "c:\Savestock\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","main:app","--port","8000" -WorkingDirectory "c:\Savestock\backend" -WindowStyle Hidden

# 2. 確認本機 API
Invoke-RestMethod http://localhost:8000/health

# 3. 手動執行本機 ETL
Set-Location C:\Savestock; .venv\Scripts\python.exe etl\fetch_data.py

# 4. 啟動 Flutter 本機預覽
Set-Location C:\Savestock\frontend; flutter run -d chrome --web-port 5000

# ── 生產部署 ────────────────────────────────────────────────

# 5. 打包 + 部署前端到 Netlify
Set-Location C:\Savestock\frontend; flutter build web --release
Set-Location C:\Savestock\frontend\build\web
netlify deploy --prod --dir=. --site=ebec3bc6-8ea5-4131-98b0-e08c54aaaac8

# 6. 部署後端到 Cloud Run（Google Cloud SDK Shell 執行）
# gcloud builds submit "C:\Savestock\backend" --tag=asia-east1-docker.pkg.dev/savestock-app/savestock-repo/savestock-api:latest --project=savestock-app
# （deploy 指令含密碼，見 TODONEXT.md 常用部署指令）

# 7. 同步資料到 Cloud SQL（需先啟動 Cloud SQL Auth Proxy）
# 密碼查詢：gcloud secrets versions access latest --secret="savestock-db-url" --project=savestock-app
```
