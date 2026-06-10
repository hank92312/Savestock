from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from database import get_db
from routers.stocks import _fetch_and_upsert

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    uuid: str
    email: Optional[str] = None
    oauth_provider: Optional[str] = None


class AddStockRequest(BaseModel):
    stock_id: str


@router.post("/", status_code=201)
def create_user(body: CreateUserRequest, conn=Depends(get_db)):
    existing = conn.execute(
        text("SELECT User_ID FROM Users WHERE UUID = :uuid"),
        {"uuid": body.uuid},
    ).fetchone()
    if existing:
        return {"user_id": existing._mapping.get("user_id"), "uuid": body.uuid, "created": False}

    result = conn.execute(
        text("""
            INSERT INTO Users (UUID, Email, OAuth_Provider)
            VALUES (:uuid, :email, :provider)
            RETURNING User_ID
        """),
        {"uuid": body.uuid, "email": body.email, "provider": body.oauth_provider},
    )
    user_id = result.fetchone()[0]
    conn.execute(
        text("INSERT INTO User_Licenses (User_ID, Tier_ID) VALUES (:uid, 1)"),
        {"uid": user_id},
    )
    return {"user_id": user_id, "uuid": body.uuid, "created": True}


@router.get("/{user_id}/watchlist")
def get_watchlist(user_id: int, conn=Depends(get_db)):
    if not conn.execute(
        text("SELECT 1 FROM Users WHERE User_ID = :uid"), {"uid": user_id}
    ).fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    rows = conn.execute(text("""
        SELECT sm.Stock_ID, sm.Name, sm.Sector, sm.Avg_Dividend_2Y, sm.Dividend_1Y, sm.Listing_Months,
               dp.Close_Price, dp.Alert_Flag, dp.Alert_Reason, dp.Date
        FROM User_Stocks us
        JOIN Stock_Master sm ON us.Stock_ID = sm.Stock_ID
        LEFT JOIN Daily_Prices dp ON sm.Stock_ID = dp.Stock_ID
            AND dp.Date = (SELECT MAX(Date) FROM Daily_Prices WHERE Stock_ID = sm.Stock_ID)
        WHERE us.User_ID = :uid AND us.Status = 'Active'
        ORDER BY
            CASE WHEN sm.Dividend_1Y > 0 AND dp.Close_Price > 0
                 THEN sm.Dividend_1Y / dp.Close_Price * 100
                 ELSE 0 END DESC
    """), {"uid": user_id}).fetchall()

    result = []
    for r in rows:
        m = r._mapping
        close = m.get("close_price")
        avg_div = m.get("avg_dividend_2y")
        div_1y = m.get("dividend_1y")
        result.append({
            "stock_id": m.get("stock_id"),
            "name": m.get("name"),
            "sector": m.get("sector"),
            "avg_dividend_2y": avg_div,
            "dividend_1y": div_1y,
            "listing_months": m.get("listing_months"),
            "close_price": close,
            "estimated_yield": round(avg_div / close * 100, 2) if close and avg_div else None,
            "yield_1y": round(div_1y / close * 100, 2) if close and div_1y else None,
            "alert_flag": bool(m.get("alert_flag")),
            "alert_reason": m.get("alert_reason"),
            "last_date": str(m.get("date")) if m.get("date") else None,
        })
    return result


@router.post("/{user_id}/watchlist", status_code=201)
def add_to_watchlist(user_id: int, body: AddStockRequest, conn=Depends(get_db)):
    if not conn.execute(
        text("SELECT 1 FROM Users WHERE User_ID = :uid"), {"uid": user_id}
    ).fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    if not conn.execute(
        text("SELECT 1 FROM Stock_Master WHERE Stock_ID = :sid"), {"sid": body.stock_id}
    ).fetchone():
        raise HTTPException(status_code=404, detail="Stock not found")

    existing = conn.execute(
        text("SELECT Status FROM User_Stocks WHERE User_ID = :uid AND Stock_ID = :sid"),
        {"uid": user_id, "sid": body.stock_id},
    ).fetchone()
    if existing:
        if existing._mapping.get("status") == "Active":
            raise HTTPException(status_code=409, detail="Stock already in watchlist")
        conn.execute(
            text("UPDATE User_Stocks SET Status = 'Active' WHERE User_ID = :uid AND Stock_ID = :sid"),
            {"uid": user_id, "sid": body.stock_id},
        )
        return {"message": "Stock reactivated in watchlist"}

    # 確認自選股數量未超過方案上限
    custom_count = conn.execute(text("""
        SELECT COUNT(*) FROM User_Stocks
        WHERE User_ID = :uid AND Is_Default = FALSE AND Status = 'Active'
    """), {"uid": user_id}).scalar()

    tier_limit = conn.execute(text("""
        SELECT pc.Max_Total_Stocks
        FROM User_Licenses ul
        JOIN Plan_Configs pc ON ul.Tier_ID = pc.Tier_ID
        WHERE ul.User_ID = :uid
        ORDER BY ul.Purchase_Date DESC
        LIMIT 1
    """), {"uid": user_id}).scalar() or 5  # 無授權紀錄者預設免費上限 5 檔

    if custom_count >= tier_limit:
        raise HTTPException(
            status_code=403,
            detail=f"已達方案上限（{tier_limit} 檔自選股）",
        )

    conn.execute(
        text("""
            INSERT INTO User_Stocks (User_ID, Stock_ID, Is_Default, Status)
            VALUES (:uid, :sid, FALSE, 'Active')
        """),
        {"uid": user_id, "sid": body.stock_id},
    )
    return {"message": "Stock added to watchlist"}


@router.delete("/{user_id}/watchlist/{stock_id}")
def remove_from_watchlist(user_id: int, stock_id: str, conn=Depends(get_db)):
    result = conn.execute(text("""
        UPDATE User_Stocks SET Status = 'Removed'
        WHERE User_ID = :uid AND Stock_ID = :sid AND Status = 'Active'
    """), {"uid": user_id, "sid": stock_id})

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Stock not in watchlist")
    return {"message": "Stock removed from watchlist"}


@router.post("/{user_id}/watchlist/refresh")
def refresh_watchlist(user_id: int, conn=Depends(get_db)):
    """重新從 yfinance 抓取用戶自選股的最新價格與股利，回傳更新後清單。"""
    if not conn.execute(
        text("SELECT 1 FROM Users WHERE User_ID = :uid"), {"uid": user_id}
    ).fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    rows = conn.execute(text("""
        SELECT us.Stock_ID
        FROM User_Stocks us
        WHERE us.User_ID = :uid AND us.Status = 'Active'
    """), {"uid": user_id}).fetchall()

    results = []
    errors = []
    for r in rows:
        try:
            data = _fetch_and_upsert(r._mapping.get("stock_id"), conn)
            if data:
                results.append(data)
        except Exception as e:
            errors.append({"stock_id": r._mapping.get("stock_id"), "error": str(e)})

    # 依近一年殖利率降序排序（與 GET /watchlist 一致；無殖利率者排最後）
    results.sort(key=lambda d: d.get("yield_1y") or -1, reverse=True)

    return {"updated": len(results), "errors": errors, "stocks": results}
