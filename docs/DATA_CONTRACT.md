# Savestock v2 — 靜態資料契約規格書 (`DATA_CONTRACT.md`)

> 本文件定義 `pipeline/` 每日產出、並由 `web/` 前端讀取的所有靜態 JSON 檔案格式。
> 所有檔案均部署於 GitHub Pages `/Savestock/data/` 目錄下，前端透過 `meta.json` 的 `version` 作為 cache-busting query string（`?v={version}`）。

---

## 1. 檔案總覽

| 路徑 | 用途 | 載入時機 |
|---|---|---|
| `data/meta.json` | 資料基準日、版本號、各資料源更新狀態 | App 啟動時必讀（`cache: "no-store"`） |
| `data/universe.json` | 全市場上市 + 上櫃 + ETF 索引（供前端 <50ms 即時搜尋） | App 啟動後背景載入並快取於 IndexedDB |
| `data/screener.json` | 全市場個股與 ETF 摘要指標、健康分數、價格帶、今日警示 | 進入「總覽 / 探索 / 我的持股」時讀取 |
| `data/calendar.json` | 近期與未來 60 日除權息預告、發放日、精選清單重要事件 | 進入「總覽」時讀取 |
| `data/s/{code}.json` | 單一證券（個股或 ETF）完整詳情（價格、股利、估值、基本面、籌碼、風險、評分明細） | 點進「證券詳情頁」時依代號載入（如 `data/s/2412.json`） |
| `data/etf/index.json` | ETF 六大分群清單、規模、費用率、折溢價、含息報酬、配息頻率 | 進入「ETF」頁時讀取 |
| `data/etf/analytics.json` | 跨 ETF 完整成分股表、重疊度矩陣、機構共識股、隱藏強勢股、熱力圖、共識動能評分 | 進入「ETF 分析」或計算「我的組合穿透持股」時讀取 |

> **代號慣例**：台股上市與上櫃一律使用**純代號**作為主鍵（如 `"2412"`、`"0056"`、`"00679B"`），並在 `market` 欄位標註 `"TWSE"`（上市）或 `"TPEX"`（上櫃）；海外美股成分股使用 `"AAPL.US"`。為了相容舊版測試與資料，計算函式亦支援帶 `.TW` / `.TWO` 後綴。

---

## 2. 各檔案 Schema 定義

### 2.1 `data/meta.json`
```json
{
  "version": "20261106-1530",
  "marketDate": "2026-11-06",
  "updatedAt": "2026-11-06T15:35:12+08:00",
  "counts": {
    "twse": 1025,
    "tpex": 845,
    "etf": 258,
    "alertsToday": 14
  },
  "sources": {
    "twseDaily": "ok",
    "tpexDaily": "ok",
    "dividends": "ok",
    "etfHoldings": "ok",
    "tdccDate": "2026-11-01"
  }
}
```

### 2.2 `data/universe.json`
```json
{
  "version": "20261106-1530",
  "items": [
    {
      "code": "2412",
      "name": "中華電",
      "market": "TWSE",
      "type": "stock",
      "sector": "通信網路業",
      "curated": true
    },
    {
      "code": "0056",
      "name": "元大高股息",
      "market": "TWSE",
      "type": "etf",
      "sector": "高股息ETF",
      "etfGroup": "high_dividend",
      "curated": true
    }
  ]
}
```

### 2.3 `data/screener.json`
供探索篩選器、精選 25 檔清單、「我的持股」即時估值與年度股利試算使用：
```json
{
  "version": "20261106-1530",
  "marketDate": "2026-11-06",
  "items": {
    "2412": {
      "code": "2412",
      "name": "中華電",
      "market": "TWSE",
      "type": "stock",
      "sector": "通信網路業",
      "curated": true,
      "hasDetail": true,
      "price": 123.5,
      "change": -0.5,
      "changePct": -0.4,
      "volume": 8420,
      "yield1y": 4.21,
      "yield2y": 4.05,
      "yield5y": 3.92,
      "div1y": 5.2,
      "div2y": 5.0,
      "div5y": 4.84,
      "paidThisYear": 5.2,
      "announcedDiv": 5.2,
      "pe": 25.4,
      "pb": 2.45,
      "pePercentile5y": 62,
      "yieldPercentile5y": 71,
      "consecDivYears": 25,
      "payoutRatio": 98.5,
      "fillRate5y": 100.0,
      "avgFillDays": 18,
      "revYoY": 4.2,
      "epsTtm": 4.86,
      "roe": 9.8,
      "priceBands": {
        "cheap": 80.67,
        "fair": 96.8,
        "expensive": 121.0,
        "zone": "expensive"
      },
      "score": {
        "total": 82,
        "grade": "A",
        "reasons": ["連續配息 25 年", "5 次除息 100% 填息", "營運現金流穩健"]
      },
      "alert": {
        "flag": false,
        "reasons": []
      }
    }
  }
}
```

