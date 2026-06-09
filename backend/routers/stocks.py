from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from database import get_db
from datetime import datetime, timedelta
import re
import yfinance as yf
import requests as req_lib

# ── 全證券搜尋快取 ──────────────────────────────────────────────
# code (不含後綴) → {"name": str, "suffix": ".TW" | ".TWO"}
_search_cache: dict[str, dict] = {}
_search_cache_loaded_at: datetime | None = None
_CACHE_TTL = timedelta(hours=24)
_UA = {"User-Agent": "Mozilla/5.0"}


def _load_search_cache() -> None:
    """載入上市(含ETF) + 上櫃 全證券名稱快取，24h TTL。"""
    global _search_cache_loaded_at
    if _search_cache_loaded_at and datetime.now() - _search_cache_loaded_at < _CACHE_TTL:
        return

    new_cache: dict[str, dict] = {}

    # 1. 上市 + ETF：TWSE STOCK_DAY_ALL（欄位 Code / Name）
    try:
        r = req_lib.get(
            "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
            timeout=10, headers=_UA,
        )
        data = r.json()
        if len(data) > 100:          # 非交易日可能為空，有資料才更新
            for item in data:
                code = item.get("Code", "").strip()
                name = item.get("Name", "").strip()
                if code and name:
                    new_cache[code] = {"name": name, "suffix": ".TW"}
    except Exception:
        pass

    # 若 STOCK_DAY_ALL 為空（非交易日），退回 t187ap03_L（公司主檔，無 ETF 但穩定）
    if not new_cache:
        try:
            r = req_lib.get(
                "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
                timeout=10, headers=_UA,
            )
            for item in r.json():
                code = item.get("公司代號", "").strip()
                name = (item.get("公司簡稱") or item.get("公司名稱", "")).strip()
                if code and name:
                    new_cache[code] = {"name": name, "suffix": ".TW"}
        except Exception:
            pass

    # 上櫃（TPEx）不在本專案範圍內，僅支援上市股票。
    if new_cache:
        _search_cache.update(new_cache)
        _search_cache_loaded_at = datetime.now()


def _resolve_stock_id(code: str) -> str:
    """將不含後綴的代號解析成完整 stock_id（.TW 或 .TWO）。"""
    _load_search_cache()
    entry = _search_cache.get(code.upper())
    if entry:
        return f"{code.upper()}{entry['suffix']}"
    return f"{code.upper()}.TW"      # 找不到就預設上市


def _search_tw_code_by_name(chinese_name: str) -> str | None:
    """用中文名稱（部分符合）查台股代號（不含後綴）。"""
    _load_search_cache()
    for code, info in _search_cache.items():
        if chinese_name in info["name"] or info["name"] in chinese_name:
            return code
    return None


