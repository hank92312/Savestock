"""公開資料源抓取器：TWSE OpenAPI、TPEx OpenAPI、MoneyDJ ETF、TDCC 集保與 FinMind。

全部使用標準 requests + BeautifulSoup，無須登入即可執行；若環境設有 FINMIND_TOKEN 自動帶入以提高速率上限。
"""
from __future__ import annotations

import csv
import io
import os
import re
import time
from datetime import date, datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def _clean_float(val) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip().replace(",", "").replace("%", "").replace("--", "").replace("N/A", "")
    if not s or s in ("-", ""):
        return None
    # 移除括號附註，例如 "49.9100（11/06）" 或 "0.38(月均:0.18)"
    s = re.split(r"[（(]", s)[0].strip()
    try:
        return float(s)
    except ValueError:
        return None


def _clean_int(val) -> int:
    f = _clean_float(val)
    return int(f) if f is not None else 0


def _roc_to_iso(roc_str: str) -> str:
    """將民國日期（如 '1151106'、'115/11/06'、'115年11月06日'）轉為 '2026-11-06'。"""
    s = (roc_str or "").strip()
    m = re.match(r"^(\d{2,3})[年/\-.]?(\d{2})[月/\-.]?(\d{2})", s)
    if m:
        yr = int(m.group(1)) + 1911
        return f"{yr:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    if re.match(r"^\d{4}[-/]\d{2}[-/]\d{2}$", s):
        return s.replace("/", "-")
    return str(date.today())


# ── 1. 全市場每日收盤價（TWSE 上市 + TPEx 上櫃，含普通股與 ETF）────────────

def fetch_twse_daily_all() -> dict[str, dict]:
    """一次抓取全上市（含上市 ETF）最新收盤價與成交量（張）。"""
    r = requests.get(
        "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
        headers=UA,
        timeout=25,
    )
    r.raise_for_status()
    rows = r.json()
    out: dict[str, dict] = {}
    for item in rows:
        code = (item.get("Code") or "").strip()
        name = (item.get("Name") or "").strip()
        close = _clean_float(item.get("ClosingPrice"))
        if not code or close is None or close <= 0:
            continue
        chg = _clean_float(item.get("Change")) or 0.0
        prev = close - chg
        chg_pct = round(chg / prev * 100, 2) if prev > 0 else 0.0
        vol_shares = _clean_int(item.get("TradeVolume"))
        out[code] = {
            "code": code,
            "name": name,
            "market": "TWSE",
            "date": _roc_to_iso(item.get("Date") or ""),
            "open": _clean_float(item.get("OpeningPrice")) or close,
            "high": _clean_float(item.get("HighestPrice")) or close,
            "low": _clean_float(item.get("LowestPrice")) or close,
            "close": close,
            "change": round(chg, 2),
            "changePct": chg_pct,
            "volume": round(vol_shares / 1000),  # 轉為「張」
        }
    return out


def fetch_tpex_daily_all() -> dict[str, dict]:
    """一次抓取全上櫃（含上櫃股票與美債/公司債 ETF）最新收盤價與成交量（張）。"""
    r = requests.get(
        "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
        headers=UA,
        timeout=25,
    )
    r.raise_for_status()
    rows = r.json()
    out: dict[str, dict] = {}
    for item in rows:
        code = (item.get("SecuritiesCompanyCode") or "").strip()
        # 過濾掉權證（6 碼純數字且非 00 開頭 ETF）
        if not code or (len(code) == 6 and not code.startswith("00")):
            continue
        close = _clean_float(item.get("Close"))
        if close is None or close <= 0:
            continue
        chg = _clean_float(item.get("Change")) or 0.0
        prev = close - chg
        chg_pct = round(chg / prev * 100, 2) if prev > 0 else 0.0
        vol_shares = _clean_int(item.get("TradingShares"))
        out[code] = {
            "code": code,
            "name": (item.get("CompanyName") or "").strip(),
            "market": "TPEX",
            "date": _roc_to_iso(item.get("Date") or ""),
            "open": _clean_float(item.get("Open")) or close,
            "high": _clean_float(item.get("High")) or close,
            "low": _clean_float(item.get("Low")) or close,
            "close": close,
            "change": round(chg, 2),
            "changePct": chg_pct,
            "volume": round(vol_shares / 1000),
        }
    return out


