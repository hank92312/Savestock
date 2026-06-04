# Savestock — 後續待辦事項 (TODONEXT)

> 最後更新：2026-06-04
> 目前進度：Phase 1（ETL）✅ Phase 2（API）✅ Phase 3（Flutter）進行中

---

## 當前狀態快照

| 層級 | 狀態 | 說明 |
|------|------|------|
| ETL (`etl/fetch_data.py`) | ✅ 完成 | 14 檔預設股票，產業別警示閾值，每日執行 |
| 資料庫 (`savestock.db`) | ✅ 完成 | SQLite，14 檔資料已寫入，殖利率公式驗證正確 |
| API (`backend/`) | ✅ 完成 | FastAPI，7 支端點，`uvicorn main:app` 啟動 |
| Flutter 首頁 | ✅ 驗收完成 | Chrome 實測正常，14 檔資料顯示、殖利率顏色分級、產業篩選皆正常 |
| Flutter 導覽框架 (`app_shell.dart`) | ✅ 完成 | BottomNavigationBar 兩個分頁：預設清單、我的股票 |
| Flutter 我的股票頁（空頁面） | ✅ 完成 | UUID 初始化 + 空清單引導畫面，等待串接 API |

---

## 下一步待辦（依優先順序）

### ✅ P1 — Flutter 首頁 + 導覽列驗收（已完成）

- [x] 確認 `flutter run -d chrome` 畫面正常顯示 14 檔股票
- [x] 底部導覽列：預設清單 / 我的股票 兩個分頁正常切換
- [x] 殖利率公式驗證：與 yfinance 原始資料比對，數值正確
- [x] 高股息 ETF 7–9%、電信 3–4% 均符合市場實際水準

---

### 🟠 P2 — Flutter 股票詳情頁

**檔案位置**：新增 `frontend/lib/screens/stock_detail_screen.dart`

- [ ] 點擊首頁卡片 → 進入個股詳情頁
- [ ] 顯示內容：
  - 股票名稱、代號、產業
  - 估算殖利率（大字顯示）
  - 近2年平均股利 / 最新收盤價
  - 近30日價格走勢圖（折線圖）
  - 今日警示說明（如有）
- [ ] 折線圖套件：`fl_chart`（需加入 `pubspec.yaml`）
- [ ] 呼叫 API：`GET /stocks/{stock_id}/prices?days=30`

---

### 🟠 P3 — Flutter 我的股票頁（自選清單）

**檔案位置**：新增 `frontend/lib/screens/my_stocks_screen.dart`

- [ ] 底部導覽列（BottomNavigationBar）：「首頁」＋「我的股票」兩個分頁
- [ ] 首次進入 → 自動建立訪客 UUID，呼叫 `POST /users` 取得 user_id，存入 SharedPreferences
- [ ] 顯示用戶自選清單，呼叫 `GET /users/{user_id}/watchlist`
- [ ] 空清單時顯示「尚未加入任何股票」引導畫面
- [ ] 右上角「＋」按鈕 → 跳至加入股票頁

---

### 🟠 P4 — Flutter 加入股票頁（搜尋自選）

**檔案位置**：新增 `frontend/lib/screens/add_stock_screen.dart`

- [ ] 搜尋框輸入股票代號（如 2330）
- [ ] 呼叫 `GET /stocks/{stock_id}` 查詢股票資訊
- [ ] 顯示查詢結果卡片（名稱、殖利率、現價）
- [ ] 確認加入 → `POST /users/{user_id}/watchlist`
- [ ] 超過免費方案上限 → 顯示「已達上限（3 檔自選股）」提示
- [ ] **注意**：目前後端 `Stock_Master` 只有預設 14 檔，用戶搜尋不在清單內的股票會回 404。後續需決定是否開放任意股票搜尋（需擴充 ETL 或改用即時查詢）。

---

### 🟡 P5 — 後端補強

- [ ] **Plan_Configs 數值確認**：資料庫中 `Max_Total_Stocks` 目前 Free=13、Premium=20，這是「總股票數」還是「自選股數」需對齊前端邏輯。建議改為「自選股上限」：Free=3、Premium=10，避免與 14 檔預設混淆。
  ```sql
  UPDATE Plan_Configs SET Max_Total_Stocks = 3 WHERE Tier_Name = 'Free';
  UPDATE Plan_Configs SET Max_Total_Stocks = 10 WHERE Tier_Name = 'Premium_Tier_1';
  ```
- [ ] **ETL 排程**：目前需手動執行 `python etl/fetch_data.py`，需設定 Windows 工作排程器或 cron，於台股收盤後（每日 14:30）自動執行。
- [ ] **Stock_Master.Default_Drop_Threshold 欄位**：Schema 有此欄位但 ETL 未寫入，可考慮在 ETL 的 `save_to_db` 中一併寫入各產業閾值。

---

### 🟡 P6 — 生產環境準備（後期）

- [ ] CORS `allow_origins=["*"]` 改為正式網域
- [ ] SQLite → PostgreSQL 切換（`.env` 中 `DATABASE_URL` 改連線字串即可，schema 已相容）
- [ ] API 部署（Railway / Render / AWS）
- [ ] Flutter 打包：Android APK / iOS IPA / Windows exe

---

## 啟動指令速查

```powershell
# 啟動 API（backend 目錄）
cd c:\Savestock\backend
c:\Savestock\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000

# 執行 ETL（手動抓取最新資料）
cd c:\Savestock
.venv\Scripts\python.exe etl\fetch_data.py

# 啟動 Flutter（frontend 目錄）
cd c:\Savestock\frontend
flutter run -d chrome
```

---

## 關鍵檔案索引

| 檔案 | 說明 |
|------|------|
| `etl/fetch_data.py` | ETL 主程式，TARGET_STOCKS 定義預設 14 檔 |
| `backend/main.py` | FastAPI 入口，掛載 stocks / users 兩個 router |
| `backend/database.py` | SQLAlchemy engine + `get_db()` dependency |
| `backend/routers/stocks.py` | 股票端點：列表、詳情、歷史價格 |
| `backend/routers/users.py` | 用戶端點：建立、自選清單 CRUD |
| `frontend/lib/main.dart` | Flutter 入口，允許四向旋轉 |
| `frontend/lib/screens/home_screen.dart` | 首頁：14 檔清單、產業篩選、響應式佈局 |
| `frontend/lib/widgets/stock_card.dart` | 股票卡片元件（含警示橫幅）|
| `frontend/lib/services/api_service.dart` | API 呼叫層（目前指向 localhost:8000）|
| `database/init_sqlite.sql` | 資料庫初始化 SQL（schema + 初始資料）|