### 2.4 `data/calendar.json`
```json
{
  "version": "20261106-1530",
  "events": [
    {
      "date": "2026-11-11",
      "code": "0056",
      "name": "元大高股息",
      "eventType": "pay_date",
      "cashDiv": 1.07,
      "stockDiv": 0.0,
      "note": "季配息發放日"
    },
    {
      "date": "2026-11-18",
      "code": "00878",
      "name": "國泰永續高股息",
      "eventType": "ex_date",
      "cashDiv": 0.55,
      "stockDiv": 0.0,
      "payDate": "2026-12-12",
      "note": "除息交易日"
    }
  ]
}
```

### 2.5 `data/s/{code}.json`（個股與 ETF 通用詳情格式）
```json
{
  "code": "2412",
  "name": "中華電",
  "market": "TWSE",
  "type": "stock",
  "sector": "通信網路業",
  "updatedAt": "2026-11-06",
  "summary": { /* 與 screener.json 單筆相同 */ },
  "scoreBreakdown": {
    "total": 82,
    "grade": "A",
    "dimensions": [
      { "key": "dividend", "label": "股利品質", "score": 31, "max": 35 },
      { "key": "valuation", "label": "估值位階", "score": 16, "max": 25 },
      { "key": "fundamentals", "label": "基本面趨勢", "score": 22, "max": 25 },
      { "key": "chips_risk", "label": "籌碼與風險", "score": 13, "max": 15 }
    ],
    "positives": ["連續配息 25 年，穩定度極高", "近 5 次除息 100% 完成填息（平均 18 天）", "年化波動度僅 11.2%，防禦性強"],
    "cautions": ["目前股價位於殖利率法偏高區間（> 121 元）"]
  },
  "prices": [
    { "date": "2026-11-06", "close": 123.5, "volume": 8420, "alert": "" }
  ],
  "dividends": [
    {
      "year": 2026,
      "exDate": "2026-07-04",
      "payDate": "2026-08-08",
      "cash": 5.2,
      "stock": 0.0,
      "total": 5.2,
      "fillDays": 14,
      "filled": true
    }
  ],
  "valuationHistory": [
    { "date": "2026-11-06", "pe": 25.4, "pb": 2.45, "yield": 4.21 }
  ],
  "fundamentals": {
    "monthlyRevenue": [
      { "ym": "2026-10", "rev": 20150, "yoy": 4.2, "mom": 1.8 }
    ],
    "quarterlyEps": [
      { "yq": "2026Q3", "eps": 1.24, "grossMargin": 36.5, "opMargin": 21.4, "roe": 2.45 }
    ],
    "debtRatio": 24.8
  },
  "chips": {
    "instiNet5d": 3420,
    "instiNet20d": 12800,
    "foreignHoldPct": 16.4,
    "marginUsagePct": 1.2,
    "largeHolder1000Pct": 78.4,
    "largeHolderDiff1w": 0.15,
    "shareholdersCount": 312450,
    "history": [
      { "date": "2026-11-06", "foreign": 850, "trust": 320, "dealer": -45, "marginBal": 1240 }
    ]
  },
  "risk": {
    "volatility1y": 11.2,
    "maxDrawdown1y": -6.4,
    "maxDrawdown3y": -11.8,
    "adaptiveDropThreshold": 2.5
  },
  "etfInfo": null
}
```
> 若 `type === "etf"`，`etfInfo` 欄位會包含：
> - `nav`（最新淨值）、`premiumDiscountPct`（折溢價%）、`expenseRatioPct`（總管理費用率%）、`aumMillions`（規模百萬台幣）、`holdersCount`（受益人數）、`divFrequency`（季配/月配/半年配/年配）、`issuer`（發行投信）、`trackingIndex`（追蹤指數）
> - `returns`：`{ "m1": -2.1, "m3": 1.5, "m6": 12.4, "y1": 28.5, "y3": 68.2 }`（含息總報酬%）
> - `navHistory`：近 30 日 `[{ "date", "nav", "price", "discountPct" }]`
> - `holdings`：完整成分股清單 `[{ "code", "name", "weight", "shares", "changeType", "weightDiff" }]`
> - `completeness`：`"full"`（完整持股）或 `"top10"`（前十大）
