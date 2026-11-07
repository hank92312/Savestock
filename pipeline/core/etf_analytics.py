"""ETF 成分股進階分析 — 純計算邏輯，不依賴 web 框架或資料庫。

對應 etf_tracker.md 第 5 節四大模組：
  A 重疊成分股（機構共識股）  B 隱藏強勢股  C 權重熱力圖矩陣  D AI 三因子選股

比照 core/dividend_calc.py：輸入由呼叫端（FastAPI / Django）從 DB 準備好餵入，
本模組只做計算、回傳 dict/list，供兩邊共用同一份口徑，附單元測試。

輸入統一格式（對應 ETF_Holdings 資料列）：
    holdings = [{"etf_id": str, "stock_id": str, "name": str, "weight": float(%)}]
權重單位一律為百分比（如 41.72）。
"""
from __future__ import annotations

# 熱力圖 / AI 選股預設輸出上限
DEFAULT_HEATMAP_STOCKS = 20
DEFAULT_AI_TOP_N = 20

# 各模組「多檔持有」門檻：共識/隱藏強勢股需被 ≥ 此值檔 ETF 持有才有意義
MIN_ETF_COUNT_CONSENSUS = 2
MIN_ETF_COUNT_HIDDEN = 2

# AI 三因子預設權重（共識度、隱藏強度、動能），加權前各自標準化
AI_WEIGHTS = {"consensus": 1 / 3, "hidden": 1 / 3, "momentum": 1 / 3}


# ── 共用彙總：把 holdings 依個股聚合 ──────────────────────────────────
def _aggregate(holdings):
    """把 holdings 依 stock_id 聚合成每檔個股的跨 ETF 統計。

    回傳 {stock_id: {stock_id, name, etf_count, total_weight, avg_weight,
                     etf_list, weights_by_etf}}。
    """
    agg: dict[str, dict] = {}
    for h in holdings:
        sid = h["stock_id"]
        eid = h["etf_id"]
        w = float(h.get("weight") or 0.0)
        rec = agg.get(sid)
        if rec is None:
            rec = agg[sid] = {
                "stock_id": sid,
                "name": h.get("name") or sid,
                "etf_list": [],
                "weights_by_etf": {},
                "total_weight": 0.0,
            }
        # 同一 ETF 對同一股票理論上只有一列；若重複則取後者、不重複計數
        if eid not in rec["weights_by_etf"]:
            rec["etf_list"].append(eid)
        rec["weights_by_etf"][eid] = w
        rec["name"] = rec["name"] or h.get("name") or sid

    for rec in agg.values():
        rec["total_weight"] = round(sum(rec["weights_by_etf"].values()), 4)
        rec["etf_count"] = len(rec["etf_list"])
        rec["avg_weight"] = round(rec["total_weight"] / rec["etf_count"], 4) if rec["etf_count"] else 0.0
        rec["etf_list"] = sorted(rec["etf_list"])
    return agg


def _minmax_normalize(values):
    """min-max 標準化到 [0,1]；全相等（含單一元素）時回傳全 0，避免除以零。"""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0 for _ in values]
    span = hi - lo
    return [(v - lo) / span for v in values]


# ── 模組 A：重疊成分股（機構共識股）───────────────────────────────────
def overlap_consensus(holdings, min_etf_count: int = MIN_ETF_COUNT_CONSENSUS):
    """算多檔 ETF 共同持有的個股。

    回傳依「重疊 ETF 數 → 總權重」降序排列的列表，每筆含：
        etf_count（重疊 ETF 數）、total_weight（總權重%）、etf_list（持有它的 ETF）。
    min_etf_count：只保留被 ≥ 此值檔 ETF 持有者（共識股本義為「多檔共同持有」）。
    """
    agg = _aggregate(holdings)
    rows = [
        {
            "stock_id": r["stock_id"],
            "name": r["name"],
            "etf_count": r["etf_count"],
            "total_weight": r["total_weight"],
            "avg_weight": r["avg_weight"],
            "etf_list": r["etf_list"],
        }
        for r in agg.values()
        if r["etf_count"] >= min_etf_count
    ]
    rows.sort(key=lambda x: (x["etf_count"], x["total_weight"]), reverse=True)
    return rows


