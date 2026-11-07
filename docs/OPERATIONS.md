# Savestock v2 — 零成本維運與設定手冊 (`OPERATIONS.md`)

> 本手冊說明如何在 5 分鐘內完成 **Cloudflare D1 跨裝置同步**與 **Gmail 通知**的啟用，以及如何關閉舊版 GCP / Netlify 資源以確保永久 \$0 成本。

---

## 1. 本地開發與一鍵更新資料

```powershell
# 1. 執行單元測試（共 22 項核心演算法與商業規則測試）
py -c "import sys; sys.path.insert(0, 'pipeline'); from tests import test_dividend_calc, test_etf_analytics, test_metrics; [getattr(m, f)() for m in (test_dividend_calc, test_etf_analytics, test_metrics) for f in dir(m) if f.startswith('test_')]; print('ALL 22 TESTS PASSED')"

# 2. 抓取全市場最新資料並產生靜態 JSON
py -m pipeline.build.run_pipeline --out web/public/data --fast

# 3. 啟動前端本地預覽 (Vite)
cd web
npm run dev
```

---

## 2. 啟用 Cloudflare Workers + D1 跨裝置同步（完全免費、免綁信用卡）

你在昨日已建立 Cloudflare 帳號，只需在 `worker/` 目錄執行以下 4 行指令即可部署完成：

```powershell
cd D:\Savestock\worker
npm install

# 1. 登入 Cloudflare 帳號（會開啟瀏覽器授權）
npx wrangler login

# 2. 建立免費 D1 資料庫（執行後會印出 database_id，請貼回 worker/wrangler.toml 的 database_id）
npx wrangler d1 create savestock-db

# 3. 初始化資料表與預設邀請碼 (HANK-ADMIN)
npx wrangler d1 execute savestock-db --remote --file=./schema.sql

# 4. 部署 Worker 上線（會印出 https://savestock-sync.<你的子網域>.workers.dev）
npx wrangler deploy
```

### PC 與外出手機配對步驟：
1. 在 PC 打開 `https://hank92312.github.io/Savestock/#/settings`。
2. 在「Cloudflare Worker 同步服務網址」填入剛才部署出的 `https://savestock-sync.<你的子網域>.workers.dev`，邀請碼填 `HANK-ADMIN`，點擊「**啟用雲端同步**」。
3. 點擊「**📱 產生手機配對 QR Code**」，用手機相機掃描畫面上的 QR Code（或在手機輸入 6 位數配對碼），手機與 PC 即完成綁定，之後任何一方修改持股，另一方打開分頁即自動同步！

---

## 3. 啟用 Gmail 盤後推播通知（使用 `hank92312@gmail.com`）

1. 前往 Google 帳戶安全性設定 → 開啟「兩步驟驗證」→ 搜尋「**應用程式密碼 (App Passwords)**」。
2. 建立一組應用程式密碼（名稱可填 `Savestock`），複製產生的 16 碼密碼。
3. 前往 GitHub Repo (`hank92312/Savestock`) → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**：
   - `GMAIL_USER`：`hank92312@gmail.com`
   - `GMAIL_APP_PASSWORD`：貼上剛才的 16 碼應用程式密碼
   - `NOTIFY_EMAIL`：`hank92312@gmail.com`
   - （選填）`FINMIND_TOKEN`：你在 FinMind 免費註冊取得的 Token（可將歷史回補速率上限提高至 600 次/小時）

---

## 4. 關閉舊版雲端資源（避免任何潛在帳單）

舊版程式碼已封存於 Git tag `v1-legacy`（隨時可透過 `git checkout v1-legacy` 查閱）。
- **GCP (`savestock-app`)**：可至 Google Cloud Console → Project Settings → **Shut down (刪除專案)**，徹底清除 Cloud Run、Artifact Registry、Cloud Scheduler 與 Secret Manager。
- **Netlify (`savestock.netlify.app`)**：已由 GitHub Pages (`https://hank92312.github.io/Savestock/`) 完整取代，可直接於 Netlify 後台刪除站台。

