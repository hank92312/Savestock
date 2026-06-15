"""個人年度股利估算 — 純計算邏輯，不依賴任何 web 框架或資料庫。

FastAPI（App 用）與 Django（網頁報表用）共用此模組，確保兩邊估算口徑一致，
避免重蹈 ETL / 後端股利邏輯各自維護的覆轍（見 TODONEXT.md 技術債段落）。

股利口徑與 backend/routers/stocks.py 完全一致：
  股利 = 現金股利 + 股票股利（配股面額還原）。

【為何全年估算用「近1年 / 近5年平均」而非「今年已除息」】
yfinance 只提供「已除息」的歷史配息。今年「已公布但尚未除息」的部分抓不到；
而季配 / 半年配個股（如 0056、2330），年中時「今年已除息」只是部分金額，
拿來當全年值會嚴重低估。因此全年估算一律用滾動值（近1年含完整四季、近5年平均），
「今年已除息」僅作為實際資訊併列，不混為全年估算。
真正的「今年已公布全年配息」需另接 MOPS 公開資訊觀測站（Phase 3）。
"""

from dataclasses import dataclass
from typing import Optional

# ── basis：全年估算基準 ────────────────────────────────────────────
BASIS_1Y = "1y"   # 近一年股利（滾動 12 個月，含完整配息週期）
BASIS_5Y = "5y"   # 近五年平均股利（較保守）
VALID_BASIS = {BASIS_1Y, BASIS_5Y}

# 影響較大門檻：占總額比重 ≥ 此值者列為高影響個股（其配息一旦變動最影響總額）
HIGH_IMPACT_SHARE_THRESHOLD = 10.0  # 百分比
# 若無個股跨過門檻，至少列出金額最大的前 N 檔，確保使用者知道該注意誰
HIGH_IMPACT_FALLBACK_TOP_N = 3

# 估算提示文字（FastAPI 與 Django 報表共用，確保口徑一致）
DISCLAIMER = (
    "標示「已公告」者採用公司今年正式公告之全年配息（年配股，資料來源證交所）；"
    "其餘以歷史股利推算（近1年或近5年平均），僅供參考，並非投資建議。"
    "季配／半年配個股年中尚無法得知全年完整配息，故以估算為準；"
    "實際可領金額會因公司公布配息、除息與否而變動。「今年已除息」為今年實際已配發金額。"
)


BASIS_ANNOUNCED = "announced"  # 已公告（實際公告值，非估算）


@dataclass
class StockDividendData:
    """單檔股票的股利資料（由呼叫端從 DB / yfinance / 證交所公告準備好餵入）。

    announced_this_year：今年已公告之全年配息（年配股，來自證交所 t187ap45_L）；
        非 None 時為實際公告值，優先於估算（Phase 3）。
    paid_this_year：今年已除息每股合計（實際值，僅供併列顯示）。
    """
    stock_id: str
    name: str
    dividend_1y: Optional[float]
    avg_dividend_5y: Optional[float]
    paid_this_year: Optional[float]
    announced_this_year: Optional[float] = None


def _resolve_per_share(data: StockDividendData, basis: str):
    """回傳 (每股股利, 來源, 是否為估算)。

    優先序：今年已公告全年配息 > 使用者選的估算基準（近1年 / 近5年平均）。
    已公告為實際值（不確定性最低），永遠優先。
    """
    if data.announced_this_year is not None:
        return data.announced_this_year, BASIS_ANNOUNCED, False
    if basis == BASIS_5Y:
        return (data.avg_dividend_5y or 0.0), BASIS_5Y, True
    return (data.dividend_1y or 0.0), BASIS_1Y, True


def estimate_portfolio(holdings, stock_data):
    """估算整個投資組合的今年度可領股利。

    holdings:   [{"stock_id": str, "quantity": int, "basis": "1y"|"5y"}]
    stock_data: {stock_id: StockDividendData}
    回傳 dict：{total, items, high_impact}。

    每檔 item 同時給出：
      amount          —— 全年估算金額（per_share × 股數）
      paid_this_year  —— 今年已實際除息金額（實際資訊，非估算）
    查無資料的股票以 available=False 標記、金額計 0（fail loud，不默默漏算）。
    """
    items = []
    total = 0.0
    for h in holdings:
        sid = h["stock_id"]
        qty = h["quantity"]
        data = stock_data.get(sid)
        if data is None:
            items.append({
                "stock_id": sid, "name": sid, "quantity": qty,
                "per_share": 0.0, "source": None, "is_estimated": False,
                "amount": 0.0, "paid_this_year": 0.0, "available": False,
            })
            continue
        per_share, source, is_estimated = _resolve_per_share(
            data, h.get("basis", BASIS_1Y)
        )
        amount = per_share * qty
        total += amount
        paid = (data.paid_this_year or 0.0) * qty
        items.append({
            "stock_id": data.stock_id, "name": data.name, "quantity": qty,
            "per_share": round(per_share, 4),
            "source": source, "is_estimated": is_estimated,
            "amount": round(amount, 2),
            "paid_this_year": round(paid, 2),
            "available": True,
        })

    for it in items:
        it["share_pct"] = round(it["amount"] / total * 100, 2) if total > 0 else 0.0

    # 影響較大：聚焦「估算（非已公告）」個股——已公告為確定值，不確定的才需提醒。
    # 依金額由大到小，取占比 ≥ 門檻者；若無人跨門檻，退而取前 N 大。
    estimated = sorted(
        [it for it in items if it["available"] and it["is_estimated"]],
        key=lambda x: x["amount"], reverse=True,
    )
    high_impact = [it for it in estimated if it["share_pct"] >= HIGH_IMPACT_SHARE_THRESHOLD]
    if not high_impact:
        high_impact = estimated[:HIGH_IMPACT_FALLBACK_TOP_N]

    return {
        "total": round(total, 2),
        "items": items,
        "high_impact": high_impact,
    }
