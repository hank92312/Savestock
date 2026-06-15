"""dividend_calc 純計算模組單元測試。

測試重點在「為什麼這樣算」——即估算的商業規則，而非只是數字湊對：
全年估算用滾動值（季配股才不會低估）、今年已除息僅作實際資訊、查無資料不可默默漏算。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.dividend_calc import (  # noqa: E402
    StockDividendData,
    estimate_portfolio,
    BASIS_1Y,
    BASIS_5Y,
)


def _data(sid, name, d1y, d5y, paid):
    return StockDividendData(sid, name, d1y, d5y, paid)


def test_full_year_estimate_uses_rolling_not_partial_paid():
    """季配股全年估算必須用近1年(滾動12月)，不可用今年已除息的部分金額。

    這是本功能最關鍵的正確性規則：2330 今年只除息1次(6元)，但近1年是20.5元，
    若誤用 6 元當全年會低估七成。
    """
    stock_data = {"2330.TW": _data("2330.TW", "台積電", 20.5, 18.0, 6.0)}
    holdings = [{"stock_id": "2330.TW", "quantity": 50, "basis": BASIS_1Y}]

    r = estimate_portfolio(holdings, stock_data)
    item = r["items"][0]

    assert item["per_share"] == 20.5            # 用滾動近1年，非今年已除息6元
    assert item["amount"] == 1025.0             # 20.5 × 50
    assert item["paid_this_year"] == 300.0      # 6 × 50，僅作實際資訊併列


def test_basis_switches_between_1y_and_5y():
    """使用者可選近1年或近5年平均作為估算基準。"""
    stock_data = {"0056.TW": _data("0056.TW", "元大高股息", 3.6, 2.0, 1.8)}

    r1y = estimate_portfolio(
        [{"stock_id": "0056.TW", "quantity": 1000, "basis": BASIS_1Y}], stock_data
    )
    r5y = estimate_portfolio(
        [{"stock_id": "0056.TW", "quantity": 1000, "basis": BASIS_5Y}], stock_data
    )

    assert r1y["items"][0]["per_share"] == 3.6
    assert r5y["items"][0]["per_share"] == 2.0


def test_invalid_basis_falls_back_to_1y():
    stock_data = {"0056.TW": _data("0056.TW", "元大高股息", 3.6, 2.0, None)}
    r = estimate_portfolio(
        [{"stock_id": "0056.TW", "quantity": 1000, "basis": "garbage"}], stock_data
    )
    assert r["items"][0]["basis"] == BASIS_1Y
    assert r["items"][0]["per_share"] == 3.6


def test_odd_lot_quantity():
    """零股（非整張，如 50 股）必須能正確計算。"""
    stock_data = {"2330.TW": _data("2330.TW", "台積電", 14.0, 11.0, None)}
    r = estimate_portfolio(
        [{"stock_id": "2330.TW", "quantity": 50, "basis": BASIS_1Y}], stock_data
    )
    assert r["total"] == 700.0  # 14 × 50


def test_total_is_sum_of_holdings():
    stock_data = {
        "2330.TW": _data("2330.TW", "台積電", 14.0, 11.0, None),
        "0056.TW": _data("0056.TW", "元大高股息", 3.6, 2.0, None),
    }
    holdings = [
        {"stock_id": "2330.TW", "quantity": 100, "basis": BASIS_1Y},   # 1400
        {"stock_id": "0056.TW", "quantity": 2000, "basis": BASIS_1Y},  # 7200
    ]
    r = estimate_portfolio(holdings, stock_data)
    assert r["total"] == 8600.0


def test_high_impact_ranks_largest_contributors():
    """影響較大＝占總額比重最高者（其配息變動最影響你的總額）。"""
    stock_data = {
        "0056.TW": _data("0056.TW", "元大高股息", 3.6, 2.0, None),
        "2412.TW": _data("2412.TW", "中華電", 4.7, 4.5, None),
    }
    holdings = [
        {"stock_id": "0056.TW", "quantity": 5000, "basis": BASIS_1Y},  # 18000
        {"stock_id": "2412.TW", "quantity": 10, "basis": BASIS_1Y},    # 47
    ]
    r = estimate_portfolio(holdings, stock_data)
    assert r["high_impact"][0]["stock_id"] == "0056.TW"


def test_missing_stock_not_silently_dropped():
    """查無資料的股票必須標記出來（fail loud），不可默默漏算。"""
    r = estimate_portfolio(
        [{"stock_id": "9999.TW", "quantity": 1000, "basis": BASIS_1Y}], {}
    )
    item = r["items"][0]
    assert item["available"] is False
    assert item["amount"] == 0.0
    assert r["total"] == 0.0


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
