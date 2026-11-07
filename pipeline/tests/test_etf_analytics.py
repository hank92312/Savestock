"""etf_analytics 純計算模組單元測試。

測試重點在「為什麼這樣算」的商業規則：
共識股要跨多檔 ETF、隱藏強勢股是「廣泛持有但權重低」、熱力圖未持有填 0、
AI 三因子標準化後加權排序、缺動能資料不可漏掉個股、空輸入不可炸。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.etf_analytics import (  # noqa: E402
    overlap_consensus,
    hidden_winners,
    weight_matrix,
    ai_stock_selection,
)


def _h(etf_id, stock_id, name, weight):
    return {"etf_id": etf_id, "stock_id": stock_id, "name": name, "weight": weight}


# 一組共用測試資料：
#   2330 被 3 檔 ETF 持有（高權重、高共識）
#   3443 被 3 檔 ETF 持有（低權重 → 隱藏強勢候選）
#   9999 只被 1 檔 ETF 持有（非共識）
SAMPLE = [
    _h("0052", "2330.TW", "台積電", 40.0),
    _h("0052", "3443.TW", "創意", 2.0),
    _h("00881", "2330.TW", "台積電", 30.0),
    _h("00881", "3443.TW", "創意", 3.0),
    _h("00881", "9999.TW", "冷門股", 5.0),
    _h("00952", "2330.TW", "台積電", 20.0),
    _h("00952", "3443.TW", "創意", 1.0),
]


def test_consensus_counts_distinct_etfs_and_sums_weight():
    """共識股：重疊 ETF 數 = 不重複 ETF 檔數，總權重 = 各 ETF 權重加總。"""
    rows = overlap_consensus(SAMPLE)
    top = rows[0]
    assert top["stock_id"] == "2330.TW"          # 3 檔 + 最高總權重 → 排第一
    assert top["etf_count"] == 3
    assert top["total_weight"] == 90.0           # 40+30+20
    assert top["etf_list"] == ["0052", "00881", "00952"]   # 代號字典序排列


def test_consensus_excludes_single_etf_stock():
    """只被 1 檔 ETF 持有的個股不算共識股（預設門檻 ≥2）。"""
    ids = [r["stock_id"] for r in overlap_consensus(SAMPLE)]
    assert "9999.TW" not in ids
    assert set(ids) == {"2330.TW", "3443.TW"}


def test_hidden_winner_prefers_low_avg_weight():
    """同為 3 檔持有時，平均權重越低者隱藏強度越高（3443 應勝過 2330）。"""
    rows = hidden_winners(SAMPLE)
    assert rows[0]["stock_id"] == "3443.TW"      # avg 2% → score 高
    # 2330 avg=30 → score=3/30=0.1；3443 avg=2 → score=3/2=1.5
    scores = {r["stock_id"]: r["hidden_score"] for r in rows}
    assert scores["3443.TW"] > scores["2330.TW"]
    assert scores["2330.TW"] == 0.1


def test_hidden_requires_multiple_etfs():
    """隱藏強勢股須被多檔持有；單檔持有的 9999 不入列。"""
    ids = [r["stock_id"] for r in hidden_winners(SAMPLE)]
    assert "9999.TW" not in ids


def test_weight_matrix_cell_matches_weight_and_zero_fill():
    """熱力圖：有持股填權重、未持股填 0，維度 = 個股數 × ETF 數。"""
    m = weight_matrix(SAMPLE, etf_ids=["0052", "00881", "00952"],
                      stock_ids=["2330.TW", "9999.TW"])
    assert m["etfs"] == ["0052", "00881", "00952"]
    assert len(m["matrix"]) == 2 and len(m["matrix"][0]) == 3
    # 2330 在三檔皆有
    assert m["matrix"][0] == [40.0, 30.0, 20.0]
    # 9999 只在 00881 → 0052/00952 填 0
    assert m["matrix"][1] == [0.0, 5.0, 0.0]


def test_weight_matrix_auto_selects_top_stocks():
    """未指定個股時，自動取重疊 ETF 數最多者當縱軸。"""
    m = weight_matrix(SAMPLE, limit_stocks=2)
    picked = [s["stock_id"] for s in m["stocks"]]
    assert set(picked) == {"2330.TW", "3443.TW"}   # 皆 3 檔，勝過 1 檔的 9999


def test_ai_score_combines_and_ranks():
    """AI Score 三因子標準化加權；動能高者在其他因子相同時分數更高。"""
    momentum = {"2330.TW": 5.0, "3443.TW": 30.0, "9999.TW": 0.0}
    rows = ai_stock_selection(SAMPLE, momentum=momentum, min_etf_count=1)
    ids = [r["stock_id"] for r in rows]
    assert set(ids) == {"2330.TW", "3443.TW", "9999.TW"}
    # 3443：隱藏強度最高 + 動能最高 → 應為第一名
    assert rows[0]["stock_id"] == "3443.TW"
    assert rows[0]["rank"] == 1
    # ai_score 應為降序
    assert all(rows[i]["ai_score"] >= rows[i + 1]["ai_score"] for i in range(len(rows) - 1))


def test_ai_missing_momentum_not_dropped():
    """缺動能資料的個股動能視為 0，仍須出現在結果中（不可默默漏掉）。"""
    rows = ai_stock_selection(SAMPLE, momentum={}, min_etf_count=1)
    ids = [r["stock_id"] for r in rows]
    assert "9999.TW" in ids
    assert all(r["momentum"] == 0.0 for r in rows)


def test_empty_holdings_no_crash():
    """空輸入不可炸（無資料時回空結果）。"""
    assert overlap_consensus([]) == []
    assert hidden_winners([]) == []
    assert ai_stock_selection([]) == []
    m = weight_matrix([])
    assert m["etfs"] == [] and m["matrix"] == []


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
