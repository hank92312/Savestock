# Savestock 交接報告（2026-06-15）

> 單一架構入口仍是 [APP.md](APP.md)；本檔聚焦「本次 session 做了什麼、現況、待驗證、如何接手」。
> 待辦與部署指令見 [TODONEXT.md](TODONEXT.md)。

---

## 1. 本次 session 摘要（2026-06-15）

兩大塊工作：

### A. 既有問題修復（早段）
1. **網頁慢載修復**：
   - 「我的股票」開啟改用 DB 快取（`fetchWatchlist`，<1 秒），🔄 按鈕才即時抓 yfinance。
   - `/stocks/lookup/` DB 有 5 日內資料直接回傳（~300ms），不再每次爬。
2. **Neon 閒置連線 SSL 斷線**：`backend/database.py` 加 `pool_pre_ping=True, pool_recycle=300`。
3. **股票卡片**：現價下方顯示「截至 MM/DD」資料日期。
4. **持股輸入持久化說明**：試算持股已存裝置端、重開自動回填（`PortfolioService`）。

### B. 新功能：個人年度股利計算（三階段，全部上線）
| Phase | 內容 | 關鍵檔案 |
|---|---|---|
| 1 | 共用計算模組 + FastAPI 端點 + Flutter 試算分頁 | `backend/core/dividend_calc.py`、`backend/routers/portfolio.py`、`frontend/lib/screens/dividend_calc_screen.dart` |
| 2 | Django 報表服務（可分享/可列印）+ Django Admin | `web_django/`（整個專案） |
| 3 | 證交所 OpenAPI 已公告配息（年配股用實際值） | `backend/core/twse_dividends.py` |

---

## 2. 股利試算功能 — 設計重點（接手必讀）

### 三層估算口徑（優先序，在 `core/dividend_calc.py`）
1. **已公告**（`source=announced`）：年配股今年正式公告之全年配息，來源證交所 OpenAPI `t187ap45_L`（`core/twse_dividends.py`，全市場一次抓、快取 12h、失敗回退估算）。實際值、非估算。
2. **近1年 `Dividend_1Y`（滾動 12 月）／近5年平均 `Avg_Dividend_5Y`**：未公告時依使用者選的基準估算。

### 為何這樣設計（重要判斷，勿回退）
- **季配股不用「今年已除息」當全年值**：年中只除息部分季別，會嚴重低估（台積電曾估成實際的 30%）。改用滾動近1年。
- **季配股不用「已公告」**：年中後續季別尚未開會決議，無法得知全年；證交所資料只有「年度」列＝年配股。季配股交回滾動估算。
- **影響較大個股**：只列「估算（非已公告）」個股，因已公告為確定值。

### 資料流
- 持股存**裝置端**（`PortfolioService` / shared_preferences），不入庫。
- 計算邏輯**單一來源** `core/`，FastAPI（App）與 Django（報表）共同 import，避免重蹈 ETL/後端股利邏輯各自維護的覆轍。
- 報表 = 自帶資料的網址 `/report?d=<base64持股>`，無生產 schema 變更即可分享。

---

## 3. 生產環境現況

| 資源 | 服務/網址 | 狀態 |
|---|---|---|
| 前端 | https://savestock.netlify.app | ✅ 含「股利試算」分頁 |
| 後端 API | `savestock-api`（Cloud Run，min=1）<br>https://savestock-api-62102931839.asia-east1.run.app | ✅ revision 00021，含 Phase 3 |
| 報表服務 | `savestock-report`（Cloud Run，min=0）<br>https://savestock-report-62102931839.asia-east1.run.app | ✅ revision 00004，含 Phase 3 |
| 資料庫 | Neon PostgreSQL（免費） | ✅ 已含 Django 自有表（migrate 過） |
| ETL 排程 | Cloud Scheduler `savestock-etl-daily`（週一至五 15:00） | ✅ |
| Secrets | `savestock-db-url`、`django-secret-key` | ✅ |

