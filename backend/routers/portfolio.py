"""個人年度股利估算 API（供 Flutter App 使用）。

計算邏輯委派給框架無關的 core.dividend_calc，與未來的 Django 報表共用同一份口徑。
本檔只負責：接收持股 → 從 DB 備妥股利資料（缺漏者即時補抓）→ 呼叫純計算模組 → 回傳。
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from pydantic import BaseModel, Field
from typing import List
from datetime import date
from concurrent.futures import ThreadPoolExecutor

from database import get_db, engine
from routers.stocks import _fetch_and_upsert
from core.dividend_calc import (
    StockDividendData, estimate_portfolio, VALID_BASIS, BASIS_1Y, DISCLAIMER,
)
from core.twse_dividends import fetch_announced_annual

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class Holding(BaseModel):
    stock_id: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)          # 零股：任意正整數股數
    basis: str = BASIS_1Y                     # 今年未公布時的估算基準：1y / 5y

    def normalized_basis(self) -> str:
        return self.basis if self.basis in VALID_BASIS else BASIS_1Y


class EstimateRequest(BaseModel):
    holdings: List[Holding] = Field(..., min_length=1)


def _build_stock_data(stock_ids, conn):
    """查 DB 組出 {sid: StockDividendData}；回傳 (資料字典, DB 缺漏清單)。"""
    year_start = date(date.today().year, 1, 1)
    announced = fetch_announced_annual()  # 證交所已公告年配股（快取，失敗回空）
    result = {}
    missing = []
    for sid in stock_ids:
        row = conn.execute(text("""
            SELECT Stock_ID AS stock_id, Name AS name,
                   Dividend_1Y AS dividend_1y, Avg_Dividend_5Y AS avg_dividend_5y
            FROM Stock_Master WHERE Stock_ID = :sid
        """), {"sid": sid}).fetchone()
        if not row:
            missing.append(sid)
            continue
        paid = conn.execute(text("""
            SELECT COALESCE(SUM(Cash_Dividend), 0) + COALESCE(SUM(Stock_Dividend), 0)
            FROM Dividends WHERE Stock_ID = :sid AND Ex_Date >= :ys
        """), {"sid": sid, "ys": str(year_start)}).scalar()
        m = row._mapping
        code = sid.replace(".TWO", "").replace(".TW", "")
        ann = announced.get(code)
        result[sid] = StockDividendData(
            stock_id=m.get("stock_id"),
            name=m.get("name"),
            dividend_1y=m.get("dividend_1y"),
            avg_dividend_5y=m.get("avg_dividend_5y"),
            paid_this_year=float(paid) if paid and paid > 0 else None,
            announced_this_year=ann["amount"] if ann else None,
        )
    return result, missing


@router.post("/estimate")
def estimate(req: EstimateRequest, conn=Depends(get_db)):
    """估算投資組合今年度可領股利。DB 缺漏的股票即時並行補抓 yfinance。"""
    stock_ids = list({h.stock_id for h in req.holdings})
    stock_data, missing = _build_stock_data(stock_ids, conn)

    # DB 沒有的股票 → 並行補抓（與自選股 refresh 同一套模式），抓完重查一次
    if missing:
        def _fetch_one(sid):
            with engine.begin() as c:
                _fetch_and_upsert(sid, c)

        with ThreadPoolExecutor(max_workers=5) as ex:
            list(ex.map(_fetch_one, missing))

        refetched, _ = _build_stock_data(missing, conn)
        stock_data.update(refetched)

    holdings = [
        {"stock_id": h.stock_id, "quantity": h.quantity, "basis": h.normalized_basis()}
        for h in req.holdings
    ]
    result = estimate_portfolio(holdings, stock_data)
    result["disclaimer"] = DISCLAIMER
    result["currency"] = "TWD"
    return result
