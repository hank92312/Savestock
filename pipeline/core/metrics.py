"""Savestock v2 — 投資指標、自適應警示、存股健康分數與穿透持股計算引擎。

純函式設計（不依賴網路或檔案系統），方便單元測試與驗證。
"""
from __future__ import annotations

import math
from typing import Optional

# ── 產業預設最低跌幅閾值（%）：作自適應閾值的地板 ───────────────────
SECTOR_FLOOR_DROP_PCT: dict[str, float] = {
    "Construction": 6.0,
    "建材營造": 6.0,
    "Semiconductor": 5.0,
    "半導體業": 5.0,
    "ETF": 3.5,
    "高股息ETF": 3.0,
    "Food": 3.0,
    "食品工業": 3.0,
    "Finance": 2.5,
    "金融保險": 2.5,
    "金融保險業": 2.5,
    "Telecom": 2.5,
    "通信網路業": 2.5,
}
DEFAULT_FLOOR_DROP_PCT = 3.5

# 二代健保補充保費門檻（單次股利 >= 20,000 元扣 2.11%）
NHI_SURCHARGE_THRESHOLD = 20000.0
NHI_SURCHARGE_RATE = 0.0211


def calc_nhi_surcharge(single_payout_amount: float) -> float:
    """計算單次配息應扣之二代健保補充保費（2.11%）。"""
    if single_payout_amount >= NHI_SURCHARGE_THRESHOLD:
        return round(single_payout_amount * NHI_SURCHARGE_RATE)
    return 0.0


def calc_price_bands(avg_div: Optional[float]) -> Optional[dict]:
    """以平均股利計算殖利率法三段價格帶：
    便宜價 = 股利 ÷ 6%（殖利率 ≥ 6%）
    合理價 = 股利 ÷ 5%（殖利率 ≈ 5%）
    昂貴價 = 股利 ÷ 4%（殖利率 ≤ 4%）
    """
    if not avg_div or avg_div <= 0:
        return None
    return {
        "cheap": round(avg_div / 0.06, 2),
        "fair": round(avg_div / 0.05, 2),
        "expensive": round(avg_div / 0.04, 2),
    }


def classify_price_zone(price: Optional[float], bands: Optional[dict]) -> str:
    """判斷目前股價落在哪個價格區間：cheap / fair / warm / expensive / unknown。"""
    if not price or price <= 0 or not bands:
        return "unknown"
    if price <= bands["cheap"]:
        return "cheap"       # 便宜區（殖利率 ≥ 6%）
    if price <= bands["fair"]:
        return "fair"        # 合理偏低（殖利率 5%～6%）
    if price <= bands["expensive"]:
        return "warm"        # 合理偏高（殖利率 4%～5%）
    return "expensive"       # 昂貴區（殖利率 < 4%）


def calc_percentile(current: Optional[float], history: list[float]) -> Optional[int]:
    """計算 current 在 history 中的百分位（0–100）。"""
    if current is None or not history:
        return None
    valid = [x for x in history if x is not None and not math.isnan(x) and x > 0]
    if len(valid) < 5:
        return None
    below = sum(1 for x in valid if x <= current)
    return int(round(below / len(valid) * 100))


def calc_dividend_quality(annual_divs: dict[int, float], current_year: int, eps_ttm: Optional[float] = None) -> dict:
    """從歷年股利 {西元年: 每股股利合計} 計算：
    - consec_years：連續配息年數（允許當年度尚未除息時從去年算起）
    - div_cv_5y：近 5 年股利變異係數（標準差 ÷ 平均，越低越穩）
    - cagr_5y：近 5 年股利年化成長率（%）
    - payout_ratio：盈餘配發率（%，最新年度股利 ÷ EPS）
    """
    if not annual_divs:
        return {
            "consec_years": 0,
            "div_cv_5y": None,
            "cagr_5y": None,
            "payout_ratio": None,
        }

    # 1. 連續配息年數：若今年已配 >0 從今年算，否則從去年往回數
    start_yr = current_year if annual_divs.get(current_year, 0) > 0 else current_year - 1
    consec = 0
    yr = start_yr
    while annual_divs.get(yr, 0) > 0:
        consec += 1
        yr -= 1

    # 2. 近 5 個完整年度股利（current_year-5 .. current_year-1）
    five_yrs = [annual_divs.get(y, 0.0) for y in range(current_year - 5, current_year)]
    positive_5y = [v for v in five_yrs if v > 0]
    div_cv = None
    if len(positive_5y) >= 3:
        mean = sum(five_yrs) / len(five_yrs)
        if mean > 0:
            var = sum((x - mean) ** 2 for x in five_yrs) / len(five_yrs)
            div_cv = round(math.sqrt(var) / mean, 3)

    # 3. 5Y CAGR
    cagr_5y = None
    d_start = annual_divs.get(current_year - 5, 0.0)
    d_end = annual_divs.get(current_year - 1, 0.0)
    if d_start > 0 and d_end > 0:
        cagr_5y = round(((d_end / d_start) ** (1 / 4) - 1) * 100, 2)

    # 4. 盈餘配發率
    payout_ratio = None
    latest_div = annual_divs.get(current_year - 1) or annual_divs.get(current_year)
    if latest_div and latest_div > 0 and eps_ttm and eps_ttm > 0:
        payout_ratio = round(latest_div / eps_ttm * 100, 1)

    return {
        "consec_years": consec,
        "div_cv_5y": div_cv,
        "cagr_5y": cagr_5y,
        "payout_ratio": payout_ratio,
    }