# ── 2. 全市場本益比 / 殖利率 / 股價淨值比 ──────────────────────────────

def fetch_valuation_all() -> dict[str, dict]:
    """合併上市 `BWIBBU_ALL` 與上櫃 `tpex_mainboard_peratio_analysis`。"""
    out: dict[str, dict] = {}
    try:
        r1 = requests.get(
            "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL",
            headers=UA,
            timeout=20,
        ).json()
        for it in r1:
            code = (it.get("Code") or "").strip()
            if code:
                out[code] = {
                    "pe": _clean_float(it.get("PEratio")),
                    "pb": _clean_float(it.get("PBratio")),
                    "officialYield": _clean_float(it.get("DividendYield")),
                }
    except Exception:
        pass

    try:
        r2 = requests.get(
            "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis",
            headers=UA,
            timeout=20,
        ).json()
        for it in r2:
            code = (it.get("SecuritiesCompanyCode") or "").strip()
            if code:
                out[code] = {
                    "pe": _clean_float(it.get("PriceEarningRatio")),
                    "pb": _clean_float(it.get("PriceBookRatio")),
                    "officialYield": _clean_float(it.get("YieldRatio")),
                    "tpexDivPerShare": _clean_float(it.get("DividendPerShare")),
                }
    except Exception:
        pass
    return out


# ── 3. 全市場產業分類（FinMind TaiwanStockInfo）────────────────────────

def fetch_stock_info_map() -> dict[str, dict]:
    """一次取得全市場股票與 ETF 的中文產業類別與上市/上櫃屬性。"""
    out: dict[str, dict] = {}
    try:
        r = requests.get(
            "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo",
            headers=UA,
            timeout=20,
        ).json()
        for row in r.get("data", []):
            cid = (row.get("stock_id") or "").strip()
            if not cid:
                continue
            out[cid] = {
                "name": (row.get("stock_name") or "").strip(),
                "sector": (row.get("industry_category") or "其他").strip(),
                "market": "TPEX" if row.get("type") == "tpex" else "TWSE",
            }
    except Exception:
        pass
    return out


# ── 4. 全市場月營收（上市 t187ap05_L + 上櫃 mopsfin_t187ap05_O）────────

def fetch_monthly_revenue_all() -> dict[str, dict]:
    """一次取得全市場最新月營收、MoM%、YoY%。"""
    out: dict[str, dict] = {}
    for url in (
        "https://openapi.twse.com.tw/v1/opendata/t187ap05_L",
        "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O",
    ):
        try:
            rows = requests.get(url, headers=UA, timeout=25).json()
            for r in rows:
                code = (r.get("公司代號") or "").strip()
                if not code:
                    continue
                ym_raw = (r.get("資料年月") or "").strip()
                if len(ym_raw) >= 5:
                    yr = int(ym_raw[:-2]) + 1911
                    mo = int(ym_raw[-2:])
                    ym = f"{yr:04d}-{mo:02d}"
                else:
                    ym = ym_raw
                out[code] = {
                    "ym": ym,
                    "rev": _clean_float(r.get("營業收入-當月營收")),
                    "mom": _clean_float(r.get("營業收入-上月比較增減(%)")),
                    "yoy": _clean_float(r.get("營業收入-去年同月增減(%)")),
                    "cumYoy": _clean_float(r.get("累計營業收入-前期比較增減(%)")),
                }
        except Exception:
            pass
    return out


# ── 5. 董事會/股東會已公告股利（上市 t187ap45_L + 上櫃 mopsfin_t187ap39_O）──

