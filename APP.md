# 專案架構文件：Savestock（長線存股防護系統）

> 最後更新：2026-07-01（Phase 5：ETF 成分股追蹤與進階分析模組上線）
> 本文件為專案的單一入口參考：看完即可掌握整體內容與架構。
> 雲端部署現況見 [第 7 節](#7-雲端部署現況gcp)。
> ETF 模組完整規格見 [`etf_tracker.md`](etf_tracker.md)。

---

## 1. 專案概述

* **專案名稱**：Savestock
* **核心目標**：以「儲蓄股利」為主的存股追蹤系統，強調長期投資與風險對抗，而非短期獲利。
* **目標受眾**：存股族、價值投資者、理財新手。
* **核心理念**：用「平均股息」計算真實殖利率，並以「絕對數值 + 產業分級」觸發暴跌／爆量警示，協助使用者避開**高殖利率陷阱**。
* **發佈方向（已定）**：**Web 優先**上線；帳號採**訪客 UUID**；含 **App 內教學導覽**。
* **延伸模組**：ETF 成分股追蹤與進階分析（16 檔科技/AI 主題 ETF + 使用者自訂 ETF），見 [3.5 節](#35-etf-追蹤模組backend-etl-web_django)。

---

## 2. 技術架構

| 層 | 技術 | 說明 |
| --- | --- | --- |
| 前端 | **Flutter (Dart)** | 跨平台 UI、財經折線圖（fl_chart）、互動 |
| 後端 | **Python FastAPI** | RESTful API，供 Flutter 呼叫 |
| ETL | **Python（yfinance + SQLAlchemy）** | 抓盤後資料、算股利/殖利率/警示、寫入 DB |
| 資料庫 | **SQLite**（本機開發）／**Neon PostgreSQL**（生產：免費方案） | 透過 SQLAlchemy `DATABASE_URL` 切換；生產 schema 見 `database/init_postgres.sql` |
| 雲端 | **GCP Cloud Run + Neon PostgreSQL** | FastAPI（`savestock-api`）＋ Django 報表服務（`savestock-report`）容器化部署，見第 7 節 |
| 網頁報表 | **Django** | 伺服器渲染可分享/可列印年度股利報表 + **ETF Dashboard/成分股/進階分析頁** + Django Admin；計算 import 共用 `core` |
| 本地儲存 | shared_preferences | 用戶 UUID、教學導覽看過旗標、股利試算持股清單（裝置端，見 4 節） |

### 資料流
```
Yahoo 財經 ──(yfinance)──> ETL 批次運算 ──> savestock.db
                                                  │
                                          FastAPI 讀取/即時補抓
                                                  │
                                         Flutter App（呼叫 API 顯示）

Yahoo 財經（含美股/韓股跨境）──(yfinance)──> etl/fetch_etf.py（每日 15:30）
                                                  │
                                    ETF_Holdings / ETF_Holding_History
                                                  │
                              Django ETF Dashboard / 成分股 / 進階分析頁（伺服器渲染）
```

---

## 3. 系統元件詳解

### 3.1 ETL（`etl/fetch_data.py`）
* 固定追蹤 **25 檔預設股**（清單寫死於 `TARGET_STOCKS`，不依賴 yfinance 的 sector 欄位）。
* 每檔抓 **1 年歷史收盤價**（約 245 筆）寫入 `Daily_Prices`，`Is_Default=1`。
* 計算並寫入 `Stock_Master`：平均股利、`Listing_Months`（上市月數）、`Default_Drop_Threshold`（產業閾值）。
* **Cloud Scheduler 自動排程**：每週一至五 **15:00（台灣時間）** 呼叫 `POST /stocks/refresh`，台股 13:30 收盤後自動更新當日收盤價。工作名稱：`savestock-etl-daily`，區域 `asia-east1`。

### 3.2 後端 API（`backend/`）
* 入口 `main.py`（CORS `allow_origins=["https://savestock.netlify.app"]` + `allow_origin_regex=r"http://localhost(:\d+)?"` 供本地 `flutter run -d chrome` 開發）、`database.py`（`engine` + `get_db()`，以 `engine.begin()` 自動 commit/rollback；`.strip()` 防 Secret Manager 換行）。
* 路由：`routers/stocks.py`、`routers/users.py`、`routers/portfolio.py`、`routers/etf.py`。
* **共用計算層 `core/`**：框架無關的 Python 模組——`dividend_calc.py`（股利估算口徑）、`twse_dividends.py`（證交所已公告配息）、`etf_analytics.py`（ETF 四大分析，見 4 節），供 FastAPI 與 Django 報表共用，避免邏輯多份維護。附 `tests/`（pytest，含 `test_etf_analytics.py` 9 案例）。

| Method | 路徑 | 說明 |
| --- | --- | --- |
| GET | `/` `/health` | 歡迎訊息／健康檢查 |
| GET | `/stocks/` | 預設清單（DB 快照，依殖利率**降序**；開啟時快速載入用） |
| POST | `/stocks/refresh` | 即時抓 yfinance 更新所有預設股並回傳（首頁「更新」按鈕/下拉用） |
| GET | `/stocks/search?q=&limit=` | 模糊搜尋候選（上市＋ETF，上櫃不列） |
| GET | `/stocks/lookup/{id}` | 查任意台股（代號或中文名）；DB 有 5 日內資料直接回傳（<1 秒），否則即時抓 yfinance（~25 秒） |
| GET | `/stocks/{id}` | 單一股票（DB 快照） |
| GET | `/stocks/{id}/prices?days=` | 歷史收盤價（1–365 日） |
| GET | `/stocks/{id}/dividends?months=` | 現金股利發放紀錄（6/12/24 月，供股利折線圖） |
| POST | `/users/` | 以 UUID 建立用戶 |
| GET | `/users/{uid}/watchlist` | 自選清單（DB，依殖利率降序） |
| POST | `/users/{uid}/watchlist` | 加入自選（檢查方案上限，超過回 403） |
| DELETE | `/users/{uid}/watchlist/{sid}` | 移除自選 |
| POST | `/users/{uid}/watchlist/refresh` | 即時刷新自選並回傳（依殖利率降序）；**並行抓取（max 5 threads）**，10 檔 ~50 秒 |
| POST | `/portfolio/estimate` | 個人年度股利試算：傳入持股清單（`stock_id`/`quantity`/`basis`），回傳全年估算總額、各檔明細、今年已除息、影響較大個股；DB 缺漏股票並行補抓 |
| POST | `/etf/refresh` | 重新抓取全部 ETF（16 檔固定 + 使用者自訂）成分股與跨境收盤價；供 Cloud Scheduler 每日 15:30 觸發，延遲 import `etl/fetch_etf.py` 避免拖慢 API 啟動 |

* **搜尋快取**：來源 TWSE `STOCK_DAY_ALL`（含 ETF 如 0050），24h TTL；上櫃不在範圍。
* **自選股共用補抓**：`_fetch_and_upsert()` 供 lookup 與 watchlist/refresh 共用（即時 yfinance 更新、補 1 年歷史、自選股以 3% 跌幅＋2.5× 量警示）。
* **連線池設定**：`pool_pre_ping=True, pool_recycle=300`，防止 Neon 閒置關閉連線後回傳死連線（`SSL connection has been closed unexpectedly`）。

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
| `ETF_Master` | `ETF_ID`, `Name`, `Category`, `Is_Custom`, `Owner_User_ID`, `Last_Updated`（16 檔固定種子 + 使用者自訂） |
| `ETF_Holdings` | `ETF_ID`, `Stock_ID`, `Stock_Name`, `Weight`, `Snapshot_Date`（當前快照，ETL 先刪後插） |
| `ETF_Holding_History` | `ETF_ID`, `Stock_ID`, `Date`, `Weight`（每日 append，供近 10 天權重趨勢折線圖） |

> 免費方案自選上限＝**10 檔**（已統一：schema 種子、後端無授權 fallback、前端文案皆為 10）。
> ETF 新表定義於 `database/init_postgres.sql` / `init_sqlite.sql`；**非自動 migration**，正式 DB 需手動執行一次建表語句（`CREATE TABLE IF NOT EXISTS` + `ON CONFLICT DO NOTHING`，可重複執行）。

### 3.4 前端 Flutter（`frontend/lib/`）
| 檔案 | 角色 |
| --- | --- |
| `main.dart` | 入口；`MaterialApp` + 自訂 `ScrollBehavior`（讓 web/桌機滑鼠可拖曳捲動） |
| `screens/onboarding_screen.dart` | **教學導覽**（首次自動顯示、❓可重看；殖利率→用法→警示→免責） |
| `screens/app_shell.dart` | 底部導覽（預設清單／我的股票／股利試算）＋首次啟動導覽判斷 |
| `screens/home_screen.dart` | 預設清單、產業篩選 Chip、響應式佈局、下拉刷新、❓教學入口 |
| `screens/my_stocks_screen.dart` | 自選清單、**開啟用 DB 快速載入（<1 秒）**、🔄 按鈕才即時抓 yfinance、刪除鈕（＋左滑刪除）、外部加入即時同步 |
| `screens/add_stock_screen.dart` | 模糊搜尋＋候選清單＋無結果直接查詢＋已追蹤標記 |
| `screens/stock_detail_screen.dart` | 殖利率大字（近1年＋近2年並列）、數據卡（兩種股利＋新上市提示）、AppBar「加入我的股票」書籤鈕、收盤價折線圖＋股利折線圖（半年/1年/2年）、警示卡 |
| `screens/dividend_calc_screen.dart` | **年度股利試算**：輸入持股（搜尋選股＋股數，含零股）→ 估算今年可領股利；持股存裝置端、自動回填；估算後彈提示窗（歷史估算說明＋影響較大個股）；**分享功能**：「分享」按鈕開底部 Sheet，提供複製連結／開啟報表／LINE／Facebook／下載試算圖片（PNG，含持股明細）5 個選項；`package:web` 直接呼叫 `window.open` 繞過 url_launcher 限制 |
| `services/watchlist_notifier.dart` | 加入自選後跨畫面即時通知「我的股票」重抓清單（singleton ChangeNotifier） |
| `services/portfolio_service.dart` | 試算持股清單的裝置端儲存（shared_preferences，與 UUID 同機制） |
| `widgets/stock_card.dart`, `widgets/sector_badge.dart` | 共用股票卡（現價下方顯示「截至 MM/DD」資料日期）、產業標籤 |
| `services/api_service.dart`, `services/user_service.dart` | API 呼叫層、UUID 與 user_id 本地管理 |
| `models/stock.dart`, `models/portfolio.dart` | `Stock`；`Holding` / `PortfolioItem` / `PortfolioEstimate`（試算模型） |
| `widgets/module_switch_bar.dart` | 「存股追蹤 ↔ ETF 追蹤」模組切換列；ETF 端直接連到 Django `/etf`（不同服務，非 Flutter 內路由） |
| `theme/app_theme.dart` | 全域樣式 |

### 3.5 ETF 追蹤模組（`backend/`、`etl/`、`web_django/`）

延伸模組，追蹤 16 檔科技/AI 主題 ETF 成分股，並提供 4 種進階分析。完整資料範疇與演算法規格見 [`etf_tracker.md`](etf_tracker.md)；此節僅記錄與既有架構的整合方式。

* **ETL（`etl/fetch_etf.py`）**：
  * 逐檔 ETF 用 `etl/etf_source.py`（yfinance 為主，留 cmoney/moneydj 備援插槽）抓成分股權重，`etl/name_resolver.py` 將台股成分股名稱轉中文（美股/韓股維持英文）。
  * 寫入 `ETF_Holdings`（先刪後插＝當前快照）＋ append `ETF_Holding_History`（每日累積，供近 10 天權重趨勢）。
  * 蒐集所有成分股跨 ETF 去重後，`ThreadPoolExecutor`（max 5，與 watchlist/refresh 同慣例）並行補抓約 4 個月收盤價；新成分股以 stub 列寫入 `Stock_Master`（`ON CONFLICT DO NOTHING`，不覆蓋既有預設股的股利資料）。
  * 可獨立執行（`python etl/fetch_etf.py`）或由 `/etf/refresh` 觸發 `run()`。
  * **注意**：`fetch_etf.py` 自建獨立 SQLAlchemy engine（非 `backend/database.py` 共用），未設 `pool_pre_ping`；目前運作正常，若日後遇到 Neon 閒置斷線可比照 `backend/database.py` 補上。
* **後端 API（`backend/routers/etf.py`）**：單一端點 `POST /etf/refresh`，延遲 import `etl/fetch_etf.py`（`sys.path` 動態加入 `etl/` 目錄）避免其重依賴拖慢 API 啟動；無需驗證，供 Cloud Scheduler 內部呼叫。
* **分析層（`backend/core/etf_analytics.py`）**：框架無關純函式，FastAPI／Django 共用：
  1. **重疊共識股**：計算多檔 ETF 共同持有個股的 `etf_count`（持有檔數）、`total_weight`（權重加總）。
  2. **隱藏強勢股**：`Hidden Score = etf_count × (1 / avg_weight)`，找「廣泛持有但單一權重不高」的潛力股。
  3. **權重熱力圖**：ETF × 個股交叉權重矩陣。
  4. **AI 三因子選股**：綜合 ETF 共識度、隱藏強度、近 3 月動能，加權輸出 Top 20。
  * 附 `backend/tests/test_etf_analytics.py`（9 案例，pytest）。
* **呈現層（`web_django/report/`）**：伺服器渲染，沿用既有設計 token：
  * `GET /etf` Dashboard（分群卡片：Tech / AI 兩族群）。
  * `GET /etf/<etf_id>` 成分股詳情（表格＋權重圓餅圖＋歷史權重折線圖）。
  * `GET /etf/analytics` 進階分析頁（支援 `?etfs=` 手動選擇或預設全部）。
  * `POST /etf/add`／`POST /etf/<etf_id>/delete`：使用者新增/刪除自訂 ETF（`Is_Custom=True`；預設 16 檔不可刪）。新增時**不**同步抓收盤價（太慢），改由下次每日 ETL 自動補上。
  * `report/context_processors.py` 的 `nav_urls` 注入 `STOCK_APP_URL`（Flutter App 網址）供頂部模組切換列使用。
* **部署整合**：`backend/Dockerfile` 與 `web_django/Dockerfile` 皆改以 **repo root 為 build context**，同時 `COPY` `backend/`（或 `web_django/`）與 `etl/`，讓兩個服務都能 import 同一份 ETF 抓取邏輯（見 [7.1 節](#71-已部署資源gcp-專案savestock-app區域asia-east1)）。

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

### 個人年度股利試算（`core/dividend_calc.py`、`core/twse_dividends.py`）
* **三層口徑（優先序）**：
  1. **已公告**（`source=announced`）：年配股今年正式公告之全年配息，來自證交所 OpenAPI `t187ap45_L`（`core/twse_dividends.py` 抓全市場、快取 12h）。實際值、非估算。
  2. **近1年**（`Dividend_1Y`，滾動 12 月）／**近5年平均**（`Avg_Dividend_5Y`）：未公告時依使用者選的基準估算。
* **為何季配股不用已公告**：季配／半年配股年中無法得知全年完整配息（後續季別尚未開會決議），證交所資料只有「年度」列＝年配股；季配股交回滾動估算（近1年本就涵蓋完整週期）。
* **為何不用「今年已除息」當全年值**：yfinance 只提供已除息歷史，季配股年中「已除息」只是部分金額，當全年會嚴重低估。故「今年已除息」僅作實際資訊併列。
* **影響較大個股**：只列「估算（非已公告）」個股——已公告為確定值，不確定的才需提醒。
* **影響較大個股**：占估算總額比重 ≥ 10% 者（無人跨門檻則取前 3 大），其配息變動最影響總額，於估算後提示窗列出。
* 純函式設計、不依賴框架／DB，FastAPI 與未來 Django 共用；附 7 個單元測試（季配股不低估、basis 切換、零股、查無資料 fail loud）。

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
* 資料庫、ETL（產業別警示、1 年歷史、新上市年化、產業閾值寫入、Dividends 表寫入、配股口徑修正）。
* 後端 12 支端點（搜尋/lookup/prices/自選 CRUD/refresh，清單與自選皆殖利率排序）。
* Flutter 全畫面：首頁、我的股票、查詢、詳情、**教學導覽（5頁含搜尋說明）**。
* 體驗優化（P3）：下拉刷新、已追蹤標記、上限友善提示、滑鼠拖曳、圖表日期、刪除鈕。
* 詳情頁「加入我的股票」書籤鈕＋跨畫面即時同步；股票名稱統一中文；股價顯示至小數點 2 位。
* UI 美化：卡片陰影（`AppTheme.cardDecoration`）、產業標籤膠囊型、殖利率分色高亮膠囊。
* 預設股擴充至 **25 檔**；ETL 全量同步至 Neon。
* 股利直條圖加「近5年」選項；不足5年自動顯示提示文字。
* 首頁「使用教學」按鈕加文字（手機可見）。
* **Cloud SQL → Neon 遷移**（2026-06-11）：DB 月費歸零，Secret Manager version 4。
* **ETL 自動排程上線**（2026-06-11）：Cloud Scheduler `savestock-etl-daily`，週一至五 15:00。
* **效能優化**（2026-06-11）：
  * 「我的股票」打開改用 DB 快取（<1 秒），🔄 才即時刷新。
  * `/stocks/lookup/` DB 5 日內有資料直接回傳（~300ms），不再每次打 yfinance。
  * `watchlist/refresh` 改並行抓取（ThreadPoolExecutor max 5），10 檔從 250 秒縮至 ~50 秒，修復 504 timeout。
  * 股票卡片加「截至 MM/DD」資料日期標籤。
  * `pool_pre_ping` 修復 Neon 閒置連線 SSL 斷線錯誤。
* **個人年度股利試算 Phase 1**（2026-06-15）：`core/dividend_calc.py` 共用計算模組（+7 單元測試）、`POST /portfolio/estimate`、Flutter「股利試算」分頁（持股存裝置端、自動回填、估算提示窗）。已部署上線。
* **個人年度股利試算 Phase 2**（2026-06-15）：`web_django/` Django 報表服務上線——伺服器渲染可分享/可列印報表（`/report?d=base64持股`，計算 import 共用 `core`、ORM 讀 Neon）、Django Admin 唯讀檢視 Stock_Master；Flutter 試算結果加「產生可分享網頁報表」按鈕。已部署（Cloud Run `savestock-report`）。
* **個人年度股利試算 Phase 3**（2026-06-15）：`core/twse_dividends.py` 接證交所 OpenAPI `t187ap45_L`，年配股採今年正式公告之全年配息（實際值優先於估算）；季配股維持滾動估算；試算/報表標示「已公告 vs 估算」。已部署（FastAPI + Django + 前端）。
* **分享功能 Phase 4**（2026-06-15）：
  * **Bug 修正**：原「產生可分享網頁報表」按鈕以 `url_launcher` 的 `LaunchMode.externalApplication` 開新分頁，在 `url_launcher_web 2.4.1`（已遷移 `package:web`）下靜默失敗；改用 `package:web` 直接呼叫 `web.window.open(url, '_blank')`，瀏覽器正確觸發開新分頁/封鎖提示。
  * **多元分享 Sheet**：計算後改為「分享」按鈕，開底部 Sheet，包含 5 個選項：複製連結（報表 URL 到剪貼簿）、開啟報表（新分頁 Django HTML）、LINE 分享（`social-plugins.line.me`）、Facebook 分享（`facebook.com/sharer`）、下載試算圖片（PNG）。
  * **試算圖片**：`_ShareCard` widget（`375px` 固定寬，白底）以 `Positioned(left: -2000)` 渲染於 Stack off-screen，`RepaintBoundary.toImage(pixelRatio: 3.0)` 截圖後透過 `Blob` + anchor click 下載；內容包含 Savestock 標題、年份、總額漸層卡、各持股明細（名稱/代號/股數/股利/已公告或估算標籤）、網站 footer。
  * **CORS 開放 localhost**：`backend/main.py` 加 `allow_origin_regex=r"http://localhost(:\d+)?"`，`flutter run -d chrome` 本地開發不需修改 API URL。已部署（FastAPI revision 00023）。
  * **pubspec.yaml**：加 `web: ^1.1.0`（將已存在的 transitive dep 升為 direct dep）。
* **股利計算修正與效能優化**（2026-06-23）：
  * `_dividend_1y` 加 400 天 fallback：358 天主窗口無股利時延伸判斷，修正年配股除息日恰落在 359–400 天前的個股（如聯強 2347、中保科 9917）近一年股利誤判為 0。
  * `/stocks/refresh` 改 `ThreadPoolExecutor` 並行（max 10）、已有中文名/上市月數的股票跳過 `ticker.info`，修復 25 檔串行抓取超過 Cloud Run 300s timeout 而 504 的問題。
  * `database.py` SQLite 連線加 `timeout=30`，讓本地並行寫入排隊等待而非報 `database is locked`（生產 Postgres 不受影響）。
* **ETF 追蹤與進階分析模組 Phase 1**（2026-07-01）：詳見 [3.5 節](#35-etf-追蹤模組backend-etl-web_django)。
  * 資料層：`ETF_Master`／`ETF_Holdings`／`ETF_Holding_History` 三張新表（手動套用至 Neon，非自動 migration）。
  * 抓取層：`etl/etf_source.py`、`etl/fetch_etf.py`、`etl/name_resolver.py`，16 檔 ETF × 10 檔成分股，含美股/韓股跨境收盤價。
  * 分析層：`backend/core/etf_analytics.py` 四大模組 + 9 個 pytest。
  * 呈現層：Django Dashboard／成分股詳情／進階分析頁，含使用者自訂 ETF 新增/刪除。
  * API：`POST /etf/refresh` 供 Cloud Scheduler 觸發；新增排程 `savestock-etf-daily`（週一至五 15:30，晚於股價排程 30 分避開撞期）。
  * **部署修正**：`backend/Dockerfile` 原以 `backend/` 為 build context，`COPY . .` 不含 `etl/`，上線後 `/etf/refresh` 會 `ModuleNotFoundError`；改為 repo root context（新增 `cloudbuild-api.yaml`），與 Django 的建置方式一致。
  * Cloud Run `savestock-api` request timeout 由 300s 提高至 600s（`/etf/refresh` 抓 83 檔跨境成分股價偶爾超過 300s）。
  * 已部署上線並驗證：16/16 ETF 成分股、82/83 成分股收盤價（剩餘 1 檔跨境股由排程自動補上，逐檔 commit 不會遺失進度）。

### ⏳ 待辦
* 通知系統接線（`User_Preferences` 已備欄位）。
* 已知限制：證交所 `t187ap45_L` 僅含上市（`.TW`）；上櫃（`.TWO`）年配股目前無已公告資料、走估算。
* `backend/Dockerfile` 未設 `PYTHONUNBUFFERED=1`，長任務（如 `/etf/refresh`）的 print log 會整批緩衝輸出，即時進度不可見（不影響功能，只影響除錯時的可觀測性）。
* `etl/fetch_etf.py` 自建獨立 DB engine，未設 `pool_pre_ping`（見 3.5 節）。

---

## 7. 雲端部署現況（GCP）

> 平台已定案：**Google Cloud Platform**（使用 $300 試用折抵金，70 天試用期）。

### 7.1 已部署資源（GCP 專案：`savestock-app`，區域 `asia-east1`）

| 資源 | 服務 | 識別 / 設定 |
| --- | --- | --- |
| 後端 API | **Cloud Run** | 服務名 `savestock-api`；512Mi；**min=1** / max=2 instances（防冷啟動）；request timeout **600s**（`/etf/refresh` 跨境抓價偶超 300s，2026-07-01 調高）；允許未驗證存取 |
| 報表服務 | **Cloud Run** | 服務名 `savestock-report`（Django）；**min=0**（次要工具，省成本）；允許未驗證存取 |
| 資料庫 | **Neon PostgreSQL（免費方案）** | 主機名見 Secret Manager（不公開）；0.5GB；AWS Singapore（Cloud SQL 已於 2026-06-11 刪除） |
| 容器倉庫 | **Artifact Registry** | `savestock-repo`（Docker 格式）；images：`savestock-api`、`savestock-report` |
| 容器建置 | **Cloud Build** | 遠端建置（本機未裝 Docker）；`savestock-api` 用 `cloudbuild-api.yaml`、`savestock-report` 用 `cloudbuild.yaml`，**皆以 repo root 為 context**（納入共用的 `backend/core` 與 `etl/`） |
| 排程 | **Cloud Scheduler** | `savestock-etl-daily`（週一至五 15:00，觸發 `/stocks/refresh`）；`savestock-etf-daily`（週一至五 15:30，觸發 `/etf/refresh`，attempt-deadline 900s） |

* **正式 API 網址**：`https://savestock-api-62102931839.asia-east1.run.app`
* **報表服務網址**：`https://savestock-report-62102931839.asia-east1.run.app`（`/report?d=...` 報表、`/admin` 管理）
* **前端網址**：`https://savestock.netlify.app`（Flutter Web，Netlify 靜態托管）
* **DB 連線**：Cloud Run 透過標準 TCP + SSL 連 Neon，`DATABASE_URL` 由 **GCP Secret Manager**（`savestock-db-url` version 4）注入（`--set-secrets`），不寫入環境變數明文。報表服務另注入 `django-secret-key` secret。
* **Django Admin**：`savestock-report` 的 Django 自有表（auth/session/admin）以 Cloud Run Job 跑 `migrate` 建於 Neon（附加、不影響既有表）；superuser 帳號 `admin`（密碼不入庫，見私訊／自行重設）。報表本身唯讀，不需 migrate。
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
| 雲端 DB 資料填充（25 檔預設股） | ✅ 完成 |
| Flutter App baseUrl 換雲端 API | ✅ `api_service.dart`、`user_service.dart` 已改 |
| CORS 收斂 | ✅ `allow_origins=["https://savestock.netlify.app"]` |
| Secret Manager（DATABASE_URL） | ✅ `savestock-db-url` version 4（Neon URL）|
| Flutter Web 部署 Netlify | ✅ `https://savestock.netlify.app` |
| 手機端對端驗證 | ✅ 全功能通過 |
| **ETL 自動排程（Cloud Scheduler）** | ✅ **已上線**（`savestock-etl-daily`，週一至五 15:00） |
| **ETF 追蹤模組**（資料層/抓取層/分析層/呈現層） | ✅ **已上線**（2026-07-01，見 [3.5 節](#35-etf-追蹤模組backend-etl-web_django)） |
| **ETF 每日排程（Cloud Scheduler）** | ✅ **已上線**（`savestock-etf-daily`，週一至五 15:30） |

### 7.4 成本提醒

* **資料庫已改用 Neon 免費方案（2026-06-11）**，Cloud SQL 已刪除，DB 費用歸零。
* 試用後預估 **近乎免費**（Cloud Run 低流量近乎免費；Neon 免費方案 0.5GB 足夠）。
* GCP 試用折抵金目前只剩 Cloud Run 計費，消耗極慢。

### 7.5 風險

* `yfinance`（爬 Yahoo）公開/商用可能違反服務條款，上線前須評估合法資料源。
* 訪客 UUID 模式資料綁裝置，換機/重裝遺失。

---

## 8. 關鍵設計決策

| 決策 | 原因 |
| --- | --- |
| 預設股 `Is_Default=1`、自選股 `Is_Default=0` | 避免 lookup 新增股混入預設清單 |
| 股票中文名優先取 TWSE 搜尋快取（批次、穩定），次為即時 mis API，最後才 yfinance 英文 | 即時 mis API 偶爾失敗會退回英文名並寫入 DB；既有英文名於下次更新自動升級為中文 |
| 我的股票開啟用 DB 快取（`fetchWatchlist`） | 開啟速度 <1 秒；資料由 Cloud Scheduler 每日 15:00 自動更新，不需每次爬 yfinance |
| 搜尋快取用 STOCK_DAY_ALL | 涵蓋 ETF；上櫃不在範圍 |
| 債券 ETF（00xxB）不支援 | Yahoo 無資料，顯示明確說明 |
| 新上市 < 24 月股利年化 | 固定 ÷2 會低估新上市股 |
| 清單顯示／排序改用近一年殖利率 | 反映最新配息水準；近2年平均保留於詳情頁作保守參考 |
| 殖利率／股利併計股票股利，配股按面額還原 | 只算現金會大幅低估含配股個股（聯邦銀等）；面額還原為台股配息表慣例、較保守，並於詳情頁加註說明 |
| 股利歷史存 DB（`Dividends` 表，現金/配股分欄）而非每次即時抓 | 詳情頁股利圖讀 DB 快、與價格圖一致，tooltip 可拆解現金／配股；`_fetch_and_upsert` 順手寫入 |
| 殖利率降序排序（清單與自選一致） | refresh 端點亦於回傳前排序 |
| 刪除用「常駐按鈕＋左滑」 | 左滑為觸控手勢，web 滑鼠難觸發 |
| 自訂 ScrollBehavior 加 mouse | 讓 web/桌機滑鼠可拖曳捲動/下拉 |
| 股利試算持股清單存裝置端（shared_preferences），非資料庫 | 一次性試算不需跨裝置同步，省 DB 寫入與容量；與需長期追蹤的「我的股票」（存 DB）明確分工，而非全面不用資料庫 |
| ETF 成分股「先刪後插快照 + 每日 append 歷史」雙表設計 | `ETF_Holdings` 只留最新一份供列表/分析查詢快；`ETF_Holding_History` 累積供權重趨勢折線圖，兩者用途不同不合併 |
| 新增自訂 ETF 時不同步抓收盤價 | 即時抓價會拖慢使用者操作（跨境股尤其慢），改由下次每日 ETL 統一補上 |
| `backend/Dockerfile`／`web_django/Dockerfile` 改以 repo root 為 build context | ETF 端點需 import `etl/` 抓取邏輯；原本以各自子目錄為 context 會漏掉 `etl/`，上線後才發現 `ModuleNotFoundError` |
| `savestock-api` request timeout 提高至 600s | `/etf/refresh` 屬排程觸發、非使用者互動端點，可接受較長回應時間，優先解決跨境抓價偶超時的問題，而非重構成非同步任務 |

---

## 9. 啟動指令速查

```powershell
# 1. 啟動本機 API（開發用）
Start-Process -FilePath "c:\Savestock\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","main:app","--port","8000" -WorkingDirectory "c:\Savestock\backend" -WindowStyle Hidden

# 2. 確認本機 API
Invoke-RestMethod http://localhost:8000/health

# 3. 手動執行本機 ETL
Set-Location C:\Savestock; .venv\Scripts\python.exe etl\fetch_data.py

# 3b. 手動執行本機 ETF ETL
Set-Location C:\Savestock; .venv\Scripts\python.exe etl\fetch_etf.py

# 4. 啟動 Flutter 本機預覽
Set-Location C:\Savestock\frontend; flutter run -d chrome --web-port 5000

# ── 生產部署 ────────────────────────────────────────────────

# 5. 打包 + 部署前端到 Netlify
Set-Location C:\Savestock\frontend; flutter build web --release
netlify deploy --prod --dir=build/web --site=<your-netlify-site-id>

# 6. 部署後端 API 到 Cloud Run（repo root 為 build context，納入 etl/；Google Cloud SDK Shell 執行）
Set-Location C:\Savestock
gcloud builds submit --config cloudbuild-api.yaml .
gcloud run deploy savestock-api --image=asia-east1-docker.pkg.dev/<gcp-project>/savestock-repo/savestock-api:latest --region=asia-east1 --allow-unauthenticated --update-secrets=DATABASE_URL=savestock-db-url:latest

# 6b. 部署 Django 報表服務到 Cloud Run（同樣 repo root context）
gcloud builds submit --config cloudbuild.yaml .
gcloud run deploy savestock-report --image=asia-east1-docker.pkg.dev/<gcp-project>/savestock-repo/savestock-report:latest --region=asia-east1 --allow-unauthenticated --update-secrets=DATABASE_URL=savestock-db-url:latest

# 7. 查 Cloud Run 錯誤 log
# gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=savestock-api AND severity>=ERROR" --project=savestock-app --limit=20 --format="value(timestamp,textPayload)"
```