def calc_risk_and_adaptive_alert(
    closes: list[float],
    volumes: list[int],
    sector: str = "Other",
) -> dict:
    """從由舊到新排列的收盤價與成交量序列計算：
    - volatility_1y：年化波動度（%）
    - max_drawdown_1y：近 1 年最大回撤（%，負值）
    - adaptive_drop_threshold：自適應暴跌門檻（%，max(產業地板, 2.5 × 60日日報酬標準差)）
    - alert_flag / alert_reasons：今日是否觸發異常下跌或「下跌爆量」警示
    """
    floor_pct = SECTOR_FLOOR_DROP_PCT.get(sector, DEFAULT_FLOOR_DROP_PCT)
    if len(closes) < 2:
        return {
            "volatility_1y": None,
            "max_drawdown_1y": None,
            "adaptive_drop_threshold": floor_pct,
            "alert_flag": False,
            "alert_reasons": [],
            "vol_info": None,
        }

    # 日報酬率（%）
    returns_pct = [
        (closes[i] - closes[i - 1]) / closes[i - 1] * 100
        for i in range(1, len(closes))
        if closes[i - 1] > 0
    ]

    # 年化波動度（近 252 交易日）
    r_1y = returns_pct[-252:]
    vol_1y = None
    if len(r_1y) >= 10:
        mean_r = sum(r_1y) / len(r_1y)
        std_r = math.sqrt(sum((x - mean_r) ** 2 for x in r_1y) / len(r_1y))
        vol_1y = round(std_r * math.sqrt(252), 2)

    # 近 60 日標準差 → 自適應暴跌閾值
    r_60d = returns_pct[-60:]
    if len(r_60d) >= 10:
        m60 = sum(r_60d) / len(r_60d)
        std60 = math.sqrt(sum((x - m60) ** 2 for x in r_60d) / len(r_60d))
        adaptive_pct = round(max(floor_pct, min(8.5, 2.5 * std60)), 2)
    else:
        adaptive_pct = floor_pct

    # 近 1 年最大回撤
    c_1y = closes[-252:]
    peak = c_1y[0]
    mdd = 0.0
    for c in c_1y:
        if c > peak:
            peak = c
        if peak > 0:
            dd = (c - peak) / peak * 100
            if dd < mdd:
                mdd = dd

    # 今日漲跌與量比
    today_chg = returns_pct[-1] if returns_pct else 0.0
    vol_ratio = 1.0
    if len(volumes) >= 5:
        avg_v20 = sum(volumes[-21:-1] or volumes[:-1]) / max(len(volumes[-21:-1] or volumes[:-1]), 1)
        if avg_v20 > 0:
            vol_ratio = volumes[-1] / avg_v20

    reasons: list[str] = []
    vol_info: Optional[str] = None
    if today_chg <= -adaptive_pct:
        reasons.append(f"異常跌幅 {today_chg:.2f}%（超過門檻 -{adaptive_pct:.1f}%）")
    if vol_ratio >= 2.5:
        if today_chg < 0:
            reasons.append(f"下跌爆量 {vol_ratio:.1f} 倍")
        else:
            vol_info = f"上漲出量 {vol_ratio:.1f} 倍"

    return {
        "volatility_1y": vol_1y,
        "max_drawdown_1y": round(mdd, 2),
        "adaptive_drop_threshold": adaptive_pct,
        "alert_flag": bool(reasons),
        "alert_reasons": reasons,
        "vol_info": vol_info,
    }