def fetch_announced_dividends_all() -> dict[str, dict]:
    """取得上市與上櫃公司最新已公告配息（現金 + 配股）。"""
    out: dict[str, dict] = {}
    target_roc = str((date.today().year - 1911) - 1)

    # 上市
    try:
        rows = requests.get(
            "https://openapi.twse.com.tw/v1/opendata/t187ap45_L",
            headers=UA,
            timeout=25,
        ).json()
        for r in rows:
            if r.get("股利年度") != target_roc or r.get("股利所屬年(季)度") != "年度":
                continue
            code = (r.get("公司代號") or "").strip()
            if not code:
                continue
            cash = sum(
                _clean_float(r.get(k)) or 0.0
                for k in (
                    "股東配發-盈餘分配之現金股利(元/股)",
                    "股東配發-法定盈餘公積發放之現金(元/股)",
                    "股東配發-資本公積發放之現金(元/股)",
                )
            )
            stock = sum(
                _clean_float(r.get(k)) or 0.0
                for k in (
                    "股東配發-盈餘轉增資配股(元/股)",
                    "股東配發-法定盈餘公積轉增資配股(元/股)",
                    "股東配發-資本公積轉增資配股(元/股)",
                )
            )
            total = round(cash + stock, 4)
            if total > 0:
                out[code] = {"cash": round(cash, 4), "stock": round(stock, 4), "total": total}
    except Exception:
        pass

    # 上櫃
    try:
        rows_o = requests.get(
            "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap39_O",
            headers=UA,
            timeout=25,
        ).json()
        for r in rows_o:
            if r.get("股利年度") != target_roc:
                continue
            code = (r.get("公司代號") or "").strip()
            if not code:
                continue
            cash = (
                (_clean_float(r.get("股東配發內容-盈餘分配之現金股利(元/股)")) or 0.0)
                + (_clean_float(r.get("股東配發內容-法定盈餘公積、資本公積發放之現金(元/股)")) or 0.0)
            )
            stock = (
                (_clean_float(r.get("股東配發內容-盈餘轉增資配股(元/股)")) or 0.0)
                + (_clean_float(r.get("股東配發內容-法定盈餘公積、資本公積轉增資配股(元/股)")) or 0.0)
            )
            total = round(cash + stock, 4)
            if total > 0:
                out[code] = {"cash": round(cash, 4), "stock": round(stock, 4), "total": total}
    except Exception:
        pass

    return out


# ── 6. 預告除權息行事曆（上市 TWT48U + 上櫃 tpex_exright_prepost）────────

def fetch_upcoming_ex_dividends() -> list[dict]:
    """取得上市與上櫃即將除權息預告清單。"""
    events: list[dict] = []
    try:
        r1 = requests.get(
            "https://www.twse.com.tw/rwd/zh/exRight/TWT48U?response=json",
            headers=UA,
            timeout=20,
        ).json()
        for row in r1.get("data", []):
            if len(row) < 8:
                continue
            ex_date = _roc_to_iso(row[0])
            code = str(row[1]).strip()
            name = str(row[2]).strip()
            cash = _clean_float(row[7]) or 0.0
            stock = (_clean_float(row[4]) or 0.0) * 10.0
            events.append({
                "date": ex_date,
                "code": code,
                "name": name,
                "eventType": "ex_date",
                "cashDiv": round(cash, 4),
                "stockDiv": round(stock, 4),
                "note": f"除{row[3]}交易日",
            })
    except Exception:
        pass

    try:
        r2 = requests.get(
            "https://www.tpex.org.tw/openapi/v1/tpex_exright_prepost",
            headers=UA,
            timeout=20,
        ).json()
        for item in r2:
            code = (item.get("SecuritiesCompanyCode") or "").strip()
            if not code:
                continue
            events.append({
                "date": _roc_to_iso(item.get("ExRrightsExDividendDate") or ""),
                "code": code,
                "name": (item.get("CompanyName") or "").strip(),
                "eventType": "ex_date",
                "cashDiv": _clean_float(item.get("CashDividend")) or 0.0,
                "stockDiv": _clean_float(item.get("StockDividendRatio")) or 0.0,
                "note": f"{item.get('ExRrightsExDividend', '除權息')}交易日",
            })
    except Exception:
        pass

    events.sort(key=lambda e: e["date"])
    return events