# ── 模組 B：隱藏強勢股 ───────────────────────────────────────────────
def hidden_winners(holdings, min_etf_count: int = MIN_ETF_COUNT_HIDDEN):
    """挖「被多檔 ETF 廣泛持有、但單檔內權重都不高」的潛在標的。

    Hidden Score = etf_count × (1 / avg_weight)
      etf_count 越高越好（廣泛持有）；avg_weight 越低越好（尚未被重壓 = 隱藏）。
    依 hidden_score 降序輸出。只計被 ≥ min_etf_count 檔持有者。
    """
    agg = _aggregate(holdings)
    rows = []
    for r in agg.values():
        if r["etf_count"] < min_etf_count or r["avg_weight"] <= 0:
            continue
        rows.append({
            "stock_id": r["stock_id"],
            "name": r["name"],
            "etf_count": r["etf_count"],
            "avg_weight": r["avg_weight"],
            "total_weight": r["total_weight"],
            "etf_list": r["etf_list"],
            "hidden_score": round(r["etf_count"] * (1.0 / r["avg_weight"]), 4),
        })
    rows.sort(key=lambda x: x["hidden_score"], reverse=True)
    return rows


# ── 模組 C：ETF × 成分股 權重熱力圖矩陣 ─────────────────────────────
def weight_matrix(holdings, etf_ids=None, stock_ids=None, limit_stocks: int = DEFAULT_HEATMAP_STOCKS):
    """產生 ETF × 個股 的交叉權重矩陣（供熱力圖）。

    回傳 {etfs, stocks, matrix}：
        etfs   —— 橫軸 ETF 代號序（未指定則取 holdings 中全部，排序）。
        stocks —— 縱軸個股序（未指定則取重疊 ETF 數最多的前 limit_stocks 檔）。
        matrix —— rows=stocks、cols=etfs 的權重（%）；未持有填 0。
    """
    agg = _aggregate(holdings)

    if etf_ids is None:
        etf_ids = sorted({h["etf_id"] for h in holdings})

    if stock_ids is None:
        ranked = sorted(
            agg.values(),
            key=lambda r: (r["etf_count"], r["total_weight"]),
            reverse=True,
        )
        stock_ids = [r["stock_id"] for r in ranked[:limit_stocks]]

    stock_rows = []
    matrix = []
    for sid in stock_ids:
        rec = agg.get(sid)
        wmap = rec["weights_by_etf"] if rec else {}
        matrix.append([round(wmap.get(eid, 0.0), 4) for eid in etf_ids])
        stock_rows.append({"stock_id": sid, "name": rec["name"] if rec else sid})

    return {"etfs": list(etf_ids), "stocks": stock_rows, "matrix": matrix}


# ── 模組 D：AI 三因子選股 ────────────────────────────────────────────
def ai_stock_selection(holdings, momentum=None, top_n: int = DEFAULT_AI_TOP_N,
                       weights=None, min_etf_count: int = 1):
    """三因子量化模型選出 Top N 智慧推薦個股。

    因子1 共識度 = etf_count；因子2 隱藏強度 = hidden_score；因子3 動能 = 近3月漲跌%。
    三因子各自 min-max 標準化到 [0,1] 後加權相加得 AI Score，降序取前 top_n。

    momentum：{stock_id: 近3月漲跌幅%}，由呼叫端從 Daily_Prices 算好餵入；
              缺資料的個股其動能視為 0（標準化後為最低），不因此被漏掉。
    weights：可覆蓋三因子權重（預設各 1/3）。
    """
    momentum = momentum or {}
    weights = {**AI_WEIGHTS, **(weights or {})}
    agg = _aggregate(holdings)

    universe = [r for r in agg.values() if r["etf_count"] >= min_etf_count]
    if not universe:
        return []

    consensus_raw = [r["etf_count"] for r in universe]
    hidden_raw = [
        r["etf_count"] * (1.0 / r["avg_weight"]) if r["avg_weight"] > 0 else 0.0
        for r in universe
    ]
    momentum_raw = [float(momentum.get(r["stock_id"], 0.0)) for r in universe]

    consensus_n = _minmax_normalize(consensus_raw)
    hidden_n = _minmax_normalize(hidden_raw)
    momentum_n = _minmax_normalize(momentum_raw)

    rows = []
    for i, r in enumerate(universe):
        ai = (weights["consensus"] * consensus_n[i]
              + weights["hidden"] * hidden_n[i]
              + weights["momentum"] * momentum_n[i])
        rows.append({
            "stock_id": r["stock_id"],
            "name": r["name"],
            "etf_count": r["etf_count"],
            "hidden_score": round(hidden_raw[i], 4),
            "momentum": round(momentum_raw[i], 4),
            "ai_score": round(ai, 6),
            "etf_list": r["etf_list"],
        })

    rows.sort(key=lambda x: x["ai_score"], reverse=True)
    rows = rows[:top_n]
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows
