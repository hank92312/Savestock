"""年度股利報表：伺服器端渲染、可列印、可分享（持股編碼於網址）。

計算口徑 import 自共用模組 core.dividend_calc，與 FastAPI App 完全一致；
股利資料以 Django ORM 讀取 Neon（managed=False 模型）。
"""

import base64
import binascii
import json
from datetime import date, timedelta

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.dividend_calc import (
    StockDividendData,
    estimate_portfolio,
    DISCLAIMER,
    VALID_BASIS,
    BASIS_1Y,
)
from core.twse_dividends import fetch_announced_annual
from core.etf_analytics import (
    overlap_consensus,
    hidden_winners,
    weight_matrix,
    ai_stock_selection,
)

from .models import (
    Dividend,
    StockMaster,
    DailyPrice,
    EtfMaster,
    EtfHolding,
    EtfHoldingHistory,
)

_HISTORY_YEARS = 3

# ETF 族群顯示順序與中文標題（dashboard 分群卡片用）
ETF_CATEGORY_ORDER = ["Tech", "AI", "Custom"]
ETF_CATEGORY_LABELS = {
    "Tech": "綜合型科技 / 資訊科技類",
    "AI": "AI / 創新科技主題類",
    "Custom": "我的自訂 ETF",
}
_WEIGHT_TREND_DAYS = 10  # 近 10 天權重趨勢


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


# ── ETF 追蹤模組視圖 ─────────────────────────────────────────────────
def etf_dashboard(request):
    """ETF Dashboard：依族群分組顯示所有追蹤中的 ETF 卡片。"""
    etfs = list(EtfMaster.objects.all())
    by_cat: dict[str, list] = {}
    for e in etfs:
        by_cat.setdefault(e.category or "Custom", []).append(e)

    # 依既定順序輸出族群；未知族群殿後
    ordered = ETF_CATEGORY_ORDER + [c for c in by_cat if c not in ETF_CATEGORY_ORDER]
    groups = [
        {
            "key": cat,
            "label": ETF_CATEGORY_LABELS.get(cat, cat),
            "etfs": sorted(by_cat[cat], key=lambda x: x.etf_id),
        }
        for cat in ordered
        if by_cat.get(cat)
    ]
    return render(request, "report/etf_dashboard.html", {"groups": groups})


def _latest_close_map(stock_ids):
    """一次取多檔個股各自的最新收盤價：{stock_id: close 或 None}。"""
    out = {sid: None for sid in stock_ids}
    # 逐檔取最新一筆（成分股僅 Top N，數量小；order_by 已 -date）
    for sid in stock_ids:
        dp = DailyPrice.objects.filter(stock_id=sid).order_by("-date").first()
        if dp:
            out[sid] = round(dp.close_price, 2)
    return out


def etf_holdings(request, etf_id):
    """ETF 成分股詳情頁：Top N 表格 + 權重圓餅 + 核心個股近 10 天權重折線。"""
    etf = EtfMaster.objects.filter(etf_id=etf_id).first()
    if etf is None:
        return render(request, "report/etf_holdings.html", {"not_found": True, "etf_id": etf_id})

    holdings = list(EtfHolding.objects.filter(etf_id=etf_id).order_by("-weight"))
    closes = _latest_close_map([h.stock_id for h in holdings])

    rows = []
    for h in holdings:
        close = closes.get(h.stock_id)
        rows.append({
            "code": h.stock_id,
            "name": h.stock_name or h.stock_id,
            "weight": round(h.weight or 0.0, 2),
            "close": close,               # None → 模板顯示「更新中」
        })

    # 圓餅圖：Top N 權重分佈
    pie_labels = [r["code"] for r in rows]
    pie_data = [r["weight"] for r in rows]

    # 近 10 天權重趨勢：以權重最高的核心個股為預設對象
    trend_labels, trend_data, core = [], [], None
    if holdings:
        core = holdings[0]
        hist = list(
            EtfHoldingHistory.objects.filter(etf_id=etf_id, stock_id=core.stock_id)
            .order_by("date")
        )[-_WEIGHT_TREND_DAYS:]
        trend_labels = [h.date.strftime("%m/%d") for h in hist]
        trend_data = [round(h.weight or 0.0, 2) for h in hist]

    snapshot_date = holdings[0].snapshot_date if holdings else None
    return render(request, "report/etf_holdings.html", {
        "not_found": False,
        "etf": etf,
        "rows": rows,
        "pie_labels": pie_labels,
        "pie_data": pie_data,
        "core_stock": {"code": core.stock_id, "name": core.stock_name} if core else None,
        "trend_labels": trend_labels,
        "trend_data": trend_data,
        "trend_days": _WEIGHT_TREND_DAYS,
        "snapshot_date": snapshot_date,
    })


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


# ── ETF 進階分析（四大模組）─────────────────────────────────────────
_MOMENTUM_DAYS = 90  # 近 3 個月動能


def _compute_momentum(stock_ids):
    """近 3 月漲跌幅%：{stock_id: pct}。一次查回窗內所有價，Python 端分組計算。"""
    if not stock_ids:
        return {}
    cutoff = date.today() - timedelta(days=_MOMENTUM_DAYS)
    rows = (DailyPrice.objects.filter(stock_id__in=list(stock_ids), date__gte=cutoff)
            .order_by("stock_id", "date")
            .values_list("stock_id", "date", "close_price"))
    first, last = {}, {}
    for sid, _d, close in rows:
        if close is None:
            continue
        if sid not in first:
            first[sid] = close        # 窗內最早
        last[sid] = close             # 窗內最新
    out = {}
    for sid in first:
        base = first[sid]
        if base and base > 0:
            out[sid] = round((last[sid] - base) / base * 100, 2)
    return out