# ── 7. 集保大戶股權分散表（TDCC OpenData id=1-5）────────────────────────

def fetch_tdcc_large_holders() -> tuple[str, dict[str, dict]]:
    """一次讀取全市場 TDCC 集保分散表 CSV，回傳 (資料日期, {代號: {large1000Pct, large400Pct, shareholders}})。
    持股分級 15 = 1,000 張以上；分級 12~15 = 400 張以上；分級 17 = 合計列。
    """
    out: dict[str, dict] = {}
    tdcc_date = ""
    try:
        r = requests.get(
            "https://smart.tdcc.com.tw/opendata/getOD.ashx?id=1-5",
            headers=UA,
            timeout=30,
        )
        r.raise_for_status()
        text = r.content.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            code = (row.get("證券代號") or "").strip()
            if not code:
                continue
            if not tdcc_date and row.get("資料日期"):
                d = row["資料日期"].strip()
                if len(d) == 8:
                    tdcc_date = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            lvl = _clean_int(row.get("持股分級"))
            pct = _clean_float(row.get("占集保庫存數比例%")) or 0.0
            holders = _clean_int(row.get("人數"))
            rec = out.setdefault(code, {"large1000Pct": 0.0, "large400Pct": 0.0, "shareholders": 0})
            if lvl == 15:
                rec["large1000Pct"] = round(pct, 2)
                rec["large400Pct"] = round(rec["large400Pct"] + pct, 2)
            elif lvl in (12, 13, 14):
                rec["large400Pct"] = round(rec["large400Pct"] + pct, 2)
            elif lvl == 17:
                rec["shareholders"] = holders
    except Exception:
        pass
    return tdcc_date, out


# ── 8. 全市場 ETF 即時淨值與折溢價 + 規模/受益人數（MIS + e添富）──────────

def fetch_etf_market_snapshots() -> dict[str, dict]:
    """合併證交所 MIS `all_etf.txt`（淨值、折溢價%）與 e添富（規模、受益人數、投信）。"""
    out: dict[str, dict] = {}
    try:
        rmis = requests.get("https://mis.twse.com.tw/stock/data/all_etf.txt", headers=UA, timeout=20).json()
        for grp in rmis.get("a1", []):
            for msg in grp.get("msgArray", []):
                code = (msg.get("a") or "").strip()
                if not code:
                    continue
                out[code] = {
                    "code": code,
                    "name": (msg.get("b") or "").strip(),
                    "price": _clean_float(msg.get("e")),
                    "nav": _clean_float(msg.get("f")),
                    "discountPct": _clean_float(msg.get("g")),
                    "prevNav": _clean_float(msg.get("h")),
                }
    except Exception:
        pass

    try:
        retf = requests.get(
            "https://www.twse.com.tw/zh/ETFortune/ajaxProductsResult",
            headers=UA,
            timeout=20,
        ).json()
        for row in retf.get("data", []):
            code = (row.get("stockNo") or "").strip()
            if not code:
                continue
            rec = out.setdefault(code, {"code": code, "name": (row.get("stockName") or "").strip()})
            rec["aumHundredMillions"] = _clean_float(row.get("totalAv"))  # 億台幣
            rec["holdersCount"] = _clean_int(row.get("holders"))
            rec["issuer"] = (row.get("issuer") or "").replace("證券投資信託股份有限公司", "投信").strip()
            rec["trackingIndex"] = row.get("indexName") or ""
            rec["listingDate"] = (row.get("listingDate") or "").replace(".", "-")
    except Exception:
        pass

    return out


# ── 9. MoneyDJ ETF 完整成分股（Basic0007B）與基本資料/費用率/報酬 ─────────

