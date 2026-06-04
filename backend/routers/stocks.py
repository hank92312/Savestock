from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from database import get_db

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


@router.get("/")
def get_default_stocks(conn=Depends(get_db)):
    rows = conn.execute(text(f"""
        SELECT sm.Stock_ID, sm.Name, sm.Sector, sm.Avg_Dividend_2Y,
               dp.Close_Price, dp.Alert_Flag, dp.Alert_Reason, dp.Date
        FROM Stock_Master sm
        {_LATEST_PRICE_JOIN}
        ORDER BY
            CASE WHEN sm.Avg_Dividend_2Y > 0 AND dp.Close_Price > 0
                 THEN sm.Avg_Dividend_2Y / dp.Close_Price * 100
                 ELSE 0 END DESC
    """)).fetchall()
    return [_row_to_dict(r) for r in rows]


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
