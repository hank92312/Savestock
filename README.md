<h1 align="center">📈 Savestock v2 — 長線存股健康防護與 ETF 智慧追蹤系統</h1>

<p align="center">
  <b>全市場靜態極速架構（上市 + 上櫃 + ETF 共 2,370+ 檔）‧ 永久 $0 維護成本 ‧ PC / 手機跨裝置雲端同步</b><br/>
  🔗 <b>線上正式站（GitHub Pages）</b>：<a href="https://hank92312.github.io/Savestock/">https://hank92312.github.io/Savestock/</a>
</p>

---

## ✨ v2 全面升級重點

1. **⚡ 查詢速度極致優化（< 50ms 零等待）**
   - 徹底移除會冷啟動與 500 斷線的傳統雲端伺服器，改由每日盤後自動化資料管線（`pipeline/`）一次向**臺灣證券交易所（TWSE）**、**櫃買中心（TPEx）**、**集保結算所（TDCC）**與**公開財經資料庫**抓取全市場 **2,370+ 檔**（含上市、上櫃、高股息/市值/科技AI/債券/海外 ETF）完整數據並預先算好所有指標，輸出為靜態 JSON 部署至 GitHub Pages CDN。
   - 前端改寫為 **React 19 + TypeScript + Vite PWA**（首屏 gzip 僅 ~100 KB），搭配 Service Worker `StaleWhileRevalidate` 快取，手機與電腦開啟瞬間呈現。
2. **💰 永久 $0 成本維護（Cloudflare Workers + D1 跨裝置同步）**
   - 支援 **PC ↔ 外出手機瀏覽器即時同步**：在 PC 點擊「產生手機配對 QR Code」，手機掃描即完成綁定（基於免費 Cloudflare Workers + D1 SQLite，免綁信用卡）。
   - 離線優先（IndexedDB 本地副本 + 雲端自動樂觀鎖合併）。
3. **🎨 存股與 ETF 同款溫潤自然介面**
   - 採用低對比暖紙色（Warm Paper `#F7F5F0`）與柔和夜間深色雙主題，存股追蹤與 ETF 追蹤共享同一套版面、卡片與詳情頁。
   - 整合「持有中」與「觀察清單」（股數設為 0 即為純觀察），不再分拆兩套系統。
4. **🩺 更詳盡的投資參考與 ETF 完整成分股**
   - **存股健康診斷評分（0–100 分）**：綜合股利品質（連續配息年數、配息穩定度、盈餘配發率）、殖利率法三段價格帶（便宜 6% / 合理 5% / 昂貴 4%）、月營收 YoY、TDCC 千張大戶持股比例與年化波動度，自動列出白話加減分理由。
   - **自適應暴跌與下跌爆量防護**：結合個股近 60 日波動率與產業分級地板，僅在異常重挫或「下跌爆量」時觸發紅色警示。
   - **年度股利試算 + 二代健保補充保費（2.11%）+ 12 個月現金流月曆 + 目標月領與複利模擬**。
   - **ETF 完整 30～60 檔成分股與穿透分析**：突破舊版僅前 10 大成分股限制，新增**我的組合穿透持股（Look-through Exposure）**、**ETF 兩兩重疊度矩陣**、機構共識股、隱藏強勢股、權重熱力圖與共識動能三因子評分。
5. **✉️ 盤後 Email 自動摘要推播**
   - 每日盤後由 GitHub Actions 透過 Gmail SMTP 自動寄發異常波動警示、進入便宜區高分股與近期除權息預告提醒。

---

## 📁 專案結構

```text
Savestock/
├── web/                     # React 19 + TypeScript + Vite PWA 前端
│   ├── src/
│   │   ├── pages/           # 總覽 / 我的持股 / 探索存股 / ETF 追蹤 / 證券詳情 / 設定同步
│   │   ├── components/      # 共用證券卡片、SVG 價格帶折線圖、月度現金流圖表
│   │   ├── store.ts         # IndexedDB 離線儲存與 Cloudflare D1 跨裝置同步引擎
│   │   └── calc.ts          # 股利試算、二代健保補充保費、穿透持股與複利模擬
├── pipeline/                # Python 全市場靜態資料管線
│   ├── sources/             # TWSE / TPEx / TDCC / MoneyDJ / FinMind 官方與公開資料抓取器
│   ├── core/                # 股利口徑、健康評分、自適應警示、ETF 四大分析純函式層
│   ├── build/               # 靜態 JSON 建置器 (run_pipeline.py)
│   ├── notify/              # Gmail SMTP 個人化盤後摘要與週報寄送 (send_digest.py)
│   └── tests/               # 22 項核心單元測試
├── worker/                  # Cloudflare Worker + D1 跨裝置同步與 QR 配對服務
└── docs/                    # 系統文件
    ├── DATA_SOURCES.md      # P0 全市場公開資料來源實測報告
    ├── DATA_CONTRACT.md     # 靜態 JSON 規格書
    └── OPERATIONS.md        # Cloudflare D1 / Gmail 啟用與維運手冊
```

> 舊版（Flutter + FastAPI + Django）已完整封存於 Git tag [`v1-legacy`](https://github.com/hank92312/Savestock/tree/v1-legacy)。
