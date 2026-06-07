# 專案架構文件：Savestock（長線存股防護系統）

> 最後更新：2026-06-06
> 本文件為專案的單一入口參考：看完即可掌握整體內容與架構。
> 細部待辦與部署決策見 [TODONEXT.md](TODONEXT.md)。

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
| 資料庫 | **SQLite**（開發）／PostgreSQL（生產規劃中） | 透過 SQLAlchemy `DATABASE_URL` 切換 |
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
* 入口 `main.py`（CORS 目前 `*`）、`database.py`（`engine` + `get_db()`，以 `engine.begin()` 自動 commit/rollback）。
* 路由：`routers/stocks.py`、`routers/users.py`。

| Method | 路徑 | 說明 |
| --- | --- | --- |
| GET | `/` `/health` | 歡迎訊息／健康檢查 |
| GET | `/stocks/` | 預設清單（依估算殖利率**降序**） |
| GET | `/stocks/search?q=&limit=` | 模糊搜尋候選（上市＋ETF，上櫃不列） |
| GET | `/stocks/lookup/{id}` | 即時查任意台股（代號或中文名）；自動判斷 `.TW/.TWO`，抓取並寫入 DB |
| GET | `/stocks/{id}` | 單一股票（DB 快照） |
| GET | `/stocks/{id}/prices?days=` | 歷史收盤價（1–365 日） |
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
| `Stock_Master` | `Stock_ID`, `Name`, `Sector`, `Avg_Dividend_2Y`, `Default_Drop_Threshold`, **`Listing_Months`**, `Last_Updated`,（實際 DB 另有 `Is_Default`） |
| `User_Stocks` | `User_ID`, `Stock_ID`, `Status`, `Is_Default`, `Custom_Drop_Threshold` |
| `Daily_Prices` | `Stock_ID`, `Date`, `Close_Price`, `Volume`, `Alert_Flag`, `Alert_Reason` |
| `User_Preferences` | `Push_Enabled`, `Email_Enabled`（推播/郵件，尚未接線） |

> 免費方案自選上限＝**5 檔**（已統一：schema 種子、後端無授權 fallback、前端文案皆為 5）。

### 3.4 前端 Flutter（`frontend/lib/`）
| 檔案 | 角色 |
| --- | --- |
| `main.dart` | 入口；`MaterialApp` + 自訂 `ScrollBehavior`（讓 web/桌機滑鼠可拖曳捲動） |
| `screens/onboarding_screen.dart` | **教學導覽**（首次自動顯示、❓可重看；殖利率→用法→警示→免責） |
| `screens/app_shell.dart` | 底部導覽（預設清單／我的股票）＋首次啟動導覽判斷 |
| `screens/home_screen.dart` | 預設清單、產業篩選 Chip、響應式佈局、下拉刷新、❓教學入口 |
| `screens/my_stocks_screen.dart` | 自選清單、開啟即時刷新、刪除鈕（＋左滑刪除） |
| `screens/add_stock_screen.dart` | 模糊搜尋＋候選清單＋無結果直接查詢＋已追蹤標記 |
| `screens/stock_detail_screen.dart` | 殖利率大字、數據卡（含新上市提示）、折線圖（tooltip 顯示日期）、警示卡 |
| `widgets/stock_card.dart`, `widgets/sector_badge.dart` | 共用股票卡、產業標籤 |
| `services/api_service.dart`, `services/user_service.dart` | API 呼叫層、UUID 與 user_id 本地管理 |
| `models/stock.dart` | `Stock`（含 `listingMonths` / `isNewListing`） |
| `theme/app_theme.dart` | 全域樣式 |

---

## 4. 核心計算邏輯

### 基準股利（年化平均）
* **上市 ≥ 2 年**：近 2 年現金股利合計 ÷ 2（ETL 另計配股）。
* **上市 < 2 年（`Listing_Months` < 24）**：上市迄今全部股利 ÷ 上市年數（年化）；前端標示「上市迄今平均」並提醒涵蓋約 X 個月。

### 殖利率
`估算殖利率 = 基準現金股利 ÷ 最新收盤價 × 100%`。清單與自選皆依此**降序**排列。

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

### ⏳ 待辦
* **P5 生產上線**：見第 7 節與 TODONEXT。
* 釐清免費方案自選上限（種子值不一致）。
* 通知系統接線。

---

## 7. 部署規劃（P5，後期）

* **已定**：Web 優先、訪客 UUID、App 內教學導覽。
* **待決**：後端託管平台（Render / Railway / Fly.io / 自架 VPS 比較表已列於 TODONEXT，由使用者決定）。
* **必做工作**：CORS 收斂、**SQLite→PostgreSQL（schema 需改寫，非僅換連線字串）**、前端正式 API 網址＋HTTPS、ETL 伺服器排程、Flutter Web 打包。
* **風險**：`yfinance`（爬 Yahoo）公開/商用可能違反服務條款，上線前須評估合法資料源；訪客模式資料綁裝置。

---

## 8. 關鍵設計決策

| 決策 | 原因 |
| --- | --- |
| 預設股 `Is_Default=1`、自選股 `Is_Default=0` | 避免 lookup 新增股混入預設清單 |
| 自選股中文名從 TWSE openapi 抓 | yfinance 台股名稱為英文 |
| 我的股票開啟即 `refresh` | 顯示即時資料而非 DB 快照 |
| 搜尋快取用 STOCK_DAY_ALL | 涵蓋 ETF；上櫃不在範圍 |
| 債券 ETF（00xxB）不支援 | Yahoo 無資料，顯示明確說明 |
| 新上市 < 24 月股利年化 | 固定 ÷2 會低估新上市股 |
| 殖利率降序排序（清單與自選一致） | refresh 端點亦於回傳前排序 |
| 刪除用「常駐按鈕＋左滑」 | 左滑為觸控手勢，web 滑鼠難觸發 |
| 自訂 ScrollBehavior 加 mouse | 讓 web/桌機滑鼠可拖曳捲動/下拉 |

---

## 9. 啟動指令速查

```powershell
# 1. 啟動 API
Start-Process -FilePath "c:\Savestock\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","main:app","--port","8000" -WorkingDirectory "c:\Savestock\backend" -WindowStyle Hidden

# 2. 確認 API
Invoke-RestMethod http://localhost:8000/health

# 3. 手動執行 ETL
Set-Location C:\Savestock; .venv\Scripts\python.exe etl\fetch_data.py

# 4. 啟動 Flutter（Web）
Set-Location C:\Savestock\frontend; flutter run -d chrome --web-port 5000
```