def fetch_moneydj_etf_detail(etf_code: str) -> dict:
    """從 MoneyDJ 取得單檔 ETF 的：
    - 完整成分股清單（Basic0007B，30～60+ 檔）
    - 總管理費用率、配息頻率、年化標準差（Basic0004）
    - 含息累積報酬率 1M / 3M / 6M / 1Y / 3Y（Basic0008）
    - 歷次配息明細（Basic0005）
    """
    etfid = f"{etf_code}.TW"
    result: dict = {
        "code": etf_code,
        "holdings": [],
        "completeness": "none",
        "expenseRatioPct": None,
        "divFrequency": None,
        "volatilityPct": None,
        "returns": {},
        "dividends": [],
    }

    # 1) Basic0007B：完整持股
    try:
        r = requests.get(
            f"https://www.moneydj.com/ETF/X/Basic/Basic0007B.xdjhtm?etfid={etfid}",
            headers=UA,
            timeout=15,
        )
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        holdings: list[dict] = []
        for t in soup.find_all("table", class_="datalist"):
            for tr in t.find_all("tr"):
                tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                if len(tds) < 2:
                    continue
                raw_name = tds[0]
                weight = _clean_float(tds[1])
                shares = _clean_int(tds[2]) if len(tds) >= 3 else 0
                if not raw_name or weight is None or weight <= 0:
                    continue
                # 解析 "南亞(1303.TW)" 或 "Apple(AAPL.US)"
                m = re.match(r"^(.+?)\(([A-Za-z0-9.*\-]+)\)$", raw_name)
                if m:
                    sname = m.group(1).strip()
                    sid = m.group(2).strip().replace(".TW", "").replace(".TWO", "")
                else:
                    sname = raw_name
                    sid = raw_name[:24]
                holdings.append({
                    "stock_id": sid,
                    "name": sname,
                    "weight": round(weight, 4),
                    "shares": shares,
                })
        if holdings:
            result["holdings"] = holdings
            result["completeness"] = "full" if len(holdings) > 10 else "top10"
    except Exception:
        pass

    # 2) Basic0004：費用率、配息頻率、年化標準差
    try:
        r4 = requests.get(
            f"https://www.moneydj.com/ETF/X/Basic/Basic0004.xdjhtm?etfid={etfid}",
            headers=UA,
            timeout=15,
        )
        r4.encoding = "utf-8"
        soup4 = BeautifulSoup(r4.text, "html.parser")
        for tr in soup4.select("table.DataTable tr"):
            cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            for idx in range(0, len(cells) - 1, 2):
                k, v = cells[idx], cells[idx + 1]
                if "總管理費用" in k:
                    result["expenseRatioPct"] = _clean_float(v)
                elif "配息頻率" in k:
                    result["divFrequency"] = v or "不配息"
                elif "年化標準差" in k:
                    result["volatilityPct"] = _clean_float(v)
                elif "ETF淨值" in k and result.get("nav") is None:
                    result["nav"] = _clean_float(v)
                elif "折溢價" in k and result.get("discountPct") is None:
                    result["discountPct"] = _clean_float(v)
    except Exception:
        pass

    # 3) Basic0008：含息總報酬
    try:
        r8 = requests.get(
            f"https://www.moneydj.com/ETF/X/Basic/Basic0008.xdjhtm?etfid={etfid}",
            headers=UA,
            timeout=15,
        )
        r8.encoding = "utf-8"
        soup8 = BeautifulSoup(r8.text, "html.parser")
        t8 = soup8.find("table", class_="DataTable")
        if t8:
            rows8 = [[c.get_text(strip=True) for c in tr.find_all(["th", "td"])] for tr in t8.find_all("tr")]
            if len(rows8) >= 3:
                headers = rows8[0]
                nav_row = rows8[2]  # 淨值含息報酬
                col_map = {"一個月": "m1", "三個月": "m3", "六個月": "m6", "一年": "y1", "三年": "y3", "五年": "y5"}
                for h_idx, h_name in enumerate(headers):
                    if h_name in col_map and h_idx < len(nav_row):
                        result["returns"][col_map[h_name]] = _clean_float(nav_row[h_idx])
    except Exception:
        pass

    # 4) Basic0005：歷次配息紀錄
    try:
        r5 = requests.get(
            f"https://www.moneydj.com/ETF/X/Basic/Basic0005.xdjhtm?etfid={etfid}",
            headers=UA,
            timeout=15,
        )
        r5.encoding = "utf-8"
        soup5 = BeautifulSoup(r5.text, "html.parser")
        t5 = soup5.find("table", class_="datalist")
        if t5:
            for tr in t5.find_all("tr")[1:]:
                tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                if len(tds) >= 6:
                    ex_d = (tds[1] or tds[0]).replace("/", "-")
                    pay_d = tds[3].replace("/", "-")
                    amt = _clean_float(tds[5]) or 0.0
                    ann_y = _clean_float(tds[6]) if len(tds) >= 7 else None
                    if ex_d and amt > 0:
                        result["dividends"].append({
                            "year": int(ex_d[:4]) if len(ex_d) >= 4 and ex_d[:4].isdigit() else date.today().year,
                            "exDate": ex_d,
                            "payDate": pay_d,
                            "cash": round(amt, 4),
                            "stock": 0.0,
                            "total": round(amt, 4),
                            "annualizedYieldPct": ann_y,
                        })
    except Exception:
        pass

    return result


