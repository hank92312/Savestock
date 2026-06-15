"""年度股利報表：伺服器端渲染、可列印、可分享（持股編碼於網址）。

計算口徑 import 自共用模組 core.dividend_calc，與 FastAPI App 完全一致；
股利資料以 Django ORM 讀取 Neon（managed=False 模型）。
"""

import base64
import binascii
import json
from datetime import date

from django.db.models import Sum
from django.shortcuts import render

from core.dividend_calc import (
    StockDividendData,
    estimate_portfolio,
    DISCLAIMER,
    VALID_BASIS,
    BASIS_1Y,
)
from core.twse_dividends import fetch_announced_annual

from .models import Dividend, StockMaster

_HISTORY_YEARS = 3


def _decode_holdings(raw: str):
    """解碼網址參數 d（base64url(JSON)）為持股清單。格式：[{"s","q","b"}]。"""
    if not raw:
        return []
    try:
        padded = raw + "=" * (-len(raw) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return []
    holdings = []
    for h in data:
        try:
            sid = str(h["s"]).upper()
            qty = int(h["q"])
        except (KeyError, TypeError, ValueError):
            continue
        if qty <= 0:
            continue
        basis = h.get("b", BASIS_1Y)
        holdings.append(
            {"stock_id": sid, "quantity": qty,
             "basis": basis if basis in VALID_BASIS else BASIS_1Y}
        )
    return holdings


def _build_stock_data(stock_ids):
    """以 ORM 讀 Neon，組出 {sid: StockDividendData}。"""
    year_start = date(date.today().year, 1, 1)
    masters = {m.stock_id: m for m in StockMaster.objects.filter(stock_id__in=stock_ids)}
    announced = fetch_announced_annual()  # 證交所已公告年配股（快取，失敗回空）
    result = {}
    for sid in stock_ids:
        m = masters.get(sid)
        if m is None:
            continue
        agg = Dividend.objects.filter(stock_id=sid, ex_date__gte=year_start).aggregate(
            c=Sum("cash_dividend"), s=Sum("stock_dividend")
        )
        paid = (agg["c"] or 0) + (agg["s"] or 0)
        code = sid.replace(".TWO", "").replace(".TW", "")
        ann = announced.get(code)
        result[sid] = StockDividendData(
            stock_id=m.stock_id,
            name=m.name,
            dividend_1y=m.dividend_1y,
            avg_dividend_5y=m.avg_dividend_5y,
            paid_this_year=paid if paid > 0 else None,
            announced_this_year=ann["amount"] if ann else None,
        )
    return result


def _histories(stock_ids):
    """各檔近 N 年配息紀錄（供報表明細表）。"""
    cutoff = date(date.today().year - _HISTORY_YEARS, 1, 1)
    out = {sid: [] for sid in stock_ids}
    rows = Dividend.objects.filter(
        stock_id__in=stock_ids, ex_date__gte=cutoff
    ).order_by("ex_date")
    for r in rows:
        out.setdefault(r.stock_id, []).append(
            {"date": r.ex_date, "cash": r.cash_dividend,
             "stock": r.stock_dividend, "total": r.total}
        )
    return out


def landing(request):
    return render(request, "report/landing.html")


def report(request):
    holdings = _decode_holdings(request.GET.get("d", ""))
    if not holdings:
        return render(request, "report/report.html", {"empty": True})

    stock_ids = list({h["stock_id"] for h in holdings})
    stock_data = _build_stock_data(stock_ids)
    result = estimate_portfolio(holdings, stock_data)
    histories = _histories(stock_ids)

    # 把歷史配息掛到每個 item 上，方便模板顯示
    for item in result["items"]:
        item["history"] = histories.get(item["stock_id"], [])

    high_impact_ids = {it["stock_id"] for it in result["high_impact"]}
    for item in result["items"]:
        item["is_high_impact"] = item["stock_id"] in high_impact_ids

    result["total_paid"] = round(
        sum(it["paid_this_year"] for it in result["items"]), 2
    )

    return render(
        request,
        "report/report.html",
        {
            "empty": False,
            "result": result,
            "disclaimer": DISCLAIMER,
            "today": date.today(),
            "year": date.today().year,
        },
    )
