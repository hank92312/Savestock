# Savestock v2 — 資料來源實測與選型報告 (`DATA_SOURCES.md`)

> 實測日期：2026-11-07（P0 階段）
> 目標：全部免費、免爬蟲反制風險、一次拿全市場（或單頁結構化抓取），徹底擺脫對 `yfinance` 逐檔請求的依賴。

---

## 1. 全市場個股與 ETF 每日行情 / 估值 / 基本面 / 籌碼

### 1.1 上市（TWSE）與上櫃（TPEx）每日批次 API 對照表

| 資料類別 | 上市（TWSE）端點與實測結果 | 上櫃（TPEx）端點與實測結果 | 呼叫次數 / 頻率 |
|---|---|---|---|
| **證券主檔與產業別** | `GET https://openapi.twse.com.tw/v1/opendata/t187ap03_L`<br/>✅ 200 OK（1.3 MB，含公司簡稱、產業代碼） | `GET https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O`<br/>✅ 200 OK（1.0 MB，含簡稱、產業代碼）<br/>備援：FinMind `TaiwanStockInfo`（605 KB，一次回傳上市+上櫃+ETF 中文產業名） | 每日 1 次 |
| **每日收盤價與成交量** | `GET https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL`<br/>✅ 200 OK（1,389 筆，含普通股與上市 ETF） | `GET https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes`<br/>✅ 200 OK（含上櫃股票與債券 ETF 如 `00679B`） | 每日 15:30 1 次 |
| **本益比 / 殖利率 / 淨值比** | `GET https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL`<br/>✅ 200 OK（1,087 筆，`PEratio` / `DividendYield` / `PBratio`） | `GET https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis`<br/>✅ 200 OK（891 筆，`PriceEarningRatio` / `YieldRatio` / `PriceBookRatio`） | 每日 15:30 1 次 |
| **預告除權息日程表（行事曆）** | `GET https://www.twse.com.tw/rwd/zh/exRight/TWT48U?response=json`<br/>✅ 200 OK（未來除權息日期、現金股利、無償配股率） | `GET https://www.tpex.org.tw/openapi/v1/tpex_exright_prepost`<br/>✅ 200 OK（67 筆，含上櫃股票與上櫃債券 ETF 除息預告） | 每日 15:30 1 次 |
| **歷史除權息結果（計算填息天數）** | `GET https://www.twse.com.tw/rwd/zh/exRight/TWT49U?response=json&startDate=YYYYMMDD&endDate=YYYYMMDD`<br/>✅ 200 OK（含除息前收盤價、除息參考價、現金股利） | `GET https://www.tpex.org.tw/openapi/v1/tpex_exright_daily`<br/>✅ 200 OK（當日除權息結果） | 每日 15:30 1 次 |
| **董事會 / 股東會已公告股利** | `GET https://openapi.twse.com.tw/v1/opendata/t187ap45_L`<br/>✅ 200 OK（1,248 筆，含盈餘/公積現金與配股、決議進度） | `GET https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap39_O`<br/>✅ 200 OK（2,483 筆，上櫃股利分派情形） | 每日 15:30 1 次 |
| **月營收（YoY / MoM）** | `GET https://openapi.twse.com.tw/v1/opendata/t187ap05_L`<br/>✅ 200 OK（1,088 筆，含當月、上月、去年同月營收與增減%） | `GET https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O`<br/>✅ 200 OK（893 筆，欄位與上市完全相同） | 每日 21:30 1 次 |
| **季報損益表（EPS / 毛利 / 營益 / 淨利）** | `GET https://openapi.twse.com.tw/v1/opendata/t187ap14_L`（全產業 EPS）<br/>`GET https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci`（一般業損益表，另有 `_basi`/`_fh`/`_ins`/`_bd`/`_mim`）<br/>✅ 200 OK | `GET https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap14_O`（上櫃 EPS）<br/>`GET https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap06_O_ci`（上櫃損益表）<br/>✅ 200 OK | 每日 21:30 1 次 |
| **季報資產負債表（負債比 / 淨值 / ROE）** | `GET https://openapi.twse.com.tw/v1/opendata/t187ap07_L_ci`（及金融/金控等分業表）<br/>✅ 200 OK | `GET https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap07_O_ci`（及分業表）<br/>✅ 200 OK | 每日 21:30 1 次 |
| **三大法人買賣超** | `GET https://www.twse.com.tw/rwd/zh/fund/T86?response=json&selectType=ALL`<br/>✅ 200 OK（外資、投信、自營商買賣超股數） | `GET https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading`<br/>✅ 200 OK（923 筆） | 每日 21:30 1 次 |
| **融資融券餘額與使用率** | `GET https://openapi.twse.com.tw/v1/exchangeReport/MI_MARGN`<br/>✅ 200 OK（1,306 筆，含今日餘額與限額） | `GET https://www.tpex.org.tw/openapi/v1/tpex_mainboard_margin_balance`<br/>✅ 200 OK（919 筆） | 每日 21:30 1 次 |
| **集保大戶股權分散表（千張大戶比例）** | `GET https://smart.tdcc.com.tw/opendata/getOD.ashx?id=1-5`<br/>✅ 200 OK（CSV 2.3 MB，約 7 萬列，一次涵蓋全市場上市+上櫃 1～15 級距） | 同左（同一份 CSV 涵蓋上市與上櫃） | 每週六 09:00 1 次 |

> **實測發現與踩坑紀錄**：
> 1. 原本規劃的 `openapi.twse.com.tw/v1/exchangeReport/TWT49U_ALL` 與 `tpex.org.tw/openapi/v1/mopsfin_t187ap45_O` 會回傳 HTML 錯誤頁，實測後已替換為實際可用的 `/rwd/zh/exRight/TWT49U` 與 `/openapi/v1/mopsfin_t187ap39_O`。
> 2. TDCC 集保開放資料 `id=1-5` 免 Token、免爬蟲，直接給全市場 CSV，每週六抓一次即可算出每檔股票的「400 張 / 1000 張大戶持股比例」與「總股東人數變化」。

---

## 2. ETF 完整成分股與專屬資訊（重大突破）

舊版最大的痛點是 `yfinance` 只給 **Top 10 成分股**，且完全沒有債券 ETF 資料。P0 實測找到**完整、免費、結構化**的官方與公開來源組合：

| 資料項目 | 主要來源（實測通過） | 備援來源 |
|---|---|---|
| **ETF 完整成分股與權重（30～60+ 檔）** | **MoneyDJ `Basic0007B.xdjhtm?etfid={代碼}`**<br/>✅ 實測 `0056.TW` 抓回完整 **51 筆**、`00878.TW` **30 筆**、`00919.TW` **41 筆**、`00851.TW`（含美股）**59 筆**、`00679B.TW`（美債 ETF）**40 筆**！HTML 表格結構單純（`table.datalist`），必須強制指定 `r.encoding = "utf-8"`。 | `Basic0007.xdjhtm`（前 10 大 + 產業配置比例） / `yfinance` |
| **全市場 ETF 即時淨值与折溢價** | **證交所基本市況 `https://mis.twse.com.tw/stock/data/all_etf.txt`**<br/>✅ 200 OK（61 KB JSON，一次回傳全市場上市櫃 ETF 的市價 `e`、預估淨值 `f`、折溢價% `g`、前日淨值 `h`）<br/>搭配 **MoneyDJ `Basic0003.xdjhtm`** 可取近 30 日歷史淨值與折溢價走勢。 | MoneyDJ `Basic0004` |
| **ETF 總費用率、規模、受益人數、配息頻率、追蹤指數** | **證交所 e 添富 `https://www.twse.com.tw/zh/ETFortune/ajaxProductsResult`**（246 檔 ETF 規模 `totalAv`、受益人數 `holders`、發行投信、追蹤指數）<br/>＋ **MoneyDJ `Basic0004.xdjhtm`**（總管理費用率%、配息頻率、成立日、月均折溢價、年化標準差） | TWSE / TPEx 主檔 |
| **ETF 歷次配息明細（含除息日、發放日、年化配息率）** | **MoneyDJ `Basic0005.xdjhtm?etfid={代碼}`**<br/>✅ 200 OK（含配息基準日、除息日、發放日、每單位配息金額、當期年化配息率%） | TWSE `TWT49U` / FinMind |
| **ETF 含息總報酬（市價 / 淨值 1M / 3M / 6M / 1Y / 3Y / 5Y）** | **MoneyDJ `Basic0008.xdjhtm?etfid={代碼}`**<br/>✅ 200 OK（直接提供考慮配息再投入後的原幣別市價與淨值累積報酬率%，以及 Alpha / Beta / R-squared） | 自行由還原股價計算 |
| **海外成分股收盤價（美股 / 日股 / 韓股）** | **`yfinance` 批次抓取**（僅針對海外成分股代號，約 30～50 檔，耗時 < 15 秒） | — |

---

## 3. 歷史資料回補（Backfill）：FinMind API 實測

針對新系統首次啟動需要的 5 年歷史價格、10 年股利、5 年本益比位階、歷史月營收與財報，實測 FinMind v4 API（`https://api.finmindtrade.com/api/v4/data`）：

| 資料集 (`dataset`) | 未帶 Token / 免費 Token 實測 | 用途 |
|---|---|---|
| `TaiwanStockInfo` | ✅ 200 OK（一次回傳全市場代碼、名稱、產業別、上市/上櫃分類） | 證券主檔與產業分類 |
| `TaiwanStockPrice` | ✅ 200 OK | 補 5 年歷史股價（計算年化波動度、最大回撤、5 年週線圖） |
| `TaiwanStockPER` | ✅ 200 OK（含 `dividend_yield`, `PER`, `PBR`） | 補 5 年歷史本益比、淨值比、殖利率（計算 5 年歷史百分位階） |
| `TaiwanStockDividend` | ✅ 200 OK（含盈餘/公積配息、配股、除息日、發放日） | 補 10 年歷史股利（計算連續配息年數、5 年平均、CAGR、穩定度） |
| `TaiwanStockDividendResult` | ✅ 200 OK（含除息前價、參考價、最高價） | 搭配股價計算近 5 次除息的**填息率与平均填息天數** |
| `TaiwanStockMonthRevenue` | ✅ 200 OK | 補近 24 個月營收 |
| `TaiwanStockFinancialStatements` | ✅ 200 OK（含 EPS、ROE、毛利率、營業利益率、自由現金流項目） | 補近 5 年季報與年報 EPS（計算盈餘配發率） |
| `TaiwanStockHoldingSharesPer` | ⚠️ 400（需付費 Sponsor 方案） | **不採用 FinMind**，改由每週抓取免費的 **TDCC 集保 OpenData (`id=1-5`)** 自行累積 |

> **回補策略**：
> - 免費註冊 FinMind Token 後上限為 **600 requests / hour**（未帶 Token 為 300 / hour）。
> - **優先回補清單（Tier 1，約 150 檔）**：25 檔精選存股 + 精選 ETF 清單 + 所有 ETF 的台股成分股，約需 450 次請求，**1 小時內可一次補完 5～10 年完整歷史**。
> - **全市場其餘股票（Tier 2，約 1,950 檔）**：由每日 TWSE / TPEx 全市場批次 API 每天自動累積，並透過 `backfill.yml` 分批自動補齊歷史。