def _get_tw_chinese_name(code_no_suffix: str) -> str | None:
    """向 TWSE/OTC 抓中文股票名稱，失敗回傳 None。"""
    for market in ("tse", "otc"):
        try:
            r = req_lib.get(
                "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
                params={"ex_ch": f"{market}_{code_no_suffix}.tw", "json": "1"},
                timeout=5,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            data = r.json()
            if data.get("msgArray") and data["msgArray"][0].get("n"):
                return data["msgArray"][0]["n"]
        except Exception:
            continue
    return None


def _has_chinese(s: str) -> bool:
    return any('一' <= c <= '鿿' for c in (s or ""))


def _resolve_chinese_name(code_no_suffix: str) -> str | None:
    """解析台股中文名稱：優先用已批次載入的 TWSE 搜尋快取（穩定可靠），
    快取無資料才退回即時 mis API。皆失敗回傳 None。"""
    _load_search_cache()
    entry = _search_cache.get(code_no_suffix.upper())
    if entry and _has_chinese(entry["name"]):
        return entry["name"]
    realtime = _get_tw_chinese_name(code_no_suffix)
    return realtime if realtime and _has_chinese(realtime) else None

router = APIRouter(prefix="/stocks", tags=["stocks"])

_LATEST_PRICE_JOIN = """
    LEFT JOIN Daily_Prices dp ON sm.Stock_ID = dp.Stock_ID
        AND dp.Date = (SELECT MAX(Date) FROM Daily_Prices WHERE Stock_ID = sm.Stock_ID)
"""

_SM_COLS = "sm.Stock_ID, sm.Name, sm.Sector, sm.Avg_Dividend_2Y, sm.Avg_Dividend_5Y, sm.Dividend_1Y, sm.Listing_Months"


def _row_to_dict(row):
    close = row.Close_Price
    avg_div = row.Avg_Dividend_2Y
    avg_div_5y = row.Avg_Dividend_5Y
    div_1y = row.Dividend_1Y
    yield_est = round(avg_div / close * 100, 2) if close and avg_div else None
    yield_1y = round(div_1y / close * 100, 2) if close and div_1y else None
    yield_5y = round(avg_div_5y / close * 100, 2) if close and avg_div_5y else None
    return {
        "stock_id": row.Stock_ID,
        "name": row.Name,
        "sector": row.Sector,
        "avg_dividend_2y": avg_div,
        "avg_dividend_5y": avg_div_5y,
        "dividend_1y": div_1y,
        "listing_months": row.Listing_Months,
        "close_price": close,
        "estimated_yield": yield_est,
        "yield_1y": yield_1y,
        "yield_5y": yield_5y,
        "alert_flag": bool(row.Alert_Flag),
        "alert_reason": row.Alert_Reason,
        "last_date": str(row.Date) if row.Date else None,
    }


def _listing_months(info) -> int | None:
    """從 yfinance info 推算上市迄今月數；無法判斷時回傳 None（視為已滿2年）。"""
    epoch = None
    if info:
        ms = info.get("firstTradeDateMilliseconds")
        epoch = ms / 1000 if ms else info.get("firstTradeDateEpochUtc")
    if not epoch:
        return None
    try:
        listing_date = datetime.fromtimestamp(epoch)
    except (OverflowError, OSError, ValueError):
        return None
    return max(int((datetime.now() - listing_date).days / 30.44), 1)


_PAR_VALUE = 10.0  # 台股面額；股票股利以面額還原成元


def _stock_div_value(ratio) -> float:
    """yfinance「Stock Splits」配股比 → 股票股利（元，面額還原）。
    台股配股 X 元對應配股比 (1 + X/10)，故 X =(ratio-1)×10；
    僅計配股（ratio>1），減資（ratio<1）不視為股利。"""
    try:
        r = float(ratio)
    except (TypeError, ValueError):
        return 0.0
    return (r - 1) * _PAR_VALUE if r > 1 else 0.0


def _total_div_series(actions):
    """每個除權息日的『現金股利 + 股票股利(面額還原)』合計序列。"""
    if actions is None or actions.empty:
        return None
    cash = actions["Dividends"].fillna(0) if "Dividends" in actions.columns else 0
    if "Stock Splits" in actions.columns:
        stock = actions["Stock Splits"].apply(_stock_div_value)
    else:
        stock = 0
    return cash + stock


def _avg_dividend(actions, listing_months: int | None) -> float:
    """上市滿2年：近2年股利平均(÷2)；不滿2年：上市迄今全部股利年化。
    股利＝現金股利＋股票股利（配股面額還原）。"""
    total_series = _total_div_series(actions)
    if total_series is None:
        return 0.0
    is_new = listing_months is not None and listing_months < 24
    if is_new:
        total = float(total_series.sum())
        years = listing_months / 12
        return total / years if years > 0 else total
    two_years_ago = datetime.now() - timedelta(days=730)
    if actions.index.tzinfo:
        two_years_ago = two_years_ago.replace(tzinfo=actions.index.tzinfo)
    recent = total_series[total_series.index > two_years_ago]
    return float(recent.sum()) / 2


def _avg_dividend_5y(actions, listing_months: int | None) -> float:
    """上市滿5年：近5年股利平均(÷5)；不滿5年：上市迄今全部股利年化。"""
    total_series = _total_div_series(actions)
    if total_series is None:
        return 0.0
    is_under_5y = listing_months is not None and listing_months < 60
    if is_under_5y:
        total = float(total_series.sum())
        years = listing_months / 12
        return total / years if years > 0 else total
    five_years_ago = datetime.now() - timedelta(days=365 * 5)
    if actions.index.tzinfo:
        five_years_ago = five_years_ago.replace(tzinfo=actions.index.tzinfo)
    recent = total_series[total_series.index > five_years_ago]
    return float(recent.sum()) / 5


def _dividend_1y(actions) -> float:
    """近 12 個月股利合計（現金＋配股面額還原；近一年殖利率用）。"""
    total_series = _total_div_series(actions)
    if total_series is None:
        return 0.0
    one_year_ago = datetime.now() - timedelta(days=365)
    if actions.index.tzinfo:
        one_year_ago = one_year_ago.replace(tzinfo=actions.index.tzinfo)
    recent = total_series[total_series.index > one_year_ago]
    return float(recent.sum())


def _upsert_dividends(sid: str, actions, conn) -> None:
    """將 yfinance 股利歷史寫入 Dividends 表（現金與配股分欄，供股利折線圖）。"""
    if actions is None or actions.empty:
        return
    has_cash = "Dividends" in actions.columns
    has_split = "Stock Splits" in actions.columns
    for ts in actions.index:
        cash = float(actions["Dividends"].get(ts, 0) or 0) if has_cash else 0.0
        stock = _stock_div_value(actions["Stock Splits"].get(ts, 0)) if has_split else 0.0
        if cash <= 0 and stock <= 0:
            continue
        try:
            conn.execute(text("""
                INSERT INTO Dividends (Stock_ID, Ex_Date, Cash_Dividend, Stock_Dividend)
                VALUES (:sid, :date, :cash, :stock)
                ON CONFLICT (Stock_ID, Ex_Date) DO UPDATE SET
                    Cash_Dividend = EXCLUDED.Cash_Dividend,
                    Stock_Dividend = EXCLUDED.Stock_Dividend
            """), {"sid": sid, "date": ts.date(), "cash": cash, "stock": stock})
        except Exception:
            pass


def _fetch_and_upsert(sid: str, conn) -> dict | None:
    """從 yfinance 抓取最新資料並寫入 DB，回傳股票 dict 或 None（查無此股）。"""
    ticker = yf.Ticker(sid)
    hist = ticker.history(period="1y")
    # yfinance 可能回傳當日尚未收盤的不完整列（Close/Volume 為 NaN），須剔除
    hist = hist.dropna(subset=["Close", "Volume"])
    if hist.empty:
        return None

    info = ticker.info
    en_name = info.get("shortName") or info.get("longName") or sid

    # 讀取已存在資料（保留原有中文名稱、sector 與產業跌幅閾值）
    existing = conn.execute(
        text("SELECT Name, Sector, Default_Drop_Threshold FROM Stock_Master WHERE Stock_ID = :sid"),
        {"sid": sid},
    ).fetchone()
    sector = existing.Sector if existing else "Unknown"

    code_only = sid.replace(".TWO", "").replace(".TW", "")
    if existing:
        name = existing.Name
        # 既有名稱若非中文（早期抓取退回了英文名），嘗試升級為正確中文名
        if not _has_chinese(name):
            name = _resolve_chinese_name(code_only) or name
    else:
        # 新股票：優先取 TWSE 中文名，皆失敗才用 yfinance 英文名
        name = _resolve_chinese_name(code_only) or en_name

    # 計算平均股利（上市不滿2年改用上市迄今年化）+ 近一年股利 + 近5年年均
    listing_months = _listing_months(info)
    actions = ticker.actions
    avg_div = _avg_dividend(actions, listing_months)
    avg_div_5y = _avg_dividend_5y(actions, listing_months)
    div_1y = _dividend_1y(actions)

    latest = hist.iloc[-1]
    prev = hist.iloc[-2] if len(hist) > 1 else latest
    close = float(latest["Close"])
    volume = int(latest["Volume"])
    today = latest.name.date()

    # 計算警示
    price_change = (close - float(prev["Close"])) / float(prev["Close"]) * 100
    avg_vol_20d = hist["Volume"].tail(20).mean()
    vol_ratio = volume / avg_vol_20d if avg_vol_20d > 0 else 1
    alert_reasons = []
    # 預設股用其產業別閾值（已存於 Default_Drop_Threshold）；無紀錄者預設 3%
    drop_pct = (existing.Default_Drop_Threshold
                if existing and existing.Default_Drop_Threshold else 0.03) * 100
    if price_change <= -drop_pct:
        alert_reasons.append(f"跌幅:{price_change:.2f}%")
    if vol_ratio >= 2.5:
        alert_reasons.append(f"爆量:{vol_ratio:.2f}倍")
    alert_flag = bool(alert_reasons)
    alert_reason = ", ".join(alert_reasons)

    conn.execute(text("""
        INSERT INTO Stock_Master (Stock_ID, Name, Sector, Avg_Dividend_2Y, Avg_Dividend_5Y, Dividend_1Y, Listing_Months, Is_Default, Last_Updated)
        VALUES (:sid, :name, :sector, :avg_div, :avg_div_5y, :div_1y, :listing_months, FALSE, CURRENT_TIMESTAMP)
        ON CONFLICT (Stock_ID) DO UPDATE SET
            Avg_Dividend_2Y = EXCLUDED.Avg_Dividend_2Y,
            Avg_Dividend_5Y = EXCLUDED.Avg_Dividend_5Y,
            Dividend_1Y = EXCLUDED.Dividend_1Y,
            Listing_Months = EXCLUDED.Listing_Months,
            Last_Updated = CURRENT_TIMESTAMP
    """), {"sid": sid, "name": name, "sector": sector, "avg_div": avg_div,
           "avg_div_5y": avg_div_5y, "div_1y": div_1y, "listing_months": listing_months})

    # 最新一筆：UPSERT（確保今日警示最新）
    conn.execute(text("""
        INSERT INTO Daily_Prices (Stock_ID, Date, Close_Price, Volume, Alert_Flag, Alert_Reason)
        VALUES (:sid, :date, :close, :volume, :alert_flag, :alert_reason)
        ON CONFLICT (Stock_ID, Date) DO UPDATE SET
            Close_Price = EXCLUDED.Close_Price,
            Volume = EXCLUDED.Volume,
            Alert_Flag = EXCLUDED.Alert_Flag,
            Alert_Reason = EXCLUDED.Alert_Reason
    """), {"sid": sid, "date": today, "close": close, "volume": volume,
           "alert_flag": alert_flag, "alert_reason": alert_reason})

    # 歷史列：DO NOTHING 保留已有警示資料
    for ts, row in hist.iloc[:-1].iterrows():
        try:
            conn.execute(text("""
                INSERT INTO Daily_Prices (Stock_ID, Date, Close_Price, Volume, Alert_Flag, Alert_Reason)
                VALUES (:sid, :date, :close, :volume, 0, '')
                ON CONFLICT (Stock_ID, Date) DO NOTHING
            """), {"sid": sid, "date": ts.date(),
                   "close": float(row["Close"]), "volume": int(row["Volume"])})
        except Exception:
            pass

    _upsert_dividends(sid, actions, conn)

    yield_est = round(avg_div / close * 100, 2) if close and avg_div else None
    yield_1y = round(div_1y / close * 100, 2) if close and div_1y else None
    yield_5y = round(avg_div_5y / close * 100, 2) if close and avg_div_5y else None
    return {
        "stock_id": sid,
        "name": name,
        "sector": sector,
        "avg_dividend_2y": avg_div,
        "avg_dividend_5y": avg_div_5y,
        "dividend_1y": div_1y,
        "listing_months": listing_months,
        "close_price": close,
        "estimated_yield": yield_est,
        "yield_1y": yield_1y,
        "yield_5y": yield_5y,
        "alert_flag": alert_flag,
        "alert_reason": alert_reason,
        "last_date": str(today),
    }


# ── 端點 ──────────────────────────────────────────────────────

@router.get("/")
def get_default_stocks(conn=Depends(get_db)):
    rows = conn.execute(text(f"""
        SELECT {_SM_COLS},
               dp.Close_Price, dp.Alert_Flag, dp.Alert_Reason, dp.Date
        FROM Stock_Master sm
        {_LATEST_PRICE_JOIN}
        WHERE sm.Is_Default = TRUE
        ORDER BY
            CASE WHEN sm.Dividend_1Y > 0 AND dp.Close_Price > 0
                 THEN sm.Dividend_1Y / dp.Close_Price * 100
                 ELSE 0 END DESC
    """)).fetchall()
    return [_row_to_dict(r) for r in rows]


@router.post("/refresh")
def refresh_default_stocks(conn=Depends(get_db)):
    """即時從 yfinance 更新所有預設股的最新價格/警示並回傳（依殖利率降序）。"""
    rows = conn.execute(
        text("SELECT Stock_ID FROM Stock_Master WHERE Is_Default = TRUE")
    ).fetchall()
    results = []
    for r in rows:
        try:
            data = _fetch_and_upsert(r.Stock_ID, conn)
            if data:
                results.append(data)
        except Exception:
            pass  # 單檔失敗不影響其餘
    results.sort(key=lambda d: d.get("yield_1y") or -1, reverse=True)
    return results


@router.get("/search")
def search_stocks(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
):
    """模糊搜尋台股：輸入代號前綴或中文名稱部分字詞，回傳候選清單。"""
    _load_search_cache()
    q = q.strip()
    has_chinese = any('一' <= c <= '鿿' for c in q)
    q_upper = q.upper()

    results = []
    for code, info in _search_cache.items():
        if has_chinese:
            if q in info["name"]:
                results.append({
                    "stock_id": f"{code}{info['suffix']}",
                    "name": info["name"],
                })
        else:
            if code.startswith(q_upper):
                results.append({
                    "stock_id": f"{code}{info['suffix']}",
                    "name": info["name"],
                })
        if len(results) >= limit:
            break

    # 代號前綴搜尋：按代號排序讓最短（最精確）的優先
    if not has_chinese:
        results.sort(key=lambda x: x["stock_id"])

    return results[:limit]


@router.get("/lookup/{stock_id}")
def lookup_stock(stock_id: str, conn=Depends(get_db)):
    """即時查詢任意台股。支援股票代號（0050、6147）或中文名稱（台積電）。"""
    query = stock_id.strip()

    # 判斷是否包含中文
    has_chinese = any('一' <= c <= '鿿' for c in query)
    if has_chinese:
        # 1. 先查 Stock_Master（已知股票）
        row = conn.execute(
            text("SELECT Stock_ID FROM Stock_Master WHERE Name LIKE :q"),
            {"q": f"%{query}%"},
        ).fetchone()
        if row:
            sid = row.Stock_ID
        else:
            # 2. 向快取查名稱對應代號
            code = _search_tw_code_by_name(query)
            if code:
                sid = _resolve_stock_id(code)
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到「{query}」，請改用股票代號查詢（如：2330）",
                )
    else:
        # 已含後綴則直接用，否則從快取解析正確後綴（.TW 或 .TWO）
        if query.upper().endswith(".TW") or query.upper().endswith(".TWO"):
            sid = query.upper()
        else:
            sid = _resolve_stock_id(query)

    result = _fetch_and_upsert(sid, conn)
    if result is None:
        code_only = sid.replace(".TWO", "").replace(".TW", "")
        if re.match(r'^00\d+B$', code_only, re.IGNORECASE):
            raise HTTPException(
                status_code=404,
                detail=f"「{code_only}」為低流動性債券 ETF，Yahoo Finance 暫無資料，目前不支援查詢",
            )
        raise HTTPException(status_code=404, detail="查無此股票，請確認代號是否正確")
    return result


