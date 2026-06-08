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

router = APIRouter(prefix="/stocks", tags=["stocks"])

_LATEST_PRICE_JOIN = """
    LEFT JOIN Daily_Prices dp ON sm.Stock_ID = dp.Stock_ID
        AND dp.Date = (SELECT MAX(Date) FROM Daily_Prices WHERE Stock_ID = sm.Stock_ID)
"""


def _row_to_dict(row):
    close = row.Close_Price
    avg_div = row.Avg_Dividend_2Y
    div_1y = row.Dividend_1Y
    yield_est = round(avg_div / close * 100, 2) if close and avg_div else None
    yield_1y = round(div_1y / close * 100, 2) if close and div_1y else None
    return {
        "stock_id": row.Stock_ID,
        "name": row.Name,
        "sector": row.Sector,
        "avg_dividend_2y": avg_div,
        "dividend_1y": div_1y,
        "listing_months": row.Listing_Months,
        "close_price": close,
        "estimated_yield": yield_est,
        "yield_1y": yield_1y,
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


def _avg_dividend(actions, listing_months: int | None) -> float:
    """上市滿2年：近2年現金股利平均(÷2)；不滿2年：上市迄今全部現金股利年化。"""
    if actions.empty or "Dividends" not in actions.columns:
        return 0.0
    is_new = listing_months is not None and listing_months < 24
    if is_new:
        total = float(actions["Dividends"].sum())
        years = listing_months / 12
        return total / years if years > 0 else total
    two_years_ago = datetime.now() - timedelta(days=730)
    if actions.index.tzinfo:
        two_years_ago = two_years_ago.replace(tzinfo=actions.index.tzinfo)
    recent = actions[actions.index > two_years_ago]
    return float(recent["Dividends"].sum()) / 2


def _dividend_1y(actions) -> float:
    """近 12 個月現金股利合計（近一年殖利率用）。"""
    if actions.empty or "Dividends" not in actions.columns:
        return 0.0
    one_year_ago = datetime.now() - timedelta(days=365)
    if actions.index.tzinfo:
        one_year_ago = one_year_ago.replace(tzinfo=actions.index.tzinfo)
    recent = actions[actions.index > one_year_ago]
    return float(recent["Dividends"].sum())


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

    # 讀取已存在資料（保留原有中文名稱與 sector）
    existing = conn.execute(
        text("SELECT Name, Sector FROM Stock_Master WHERE Stock_ID = :sid"),
        {"sid": sid},
    ).fetchone()
    sector = existing.Sector if existing else "Unknown"

    if existing:
        name = existing.Name  # 已有名稱就保留
    else:
        # 新股票：優先向 TWSE 抓中文名，失敗才用 yfinance 英文名
        code_only = sid.replace(".TWO", "").replace(".TW", "")
        name = _get_tw_chinese_name(code_only) or en_name

    # 計算平均股利（上市不滿2年改用上市迄今年化）+ 近一年股利
    listing_months = _listing_months(info)
    avg_div = _avg_dividend(ticker.actions, listing_months)
    div_1y = _dividend_1y(ticker.actions)

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
    if price_change <= -3.0:           # 自選股統一用 3% 跌幅警示
        alert_reasons.append(f"跌幅:{price_change:.2f}%")
    if vol_ratio >= 2.5:
        alert_reasons.append(f"爆量:{vol_ratio:.2f}倍")
    alert_flag = bool(alert_reasons)
    alert_reason = ", ".join(alert_reasons)

    conn.execute(text("""
        INSERT INTO Stock_Master (Stock_ID, Name, Sector, Avg_Dividend_2Y, Dividend_1Y, Listing_Months, Is_Default, Last_Updated)
        VALUES (:sid, :name, :sector, :avg_div, :div_1y, :listing_months, 0, CURRENT_TIMESTAMP)
        ON CONFLICT (Stock_ID) DO UPDATE SET
            Avg_Dividend_2Y = EXCLUDED.Avg_Dividend_2Y,
            Dividend_1Y = EXCLUDED.Dividend_1Y,
            Listing_Months = EXCLUDED.Listing_Months,
            Last_Updated = CURRENT_TIMESTAMP
    """), {"sid": sid, "name": name, "sector": sector, "avg_div": avg_div,
           "div_1y": div_1y, "listing_months": listing_months})

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

    yield_est = round(avg_div / close * 100, 2) if close and avg_div else None
    yield_1y = round(div_1y / close * 100, 2) if close and div_1y else None
    return {
        "stock_id": sid,
        "name": name,
        "sector": sector,
        "avg_dividend_2y": avg_div,
        "dividend_1y": div_1y,
        "listing_months": listing_months,
        "close_price": close,
        "estimated_yield": yield_est,
        "yield_1y": yield_1y,
        "alert_flag": alert_flag,
        "alert_reason": alert_reason,
        "last_date": str(today),
    }


# ── 端點 ──────────────────────────────────────────────────────

@router.get("/")
def get_default_stocks(conn=Depends(get_db)):
    rows = conn.execute(text(f"""
        SELECT sm.Stock_ID, sm.Name, sm.Sector, sm.Avg_Dividend_2Y, sm.Dividend_1Y, sm.Listing_Months,
               dp.Close_Price, dp.Alert_Flag, dp.Alert_Reason, dp.Date
        FROM Stock_Master sm
        {_LATEST_PRICE_JOIN}
        WHERE sm.Is_Default = 1
        ORDER BY
            CASE WHEN sm.Avg_Dividend_2Y > 0 AND dp.Close_Price > 0
                 THEN sm.Avg_Dividend_2Y / dp.Close_Price * 100
                 ELSE 0 END DESC
    """)).fetchall()
    return [_row_to_dict(r) for r in rows]


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
        SELECT sm.Stock_ID, sm.Name, sm.Sector, sm.Avg_Dividend_2Y, sm.Dividend_1Y, sm.Listing_Months,
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