### Django Admin
- 網址：`<報表服務>/admin`，帳號 `admin`。
- **密碼不在 git／任何檔案**——於 2026-06-15 對話中提供，建議登入後重設（或重跑 createsuperuser）。

---

## 4. ⏳ 待你驗證（新 session 回報用）

App（savestock.netlify.app，**Ctrl+Shift+R 兩次**換新版）：
1. **股利試算分頁**：新增持股（搜尋→選股→股數，含零股）→ 計算 → 看總額卡 + 各檔明細 + 提示窗。
2. **已公告 vs 估算**：加一檔**年配股**（如中華電 2412、中鋼 2002）→ 該檔應顯示「已公告」（綠字）、用實際公告值；季配股（0056、台積電）顯示估算。
3. **持股持久化**：加幾筆 → 完全關閉分頁再開 → 持股應還在。
4. **網頁報表**：試算結果點「產生可分享網頁報表」→ 開新分頁，年配股顯示「已公告」綠標、可列印。
5. **Django Admin**：`<報表服務>/admin` 用 admin 登入，可查 Stock_Master。

---

## 5. 已知限制 / 待辦

- **上櫃（.TWO）年配股**：證交所 `t187ap45_L` 只含上市，上櫃無已公告資料、走估算。
- **獨立任務（已開卡）**：台積電 2330 `Dividend_1Y` 在 Neon 約 26.5，比實際配息（~18–20）偏高，疑似配股換算或重複計入 bug——屬既有 ETL 資料問題，與本功能無關。查 `_dividend_1y` / `_total_div_series`（ETL 與後端兩邊同步）。
- 通知系統接線（`User_Preferences` 已備欄位）。

---

## 6. 部署指令速查

```powershell
# 前端 → Netlify
cd C:\Savestock\frontend; flutter build web --release
cd C:\Savestock\frontend\build\web
netlify deploy --prod --dir=. --site=ebec3bc6-8ea5-4131-98b0-e08c54aaaac8

# 後端 FastAPI → Cloud Run（build 後 deploy）
gcloud builds submit "C:\Savestock\backend" --tag=asia-east1-docker.pkg.dev/savestock-app/savestock-repo/savestock-api:latest --project=savestock-app
gcloud run deploy savestock-api --image=asia-east1-docker.pkg.dev/savestock-app/savestock-repo/savestock-api:latest --region=asia-east1 --project=savestock-app

# Django 報表 → Cloud Run（root context 納入 backend/core）
gcloud builds submit --config cloudbuild.yaml --project=savestock-app .
gcloud run deploy savestock-report --image=asia-east1-docker.pkg.dev/savestock-app/savestock-repo/savestock-report:latest --region=asia-east1 --project=savestock-app

# Django migrate（Cloud Run Job，secret 注入；Admin 需要時）
# 既有 setup job 已刪；如需重建見對話紀錄或用 gcloud run jobs create ... --command python --args "manage.py,migrate"

# 本機測試
cd C:\Savestock; .venv\Scripts\python.exe -m pytest backend\tests\ -q   # 7 tests
cd C:\Savestock\web_django; $env:DATABASE_URL=""; ..\.venv\Scripts\python.exe manage.py runserver 8002 --noreload
```

---

## 7. 本次 session 提交紀錄（main，由舊到新）

```
d0d9340  fix: Neon 閒置連線 pool_pre_ping
6c4fba0  docs: ETL 排程完成、成本更新
0fdbd48  docs: 明日驗證項目
6780680  perf: 我的股票/搜尋頁慢載修復
81609dc  fix+feat: 並行抓取 + 股票卡資料日期
2121ced  docs: APP.md 更新
d5321b2  feat(portfolio): Phase 1 後端
f49f6d3  feat(portfolio): Phase 1 前端
2f825ce  docs: APP.md Phase 1
8d3d1dd  feat(web_django): Phase 2 Django 報表 + Admin
c7bf09b  feat(portfolio): Phase 2 前端報表按鈕
e0cfd27  docs: APP.md Phase 2
347dc1a  feat(portfolio): Phase 3 證交所已公告配息
0593233  docs: APP.md Phase 3
```