def calc_stock_health_score(
    *,
    is_etf: bool = False,
    yield_1y: Optional[float] = None,
    yield_5y: Optional[float] = None,
    consec_years: int = 0,
    div_cv_5y: Optional[float] = None,
    payout_ratio: Optional[float] = None,
    fill_rate_5y: Optional[float] = None,
    pe: Optional[float] = None,
    price_zone: str = "unknown",
    rev_yoy: Optional[float] = None,
    eps_ttm: Optional[float] = None,
    volatility_1y: Optional[float] = None,
    insti_net_5d: Optional[float] = None,
    etf_expense_pct: Optional[float] = None,
    etf_discount_pct: Optional[float] = None,
) -> dict:
    """計算 0–100 存股健康分數與白話加減分理由（完全透明可解釋）。"""
    positives: list[str] = []
    cautions: list[str] = []

    # 1. 股利品質（滿分 35）
    div_score = 0
    if consec_years >= 15:
        div_score += 14
        positives.append(f"連續配息 {consec_years} 年，長期配息紀錄極佳")
    elif consec_years >= 10:
        div_score += 11
        positives.append(f"連續配息 {consec_years} 年")
    elif consec_years >= 5:
        div_score += 8
    elif consec_years >= 1:
        div_score += 4
    else:
        cautions.append("尚無穩定連續配息紀錄")

    if div_cv_5y is not None:
        if div_cv_5y <= 0.15:
            div_score += 8
            positives.append("近 5 年配息金額非常穩定")
        elif div_cv_5y <= 0.30:
            div_score += 5
        elif div_cv_5y > 0.50:
            div_score += 1
            cautions.append("歷年配息金額起伏較大（景氣循環或大小年）")
    else:
        div_score += 4

    if is_etf:
        div_score += 8
    elif payout_ratio is not None:
        if 40 <= payout_ratio <= 85:
            div_score += 8
            positives.append(f"盈餘配發率 {payout_ratio:.0f}%，配息有獲利支撐")
        elif 85 < payout_ratio <= 100:
            div_score += 5
        elif payout_ratio > 100:
            div_score += 1
            cautions.append(f"配發率達 {payout_ratio:.0f}%（超額配息，留意是否動用老本）")
        else:
            div_score += 4
    else:
        div_score += 5

    if fill_rate_5y is not None:
        if fill_rate_5y >= 80:
            div_score += 5
            positives.append(f"歷史填息率 {fill_rate_5y:.0f}%")
        elif fill_rate_5y >= 60:
            div_score += 3
        else:
            cautions.append(f"歷史填息率偏低（{fill_rate_5y:.0f}%），留意貼息風險")
    else:
        div_score += 3
    div_score = min(35, div_score)

    # 2. 估值與成本位階（滿分 25）
    val_score = 12
    if price_zone == "cheap":
        val_score = 23
        positives.append("目前股價位於平均股利便宜區（殖利率 ≥ 6%）")
    elif price_zone == "fair":
        val_score = 19
        positives.append("目前股價位於合理偏低區（殖利率 5%～6%）")
    elif price_zone == "warm":
        val_score = 14
    elif price_zone == "expensive":
        val_score = 8
        if not is_etf:
            cautions.append("目前股價高於殖利率法昂貴價（殖利率 < 4%）")

    if not is_etf and yield_1y and yield_5y and yield_5y > 0:
        if yield_1y > yield_5y * 1.6 and (rev_yoy is not None and rev_yoy < -10):
            val_score = max(4, val_score - 6)
            cautions.append("近一年殖利率異常高於 5 年均值且營收衰退，提防高殖利率陷阱")

    if is_etf:
        if etf_expense_pct is not None:
            if etf_expense_pct <= 0.45:
                val_score = min(25, val_score + 3)
                positives.append(f"內扣總費用率低（{etf_expense_pct:.2f}%）")
            elif etf_expense_pct >= 0.90:
                val_score = max(5, val_score - 3)
                cautions.append(f"內扣總費用率偏高（{etf_expense_pct:.2f}%）")
        if etf_discount_pct is not None and etf_discount_pct >= 1.0:
            val_score = max(4, val_score - 5)
            cautions.append(f"目前溢價 {etf_discount_pct:.2f}%（高於淨值超過 1%，留意追高風險）")
    val_score = min(25, max(0, val_score))

    # 3. 基本面趨勢（滿分 25）
    fund_score = 15
    if is_etf:
        fund_score = 20
    else:
        if eps_ttm is not None:
            if eps_ttm > 0:
                fund_score += 4
            else:
                fund_score -= 8
                cautions.append("近四季累計 EPS 為虧損")
        if rev_yoy is not None:
            if rev_yoy >= 10:
                fund_score += 6
                positives.append(f"最新月營收年增 +{rev_yoy:.1f}%，基本面成長")
            elif rev_yoy >= 0:
                fund_score += 3
            elif rev_yoy <= -15:
                fund_score -= 5
                cautions.append(f"最新月營收年減 {rev_yoy:.1f}%，動能轉弱")
        if pe is not None and 0 < pe <= 16:
            fund_score += 2
    fund_score = min(25, max(0, fund_score))

    # 4. 籌碼與波動風險（滿分 15）
    risk_score = 10
    if volatility_1y is not None:
        if volatility_1y <= 18:
            risk_score += 3
            positives.append(f"年化波動度低（{volatility_1y:.1f}%），股價穩健")
        elif volatility_1y >= 35:
            risk_score -= 3
            cautions.append(f"年化波動度較高（{volatility_1y:.1f}%）")
    if insti_net_5d is not None:
        if insti_net_5d > 0:
            risk_score += 2
        elif insti_net_5d < 0:
            risk_score -= 1
    risk_score = min(15, max(0, risk_score))

    total = int(round(div_score + val_score + fund_score + risk_score))
    if total >= 80:
        grade = "A"
    elif total >= 70:
        grade = "B+"
    elif total >= 60:
        grade = "B"
    elif total >= 50:
        grade = "C"
    else:
        grade = "D"

    return {
        "total": total,
        "grade": grade,
        "dimensions": [
            {"key": "dividend", "label": "股利品質", "score": div_score, "max": 35},
            {"key": "valuation", "label": "估值與成本", "score": val_score, "max": 25},
            {"key": "fundamentals", "label": "基本面趨勢", "score": fund_score, "max": 25},
            {"key": "chips_risk", "label": "籌碼與風險", "score": risk_score, "max": 15},
        ],
        "positives": positives[:3],
        "cautions": cautions[:3],
    }


def calc_etf_lookthrough(
    user_positions: list[dict],
    etf_holdings_map: dict[str, list[dict]],
) -> list[dict]:
    """計算『我的組合穿透持股（Look-through Exposure）』：
    輸入：
      user_positions = [{"code": "0056", "market_value": 100000}, {"code": "2330", "market_value": 50000}]
      etf_holdings_map = {"0056": [{"stock_id": "2330", "name": "台積電", "weight": 8.5}, ...]}
    輸出依穿透總金額降序排列的真實底層個股曝險列表。
    """
    total_portfolio_val = sum(float(p.get("market_value") or 0) for p in user_positions)
    if total_portfolio_val <= 0:
        return []

    exposure: dict[str, dict] = {}
    for pos in user_positions:
        code = pos["code"].replace(".TW", "").replace(".TWO", "")
        val = float(pos.get("market_value") or 0)
        if val <= 0:
            continue
        holdings = etf_holdings_map.get(code) or etf_holdings_map.get(f"{code}.TW")
        if holdings:
            for h in holdings:
                sid = h["stock_id"].replace(".TW", "").replace(".TWO", "")
                w = float(h.get("weight") or 0) / 100.0
                contrib = val * w
                if contrib <= 0:
                    continue
                rec = exposure.setdefault(sid, {
                    "code": sid,
                    "name": h.get("name") or sid,
                    "exposed_value": 0.0,
                    "sources": [],
                })
                rec["exposed_value"] += contrib
                rec["sources"].append({"from": code, "weight_pct": round(w * 100, 2), "value": round(contrib)})
        else:
            rec = exposure.setdefault(code, {
                "code": code,
                "name": pos.get("name") or code,
                "exposed_value": 0.0,
                "sources": [],
            })
            rec["exposed_value"] += val
            rec["sources"].append({"from": "直接持有", "weight_pct": 100.0, "value": round(val)})

    result = []
    for rec in exposure.values():
        result.append({
            "code": rec["code"],
            "name": rec["name"],
            "exposed_value": round(rec["exposed_value"]),
            "portfolio_pct": round(rec["exposed_value"] / total_portfolio_val * 100, 2),
            "sources": rec["sources"],
        })
    result.sort(key=lambda x: x["exposed_value"], reverse=True)
    return result


def calc_etf_pairwise_overlap(etf_holdings_map: dict[str, list[dict]]) -> dict:
    """計算多檔 ETF 兩兩之間的權重重疊度矩陣（Overlap Weight %）：
    Overlap(A, B) = sum_s min(weight_A(s), weight_B(s))
    """
    etf_ids = sorted(etf_holdings_map.keys())
    w_maps: dict[str, dict[str, float]] = {}
    for eid in etf_ids:
        w_maps[eid] = {
            h["stock_id"].replace(".TW", "").replace(".TWO", ""): float(h.get("weight") or 0.0)
            for h in etf_holdings_map[eid]
        }

    matrix: list[list[float]] = []
    for a in etf_ids:
        row: list[float] = []
        for b in etf_ids:
            if a == b:
                row.append(100.0)
            else:
                common = set(w_maps[a].keys()) & set(w_maps[b].keys())
                overlap = sum(min(w_maps[a][s], w_maps[b][s]) for s in common)
                row.append(round(overlap, 2))
        matrix.append(row)

    return {"etfs": etf_ids, "matrix": matrix}