@router.get("/{stock_id}")
def get_stock(stock_id: str, conn=Depends(get_db)):
    row = conn.execute(text(f"""
        SELECT {_SM_COLS},
               dp.Close_Price, dp.Alert_Flag, dp.Alert_Reason, dp.Date
        FROM Stock_Master sm
        {_LATEST_PRICE_JOIN}
        WHERE sm.Stock_ID = :sid
    """), {"sid": stock_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Stock not found")
    return _row_to_dict(row)


@router.get("/{stock_id}/prices")
def get_stock_prices(
    stock_id: str,
    days: int = Query(30, ge=1, le=365),
    conn=Depends(get_db),
):
    exists = conn.execute(
        text("SELECT 1 FROM Stock_Master WHERE Stock_ID = :sid"),
        {"sid": stock_id},
    ).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Stock not found")

    rows = conn.execute(text("""
        SELECT Date, Close_Price, Volume, Alert_Flag, Alert_Reason
        FROM Daily_Prices
        WHERE Stock_ID = :sid
        ORDER BY Date DESC
        LIMIT :days
    """), {"sid": stock_id, "days": days}).fetchall()

    return [
        {
            "date": str(r.Date),
            "close_price": r.Close_Price,
            "volume": r.Volume,
            "alert_flag": bool(r.Alert_Flag),
            "alert_reason": r.Alert_Reason,
        }
        for r in rows
    ]


@router.get("/{stock_id}/dividends")
def get_stock_dividends(
    stock_id: str,
    months: int = Query(24, ge=1, le=120),
    conn=Depends(get_db),
):
    """個股近 N 個月現金股利發放紀錄（供詳情頁股利折線圖；6/12/24 月）。"""
    exists = conn.execute(
        text("SELECT 1 FROM Stock_Master WHERE Stock_ID = :sid"),
        {"sid": stock_id},
    ).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Stock not found")

    cutoff = (datetime.now() - timedelta(days=int(months * 30.44))).date()
    rows = conn.execute(text("""
        SELECT Ex_Date, Cash_Dividend, Stock_Dividend
        FROM Dividends
        WHERE Stock_ID = :sid AND Ex_Date >= :cutoff
        ORDER BY Ex_Date ASC
    """), {"sid": stock_id, "cutoff": str(cutoff)}).fetchall()

    return [
        {
            "date": str(r.Ex_Date),
            "cash": r.Cash_Dividend,
            "stock": r.Stock_Dividend,
            "total": round((r.Cash_Dividend or 0) + (r.Stock_Dividend or 0), 4),
        }
        for r in rows
    ]
