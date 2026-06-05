from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from database import get_db
from datetime import datetime, timedelta
import yfinance as yf
import requests as req_lib

# 模組層級快取：{ 簡稱/全名 → 股票代號 }，第一次查詢時從 TWSE 載入
_tw_name_cache: dict[str, str] = {}
_tw_cache_loaded = False


def _load_tw_name_cache() -> None:
    """從 TWSE openapi 載入所有上市公司名稱→代號對應表（只載入一次）。"""
    global _tw_cache_loaded
    if _tw_cache_loaded:
        return
    try:
        r = req_lib.get(
            "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        for item in r.json():
            code = item.get("公司代號", "")
            short = item.get("公司簡稱", "")
            full = item.get("公司名稱", "")
            if code:
                if short:
                    _tw_name_cache[short] = code
                if full:
                    _tw_name_cache[full] = code
        _tw_cache_loaded = True
    except Exception:
        pass


def _search_tw_code_by_name(chinese_name: str) -> str | None:
    """用中文名稱（部分符合）查台股代號。"""
    _load_tw_name_cache()
    for name, code in _tw_name_cache.items():
        if chinese_name in name or name in chinese_name:
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
    yield_est = round(avg_div / close * 100, 2) if close and avg_div else None
    return {
        "stock_id": row.Stock_ID,
        "name": row.Name,
        "sector": row.Sector,
        "avg_dividend_2y": avg_div,
        "close_price": close,
        "estimated_yield": yield_est,
        "alert_flag": bool(row.Alert_Flag),
        "alert_reason": row.Alert_Reason,
        "last_date": str(row.Date) if row.Date else None,
    }


def _fetch_and_upsert(sid: str, conn) -> dict | None:
    """從 yfinance 抓取最新資料並寫入 DB，回傳股票 dict 或 None（查無此股）。"""
    ticker = yf.Ticker(sid)
    hist = ticker.history(period="1mo")
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
        code_only = sid.replace(".TW", "")
        name = _get_tw_chinese_name(code_only) or en_name

    # 計算近 2 年平均股利
    actions = ticker.actions
    avg_div = 0.0
    if not actions.empty and "Dividends" in actions.columns:
        two_years_ago = datetime.now() - timedelta(days=730)
        if actions.index.tzinfo:
            two_years_ago = two_years_ago.replace(tzinfo=actions.index.tzinfo)
        recent = actions[actions.index > two_years_ago]
        avg_div = float(recent["Dividends"].sum()) / 2

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
        INSERT INTO Stock_Master (Stock_ID, Name, Sector, Avg_Dividend_2Y, Is_Default, Last_Updated)
        VALUES (:sid, :name, :sector, :avg_div, 0, CURRENT_TIMESTAMP)
        ON CONFLICT (Stock_ID) DO UPDATE SET
            Avg_Dividend_2Y = EXCLUDED.Avg_Dividend_2Y,
            Last_Updated = CURRENT_TIMESTAMP
    """), {"sid": sid, "name": name, "sector": sector, "avg_div": avg_div})

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

    yield_est = round(avg_div / close * 100, 2) if close and avg_div else None
    return {
        "stock_id": sid,
        "name": name,
        "sector": sector,
        "avg_dividend_2y": avg_div,
        "close_price": close,
        "estimated_yield": yield_est,
        "alert_flag": alert_flag,
        "alert_reason": alert_reason,
        "last_date": str(today),
    }


# ── 端點 ──────────────────────────────────────────────────────

@router.get("/")
def get_default_stocks(conn=Depends(get_db)):
    rows = conn.execute(text(f"""
        SELECT sm.Stock_ID, sm.Name, sm.Sector, sm.Avg_Dividend_2Y,
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


@router.get("/lookup/{stock_id}")
def lookup_stock(stock_id: str, conn=Depends(get_db)):
    """即時查詢任意台股。支援股票代號（0050）或中文名稱（台積電）。"""
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
            # 2. 向 TWSE 查名稱對應代號
            code = _search_tw_code_by_name(query)
            if code:
                sid = f"{code}.TW"
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到「{query}」，請改用股票代號查詢（如：2330）",
                )
    else:
        sid = query.upper()
        if not sid.endswith(".TW"):
            sid = f"{sid}.TW"

    result = _fetch_and_upsert(sid, conn)
    if result is None:
        raise HTTPException(status_code=404, detail="查無此股票，請確認代號是否正確")
    return result


@router.get("/{stock_id}")
def get_stock(stock_id: str, conn=Depends(get_db)):
    row = conn.execute(text(f"""
        SELECT sm.Stock_ID, sm.Name, sm.Sector, sm.Avg_Dividend_2Y,
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