def etf_analytics(request):
    """四大分析：重疊共識股、隱藏強勢股、權重熱力圖、AI 三因子選股。

    支援手動選擇 ETF（?etfs=00881.TW,00851.TW）；未指定＝一鍵分析全部。
    """
    all_etfs = list(EtfMaster.objects.all().order_by("etf_id"))
    sel_raw = request.GET.get("etfs", "").strip()
    selected = [s for s in sel_raw.split(",") if s] if sel_raw else []

    qs = EtfHolding.objects.all()
    if selected:
        qs = qs.filter(etf_id__in=selected)
    holdings = [
        {"etf_id": h.etf_id, "stock_id": h.stock_id,
         "name": h.stock_name or h.stock_id, "weight": h.weight or 0.0}
        for h in qs
    ]

    consensus = overlap_consensus(holdings)[:30]
    hidden = hidden_winners(holdings)[:30]

    momentum = _compute_momentum({h["stock_id"] for h in holdings})
    ai = ai_stock_selection(holdings, momentum=momentum, top_n=20, min_etf_count=1)

    # 熱力圖：取重疊數最高的前 15 檔個股 × 參與分析的 ETF
    hm = weight_matrix(holdings, limit_stocks=15)
    max_w = max((c for row in hm["matrix"] for c in row), default=0.0) or 1.0
    heat_rows = []
    for srow, wrow in zip(hm["stocks"], hm["matrix"]):
        cells = [{"w": w, "alpha": round(w / max_w, 3) if w > 0 else 0.0} for w in wrow]
        heat_rows.append({"code": srow["stock_id"], "name": srow["name"], "cells": cells})

    # 圖表資料（Chart.js）
    consensus_top = consensus[:15]
    hidden_top = hidden[:15]

    return render(request, "report/etf_analytics.html", {
        "all_etfs": all_etfs,
        "selected": selected,
        "is_all": not selected,
        "etf_count": len({h["etf_id"] for h in holdings}),
        "consensus": consensus,
        "hidden": hidden,
        "ai": ai,
        "heatmap": {"etfs": hm["etfs"], "rows": heat_rows},
        # 圖表 JSON
        "c_labels": [r["stock_id"] for r in consensus_top],
        "c_counts": [r["etf_count"] for r in consensus_top],
        "c_weights": [r["total_weight"] for r in consensus_top],
        "h_labels": [r["stock_id"] for r in hidden_top],
        "h_scores": [r["hidden_score"] for r in hidden_top],
        "ai_labels": [r["stock_id"] for r in ai],
        "ai_scores": [r["ai_score"] for r in ai],
    })


# ── 使用者自訂 ETF：新增 / 刪除 ─────────────────────────────────────
def _normalize_etf_id(raw: str) -> str:
    """使用者輸入的代號正規化：無後綴視為台股 ETF，補 .TW（如 0050 → 0050.TW）。"""
    s = (raw or "").strip().upper()
    return s if ("." in s or not s) else f"{s}.TW"


@require_POST
def etf_add(request):
    """新增自訂 ETF：驗證代號→抓成分股→台股名轉中文→寫入 DB（Is_Custom=1）。

    成分股個股收盤價不在此同步抓取（太慢），改由每日 ETL 自動補上。
    """
    # 延遲 import：只有真的要新增時才載入 yfinance / 名稱解析，降低 Django 啟動負擔
    import etf_source
    import name_resolver

    etf_id = _normalize_etf_id(request.POST.get("etf_id", ""))
    if not etf_id:
        messages.error(request, "請輸入 ETF 代號。")
        return redirect("etf_dashboard")

    if EtfMaster.objects.filter(etf_id=etf_id).exists():
        messages.error(request, f"{etf_id} 已在追蹤清單中。")
        return redirect("etf_dashboard")

    try:
        holdings = etf_source.fetch_etf_holdings(etf_id)
    except etf_source.SourceError:
        messages.error(request, f"找不到 {etf_id} 的成分股資料，請確認是有效的台股 ETF 代號。")
        return redirect("etf_dashboard")

    etf_name = name_resolver.resolve_name(etf_id, etf_id)
    today = date.today()
    EtfMaster.objects.create(
        etf_id=etf_id, name=etf_name, category="Custom", is_custom=True, owner_user_id=None
    )
    for h in holdings:
        nm = name_resolver.resolve_name(h["stock_id"], h["name"])
        EtfHolding.objects.create(
            etf_id=etf_id, stock_id=h["stock_id"], stock_name=nm,
            weight=h["weight"], snapshot_date=today,
        )
        EtfHoldingHistory.objects.create(
            etf_id=etf_id, stock_id=h["stock_id"], date=today, weight=h["weight"],
        )

    messages.success(request, f"已新增 {etf_name}（{etf_id}），共 {len(holdings)} 檔成分股。收盤價將於下次盤後更新。")
    return redirect("etf_holdings", etf_id=etf_id)


@require_POST
def etf_delete(request, etf_id):
    """刪除自訂 ETF（僅限 Is_Custom；預設 16 檔不可刪）。"""
    etf = EtfMaster.objects.filter(etf_id=etf_id).first()
    if etf is None or not etf.is_custom:
        messages.error(request, "只能刪除自己新增的 ETF。")
        return redirect("etf_dashboard")

    EtfHolding.objects.filter(etf_id=etf_id).delete()
    EtfHoldingHistory.objects.filter(etf_id=etf_id).delete()
    EtfMaster.objects.filter(etf_id=etf_id).delete()
    messages.success(request, f"已移除 {etf.name}（{etf_id}）。")
    return redirect("etf_dashboard")