# ── 10. FinMind 個股歷史股價與歷年股利（供精選個股與自選股深度歷史）────────

def fetch_finmind_stock_history(code: str, start_date: str = "2020-01-01") -> tuple[list[dict], list[dict], list[dict]]:
    """從 FinMind 取得單一股票的：
    - 歷史收盤價 `TaiwanStockPrice`
    - 歷年股利 `TaiwanStockDividend`
    - 歷史本益比/殖利率 `TaiwanStockPER`
    """
    token = os.getenv("FINMIND_TOKEN", "").strip()
    base = "https://api.finmindtrade.com/api/v4/data"
    prices: list[dict] = []
    dividends: list[dict] = []
    valuations: list[dict] = []

    def _get(dataset: str, sd: str):
        params = {"dataset": dataset, "data_id": code, "start_date": sd}
        if token:
            params["token"] = token
        r = requests.get(base, params=params, headers=UA, timeout=20).json()
        return r.get("data") or []

    try:
        p_date = f"{date.today().year - 2}-01-01"
        for row in _get("TaiwanStockPrice", p_date):
            c = _clean_float(row.get("close"))
            if c and c > 0:
                prices.append({
                    "date": row.get("date"),
                    "close": c,
                    "volume": round(_clean_int(row.get("Trading_Volume")) / 1000),
                })
    except Exception:
        pass

    try:
        for row in _get("TaiwanStockDividend", start_date):
            cash = (
                (_clean_float(row.get("CashEarningsDistribution")) or 0.0)
                + (_clean_float(row.get("CashStatutorySurplus")) or 0.0)
            )
            stock = (
                (_clean_float(row.get("StockEarningsDistribution")) or 0.0)
                + (_clean_float(row.get("StockStatutorySurplus")) or 0.0)
            )
            total = round(cash + stock, 4)
            if total <= 0:
                continue
            ex_d = (
                row.get("CashExDividendTradingDate")
                or row.get("StockExDividendTradingDate")
                or row.get("date")
                or ""
            )
            pay_d = row.get("CashDividendPaymentDate") or ""
            yr = int(ex_d[:4]) if len(ex_d) >= 4 and ex_d[:4].isdigit() else date.today().year
            dividends.append({
                "year": yr,
                "exDate": ex_d,
                "payDate": pay_d,
                "cash": round(cash, 4),
                "stock": round(stock, 4),
                "total": total,
            })
    except Exception:
        pass

    try:
        v_date = f"{date.today().year - 3}-01-01"
        raw_v = _get("TaiwanStockPER", v_date)
        # 抽樣每週一筆以控制 JSON 體積
        for idx, row in enumerate(raw_v):
            if idx % 5 == 0 or idx == len(raw_v) - 1:
                valuations.append({
                    "date": row.get("date"),
                    "pe": _clean_float(row.get("PER")),
                    "pb": _clean_float(row.get("PBR")),
                    "yield": _clean_float(row.get("dividend_yield")),
                })
    except Exception:
        pass

    time.sleep(0.15)
    return prices, dividends, valuations

