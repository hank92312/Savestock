"""metrics.py 單元測試：驗證股利品質、價格帶、自適應警示、健康分數、穿透持股與重疊度矩陣。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.metrics import (  # noqa: E402
    calc_nhi_surcharge,
    calc_price_bands,
    classify_price_zone,
    calc_dividend_quality,
    calc_risk_and_adaptive_alert,
    calc_stock_health_score,
    calc_etf_lookthrough,
    calc_etf_pairwise_overlap,
)


def test_nhi_surcharge_threshold():
    assert calc_nhi_surcharge(19999) == 0.0
    assert calc_nhi_surcharge(20000) == 422.0


def test_price_bands_and_zone():
    bands = calc_price_bands(6.0)
    assert bands == {"cheap": 100.0, "fair": 120.0, "expensive": 150.0}
    assert classify_price_zone(95.0, bands) == "cheap"
    assert classify_price_zone(110.0, bands) == "fair"
    assert classify_price_zone(135.0, bands) == "warm"
    assert classify_price_zone(160.0, bands) == "expensive"


def test_dividend_quality_consecutive_and_payout():
    divs = {2021: 4.0, 2022: 4.2, 2023: 4.5, 2024: 4.8, 2025: 5.0}
    q = calc_dividend_quality(divs, current_year=2026, eps_ttm=6.0)
    assert q["consec_years"] == 5
    assert q["cagr_5y"] > 0
    assert q["payout_ratio"] == 83.3


def test_adaptive_alert_only_flags_down_volume_spike():
    # 上漲爆量不應觸發警示，只有下跌爆量才觸發
    closes_up = [100.0] * 25 + [102.0]
    vols = [1000] * 25 + [3000]
    r_up = calc_risk_and_adaptive_alert(closes_up, vols, sector="Telecom")
    assert r_up["alert_flag"] is False
    assert r_up["vol_info"] is not None

    closes_down = [100.0] * 25 + [98.0]
    r_down = calc_risk_and_adaptive_alert(closes_down, vols, sector="Telecom")
    assert r_down["alert_flag"] is True
    assert any("下跌爆量" in s for s in r_down["alert_reasons"])


def test_health_score_penalizes_yield_trap():
    good = calc_stock_health_score(
        consec_years=20, div_cv_5y=0.08, payout_ratio=70, fill_rate_5y=100,
        price_zone="fair", rev_yoy=12.0, eps_ttm=5.0, volatility_1y=14.0,
    )
    trap = calc_stock_health_score(
        consec_years=2, div_cv_5y=0.65, payout_ratio=130, fill_rate_5y=40,
        yield_1y=11.0, yield_5y=4.0, price_zone="cheap", rev_yoy=-25.0, eps_ttm=-1.0, volatility_1y=42.0,
    )
    assert good["total"] >= 80 and good["grade"] == "A"
    assert trap["total"] < 50
    assert any("陷阱" in c or "超額配息" in c for c in trap["cautions"])


def test_etf_lookthrough_and_overlap():
    etf_map = {
        "0056": [{"stock_id": "2382.TW", "name": "廣達", "weight": 5.0}, {"stock_id": "2891.TW", "name": "中信金", "weight": 4.0}],
        "00878": [{"stock_id": "2382.TW", "name": "廣達", "weight": 8.0}, {"stock_id": "2891.TW", "name": "中信金", "weight": 10.0}],
    }
    look = calc_etf_lookthrough(
        [{"code": "0056", "market_value": 100000}, {"code": "00878", "market_value": 100000}],
        etf_map,
    )
    assert look[0]["code"] == "2891"
    assert look[0]["exposed_value"] == 14000
    ov = calc_etf_pairwise_overlap(etf_map)
    assert ov["matrix"][0][1] == 9.0  # min(5,8) + min(4,10) = 5 + 4 = 9.0%

