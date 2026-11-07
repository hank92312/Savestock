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

## 2. Cloudflare Workers + D1 跨裝置同步（已正式上線）

- **雲端同步 API 網址**：`https://savestock-sync.hank92312.workers.dev`
- **D1 Database ID**：`8048270a-a909-4a75-a44a-45829f3bfd8c`
- **預設邀請碼**：`HANK-ADMIN`

### 手機 ↔ 電腦雙向配對與朋友獨立帳號步驟：
1. **初次設定（手機或電腦皆可）**：
   - 打開 `https://hank92312.github.io/Savestock/#/settings`。
   - 填寫「暱稱」與「接收通知 Email」，邀請碼維持預設 `HANK-ADMIN`，點擊「**一鍵啟用雲端同步**」。
   - **朋友使用**：每位朋友只要填寫他自己的 Email 並點擊啟用，系統會在 D1 自動分配各自獨立的帳戶與持股記錄，彼此互不干擾且各自接收盤後 Email。
2. **第二台裝置同步（手機配電腦 或 電腦配手機）**：
   - **方法 A**：在第二台裝置輸入同一個 Email 點擊「一鍵啟用雲端同步」，系統自動識別並下載現有持股。
   - **方法 B**：在第一台裝置點擊「**📱 產生跨裝置配對碼 / QR Code**」，在第二台裝置輸入 6 位數配對碼（或掃描 QR Code）即可完成綁定！

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

