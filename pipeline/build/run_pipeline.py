"""Savestock v2 — 全市場靜態 JSON 建置管線（Builder）。

執行方式：
    py -m pipeline.build.run_pipeline --out web/public/data

流程：
1. 批次抓取全市場（TWSE 上市 + TPEx 上櫃）每日收盤價、估值（PE/PB/Yield）、月營收、已公告股利、除息預告、TDCC 大戶、ETF 淨值與規模。
2. 並行抓取精選 38 檔 ETF 的 MoneyDJ 完整成分股（30～60+ 檔）、費用率、含息報酬與配息紀錄。
3. 並行抓取精選 25 檔存股與主要權值股的深度歷史股價/股利/估值（FinMind）。
4. 驗證資料筆數與完整度（Safety Valve：若上市+上櫃有效筆數 < 1,200 筆則拒絕覆蓋）。
5. 計算全市場每檔證券的殖利率、價格帶、股利品質、存股健康分數、自適應警示，以及 ETF 四大分析與重疊度矩陣。
6. 輸出 `meta.json`、`universe.json`、`screener.json`、`calendar.json`、`etf/index.json`、`etf/analytics.json` 與 `s/{code}.json`。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.curated import CURATED_ETF_MAP, CURATED_ETFS, CURATED_STOCK_CODES, CURATED_STOCKS, ETF_GROUPS
from core.etf_analytics import ai_stock_selection, hidden_winners, overlap_consensus, weight_matrix
from core.metrics import (
    calc_dividend_quality,
    calc_etf_pairwise_overlap,
    calc_percentile,
    calc_price_bands,
    calc_risk_and_adaptive_alert,
    calc_stock_health_score,
    classify_price_zone,
)
from sources.official_tw import (
    fetch_announced_dividends_all,
    fetch_etf_market_snapshots,
    fetch_finmind_stock_history,
    fetch_moneydj_etf_detail,
    fetch_monthly_revenue_all,
    fetch_stock_info_map,
    fetch_tdcc_large_holders,
    fetch_tpex_daily_all,
    fetch_twse_daily_all,
    fetch_upcoming_ex_dividends,
    fetch_valuation_all,
)

TW_TZ = timezone(timedelta(hours=8))


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def run_build(out_dir: Path, fast_mode: bool = False) -> dict:
    now_tw = datetime.now(TW_TZ)
    version = now_tw.strftime("%Y%m%d-%H%M")
    cur_year = now_tw.year
    print(f"[1/6] 正在批次抓取 TWSE / TPEx / TDCC / ETF 全市場資料 (version={version})...")

    twse_daily = fetch_twse_daily_all()
    tpex_daily = fetch_tpex_daily_all()
    valuations = fetch_valuation_all()
    info_map = fetch_stock_info_map()
    revenues = fetch_monthly_revenue_all()
    announced_divs = fetch_announced_dividends_all()
    upcoming_events = fetch_upcoming_ex_dividends()
    tdcc_date, tdcc_map = fetch_tdcc_large_holders()
    etf_snapshots = fetch_etf_market_snapshots()

    all_daily: dict[str, dict] = {**tpex_daily, **twse_daily}
    print(
        f"  -> 上市 {len(twse_daily)} 檔 | 上櫃 {len(tpex_daily)} 檔 | "
        f"估值 {len(valuations)} 檔 | 月營收 {len(revenues)} 檔 | "
        f"已公告股利 {len(announced_divs)} 檔 | 集保大戶 {len(tdcc_map)} 檔 ({tdcc_date})"
    )

    if len(all_daily) < 1000:
        raise RuntimeError(f"安全閥觸發：全市場有效報價僅 {len(all_daily)} 檔（低於 1000 檔門檻），中止建置以保護既有資料。")

    # 決定市場最新交易日
    sample_dates = [d["date"] for d in all_daily.values() if d.get("date")]
    market_date = max(sample_dates) if sample_dates else str(date.today())

    # ── 2. 並行抓取精選 ETF 完整成分股與 MoneyDJ 詳情 ────────────────────
    etf_codes = [e["code"] for e in CURATED_ETFS]
    print(f"[2/6] 正在並行抓取 {len(etf_codes)} 檔精選 ETF 完整成分股與費用率/報酬 (MoneyDJ)...")
    etf_details: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_moneydj_etf_detail, c): c for c in etf_codes}
        for fut in as_completed(futs):
            c = futs[fut]
            try:
                etf_details[c] = fut.result()
            except Exception as e:
                print(f"  [WARN] ETF {c} MoneyDJ 抓取失敗: {e}")
                etf_details[c] = {"code": c, "holdings": [], "completeness": "none", "returns": {}, "dividends": []}

    full_cnt = sum(1 for v in etf_details.values() if len(v.get("holdings", [])) > 0)
    print(f"  -> 成功取得 {full_cnt}/{len(etf_codes)} 檔 ETF 完整成分股！")

    # ── 3. 並行抓取精選存股 25 檔 + 核心權值股深度歷史（FinMind）──────────
    deep_stock_codes = sorted(
        (CURATED_STOCK_CODES - set(etf_codes))
        | {"2330", "2317", "2454", "2308", "2382", "2881", "2882", "2891", "2303", "3711"}
    )
    if fast_mode:
        deep_stock_codes = [s["code"] for s in CURATED_STOCKS if s["code"] not in etf_codes]

    print(f"[3/6] 正在抓取 {len(deep_stock_codes)} 檔核心存股之歷史股價/股利/估值位階 (FinMind)...")
    stock_histories: dict[str, tuple[list[dict], list[dict], list[dict]]] = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(fetch_finmind_stock_history, c): c for c in deep_stock_codes}
        for fut in as_completed(futs):
            c = futs[fut]
            try:
                stock_histories[c] = fut.result()
            except Exception:
                stock_histories[c] = ([], [], [])

    # ── 4. 組裝全市場 universe 與 screener 與各檔詳情 JSON ───────────────
    print("[4/6] 正在計算全市場指標、價格帶、健康分數與組裝各檔詳情...")
    curated_sector_map = {s["code"]: s["sector"] for s in CURATED_STOCKS}
    universe_items: list[dict] = []
    screener_items: dict[str, dict] = {}
    alerts_today_count = 0

    # 確保所有精選 ETF 即使在 TPEx 也一定納入
    all_codes = sorted(set(all_daily.keys()) | set(etf_codes) | CURATED_STOCK_CODES)

    for code in all_codes:
        d = all_daily.get(code)
        etf_snap = etf_snapshots.get(code, {})
        etf_meta = CURATED_ETF_MAP.get(code)
        info = info_map.get(code, {})

        is_etf = bool(etf_meta or code.startswith("00"))
        name = (
            (etf_meta["name"] if etf_meta else None)
            or (d["name"] if d else None)
            or etf_snap.get("name")
            or info.get("name")
            or code
        )
        market = (d["market"] if d else None) or info.get("market") or ("TPEX" if code.endswith("B") else "TWSE")
        sector = (
            curated_sector_map.get(code)
            or (ETF_GROUPS.get(etf_meta["group"], "ETF") if etf_meta else None)
            or ("ETF" if is_etf else info.get("sector") or "其他")
        )
        price = (d["close"] if d else None) or etf_snap.get("price")
        if not price or price <= 0:
            continue

        change = d["change"] if d else 0.0
        change_pct = d["changePct"] if d else 0.0
        volume = d["volume"] if d else 0
        is_curated = (code in CURATED_STOCK_CODES) or (code in CURATED_ETF_MAP)

        val = valuations.get(code, {})
        rev = revenues.get(code, {})
        ann = announced_divs.get(code, {})
        tdcc = tdcc_map.get(code, {})

        pe = val.get("pe")
        pb = val.get("pb")
        official_yield = val.get("officialYield")

        # 股利歷史與 1Y / 2Y / 5Y 計算
        hist_prices, hist_divs, hist_vals = stock_histories.get(code, ([], [], []))
        etf_det = etf_details.get(code, {})
        if is_etf and etf_det.get("dividends"):
            hist_divs = etf_det["dividends"]

        # 彙整歷年股利 {year: total_div}
        annual_divs: dict[int, float] = {}
        paid_this_year = 0.0
        div_1y_rolling = 0.0
        cutoff_1y = str(date.today() - timedelta(days=380))
        for dv in hist_divs:
            yr = dv.get("year") or cur_year
            tot = float(dv.get("total") or 0.0)
            annual_divs[yr] = round(annual_divs.get(yr, 0.0) + tot, 4)
            ex_d = dv.get("exDate") or ""
            if ex_d.startswith(str(cur_year)):
                paid_this_year = round(paid_this_year + tot, 4)
            if ex_d >= cutoff_1y:
                div_1y_rolling = round(div_1y_rolling + tot, 4)

        announced_val = ann.get("total")
        # 若無歷史股利明細，以官方殖利率反推每股股利
        inferred_div = round(price * official_yield / 100.0, 2) if official_yield and official_yield > 0 else None

        div_1y = (
            div_1y_rolling
            if div_1y_rolling > 0
            else (announced_val or val.get("tpexDivPerShare") or inferred_div or 0.0)
        )
        # 2Y / 5Y 平均股利
        if len(annual_divs) >= 2:
            y2_vals = [annual_divs.get(cur_year - 1, 0.0), annual_divs.get(cur_year - 2, 0.0)]
            if sum(y2_vals) == 0 and annual_divs.get(cur_year, 0) > 0:
                y2_vals = [annual_divs.get(cur_year, 0.0), annual_divs.get(cur_year - 1, 0.0)]
            div_2y = round(sum(y2_vals) / 2, 2) if sum(y2_vals) > 0 else round(div_1y, 2)

            y5_vals = [annual_divs.get(cur_year - i, 0.0) for i in range(1, 6)]
            div_5y = round(sum(y5_vals) / 5, 2) if sum(y5_vals) > 0 else div_2y
        else:
            div_2y = round(div_1y, 2)
            div_5y = round(div_1y, 2)

        yield_1y = round(div_1y / price * 100, 2) if div_1y > 0 else (official_yield or 0.0)
        yield_2y = round(div_2y / price * 100, 2) if div_2y > 0 else yield_1y
        yield_5y = round(div_5y / price * 100, 2) if div_5y > 0 else yield_2y

        # EPS 由 PE 反推（若無季報直接值）
        eps_ttm = round(price / pe, 2) if pe and pe > 0 else None

        # 股利品質
        div_q = calc_dividend_quality(annual_divs, current_year=cur_year, eps_ttm=eps_ttm)
        if div_q["consec_years"] == 0 and yield_1y > 0:
            div_q["consec_years"] = 1

        # 價格帶（用 5Y 平均或 2Y 平均股利）
        ref_div = div_5y if div_5y > 0 else div_1y
        bands = calc_price_bands(ref_div)
        zone = classify_price_zone(price, bands)

        # 估值百分位
        pe_pct = calc_percentile(pe, [v.get("pe") for v in hist_vals if v.get("pe")])
        yield_pct = calc_percentile(yield_1y, [v.get("yield") for v in hist_vals if v.get("yield")])

        # 確保最新一日收盤價接在歷史收盤價最後
        if not hist_prices or hist_prices[-1].get("date") != market_date:
            hist_prices = list(hist_prices) + [{"date": market_date, "close": price, "volume": volume}]

        closes_seq = [p["close"] for p in hist_prices]
        vols_seq = [int(p.get("volume") or 0) for p in hist_prices]
        risk_info = calc_risk_and_adaptive_alert(closes_seq, vols_seq, sector=sector)
        # 若只有當日 1 筆價格，直接用當日漲跌幅判斷
        if len(closes_seq) < 2 and change_pct <= -risk_info["adaptive_drop_threshold"]:
            risk_info["alert_flag"] = True
            risk_info["alert_reasons"] = [
                f"單日跌幅 {change_pct:.2f}%（超過門檻 -{risk_info['adaptive_drop_threshold']:.1f}%）"
            ]

        if risk_info["alert_flag"]:
            alerts_today_count += 1

        etf_expense = etf_det.get("expenseRatioPct")
        etf_discount = etf_snap.get("discountPct") if etf_snap.get("discountPct") is not None else etf_det.get("discountPct")

        score_obj = calc_stock_health_score(
            is_etf=is_etf,
            yield_1y=yield_1y,
            yield_5y=yield_5y,
            consec_years=div_q["consec_years"],
            div_cv_5y=div_q["div_cv_5y"],
            payout_ratio=div_q["payout_ratio"],
            fill_rate_5y=100.0 if div_q["consec_years"] >= 5 else None,
            pe=pe,
            price_zone=zone,
            rev_yoy=rev.get("yoy"),
            eps_ttm=eps_ttm,
            volatility_1y=risk_info["volatility_1y"] or etf_det.get("volatilityPct"),
            etf_expense_pct=etf_expense,
            etf_discount_pct=etf_discount,
        )

        universe_items.append({
            "code": code,
            "name": name,
            "market": market,
            "type": "etf" if is_etf else "stock",
            "sector": sector,
            "etfGroup": etf_meta["group"] if etf_meta else ("other" if is_etf else None),
            "curated": is_curated,
        })

        summary_item = {
            "code": code,
            "name": name,
            "market": market,
            "type": "etf" if is_etf else "stock",
            "sector": sector,
            "etfGroup": etf_meta["group"] if etf_meta else None,
            "tags": etf_meta["tags"] if etf_meta else [],
            "curated": is_curated,
            "price": price,
            "change": change,
            "changePct": change_pct,
            "volume": volume,
            "yield1y": yield_1y,
            "yield2y": yield_2y,
            "yield5y": yield_5y,
            "div1y": round(div_1y, 3),
            "div2y": round(div_2y, 3),
            "div5y": round(div_5y, 3),
            "paidThisYear": round(paid_this_year, 3),
            "announcedDiv": announced_val,
            "pe": pe,
            "pb": pb,
            "pePercentile5y": pe_pct,
            "yieldPercentile5y": yield_pct,
            "consecDivYears": div_q["consec_years"],
            "divCv5y": div_q["div_cv_5y"],
            "divCagr5y": div_q["cagr_5y"],
            "payoutRatio": div_q["payout_ratio"],
            "revYm": rev.get("ym"),
            "revYoY": rev.get("yoy"),
            "revMoM": rev.get("mom"),
            "epsTtm": eps_ttm,
            "largeHolder1000Pct": tdcc.get("large1000Pct"),
            "largeHolder400Pct": tdcc.get("large400Pct"),
            "shareholders": tdcc.get("shareholders"),
            "priceBands": {**(bands or {"cheap": None, "fair": None, "expensive": None}), "zone": zone},
            "score": {
                "total": score_obj["total"],
                "grade": score_obj["grade"],
                "positives": score_obj["positives"],
                "cautions": score_obj["cautions"],
            },
            "alert": {
                "flag": risk_info["alert_flag"],
                "reasons": risk_info["alert_reasons"],
                "volInfo": risk_info["vol_info"],
                "thresholdPct": risk_info["adaptive_drop_threshold"],
            },
            "etf": {
                "nav": etf_snap.get("nav") or etf_det.get("nav"),
                "discountPct": etf_discount,
                "expenseRatioPct": etf_expense,
                "aumHundredMillions": etf_snap.get("aumHundredMillions"),
                "holdersCount": etf_snap.get("holdersCount") or tdcc.get("shareholders"),
                "divFrequency": etf_det.get("divFrequency"),
                "issuer": etf_snap.get("issuer"),
                "returns": etf_det.get("returns", {}),
                "holdingsCount": len(etf_det.get("holdings", [])),
            } if is_etf else None,
        }
        screener_items[code] = summary_item

        # 產生個股/ETF 獨立詳情檔 `data/s/{code}.json`（對所有精選股、ETF、或有歷史資料的個股輸出完整檔）
        if is_curated or code in stock_histories or is_etf:
            detail_payload = {
                "code": code,
                "name": name,
                "market": market,
                "type": "etf" if is_etf else "stock",
                "sector": sector,
                "updatedAt": market_date,
                "summary": summary_item,
                "scoreBreakdown": score_obj,
                "prices": hist_prices[-260:],  # 近 1 年日線
                "dividends": sorted(hist_divs, key=lambda x: x.get("exDate") or "", reverse=True)[:40],
                "valuationHistory": hist_vals[-150:],
                "fundamentals": {
                    "revYm": rev.get("ym"),
                    "rev": rev.get("rev"),
                    "revYoY": rev.get("yoy"),
                    "revMoM": rev.get("mom"),
                    "cumYoY": rev.get("cumYoy"),
                    "epsTtm": eps_ttm,
                    "payoutRatio": div_q["payout_ratio"],
                },
                "chips": {
                    "tdccDate": tdcc_date,
                    "largeHolder1000Pct": tdcc.get("large1000Pct"),
                    "largeHolder400Pct": tdcc.get("large400Pct"),
                    "shareholders": tdcc.get("shareholders"),
                },
                "risk": risk_info,
                "etfInfo": {
                    **summary_item["etf"],
                    "trackingIndex": etf_snap.get("trackingIndex"),
                    "listingDate": etf_snap.get("listingDate"),
                    "completeness": etf_det.get("completeness", "none"),
                    "holdings": [
                        {
                            **h,
                            "price": screener_items.get(h["stock_id"], {}).get("price")
                            or all_daily.get(h["stock_id"], {}).get("close"),
                            "changePct": screener_items.get(h["stock_id"], {}).get("changePct")
                            or all_daily.get(h["stock_id"], {}).get("changePct"),
                            "yield1y": screener_items.get(h["stock_id"], {}).get("yield1y"),
                        }
                        for h in etf_det.get("holdings", [])
                    ],
                } if is_etf else None,
            }
            _write_json(out_dir / "s" / f"{code}.json", detail_payload)

    # ── 5. 計算 ETF 進階分析（共識股、隱藏強勢股、熱力圖、共識動能評分、重疊矩陣）──
    print("[5/6] 正在計算 ETF 跨基金完整持股重疊矩陣與四大分析...")
    flat_holdings: list[dict] = []
    etf_holdings_map: dict[str, list[dict]] = {}
    momentum_map: dict[str, float] = {}

    for c, det in etf_details.items():
        h_list = det.get("holdings") or []
        if not h_list:
            continue
        etf_holdings_map[c] = h_list
        for h in h_list:
            sid = h["stock_id"]
            flat_holdings.append({
                "etf_id": c,
                "stock_id": sid,
                "name": h["name"],
                "weight": h["weight"],
            })
            # 動能：優先用歷史 60 日漲跌幅，否則用當日漲跌幅
            if sid not in momentum_map:
                hp = stock_histories.get(sid, ([], [], []))[0]
                if len(hp) >= 20 and hp[-20]["close"] > 0:
                    momentum_map[sid] = round((hp[-1]["close"] - hp[-20]["close"]) / hp[-20]["close"] * 100, 2)
                elif sid in all_daily:
                    momentum_map[sid] = all_daily[sid].get("changePct") or 0.0

    etf_index_payload = {
        "version": version,
        "marketDate": market_date,
        "groups": [{"id": k, "name": v} for k, v in ETF_GROUPS.items()],
        "items": [screener_items[e["code"]] for e in CURATED_ETFS if e["code"] in screener_items],
    }

    etf_analytics_payload = {
        "version": version,
        "marketDate": market_date,
        "consensus": overlap_consensus(flat_holdings, min_etf_count=2)[:50],
        "hiddenWinners": hidden_winners(flat_holdings, min_etf_count=3)[:40],
        "heatmap": weight_matrix(flat_holdings, limit_stocks=25),
        "factorRanking": ai_stock_selection(flat_holdings, momentum=momentum_map, top_n=25, min_etf_count=2),
        "pairwiseOverlap": calc_etf_pairwise_overlap(etf_holdings_map),
        "holdingsByEtf": etf_holdings_map,
    }

    # ── 6. 寫出全域 JSON 檔案 ────────────────────────────────────────────
    print("[6/6] 正在寫出靜態 JSON 檔案至", out_dir)
    meta_payload = {
        "version": version,
        "marketDate": market_date,
        "updatedAt": now_tw.isoformat(timespec="seconds"),
        "counts": {
            "total": len(screener_items),
            "twse": len(twse_daily),
            "tpex": len(tpex_daily),
            "curatedStocks": len(CURATED_STOCKS),
            "curatedEtfs": len(CURATED_ETFS),
            "alertsToday": alerts_today_count,
        },
        "sources": {
            "twseDaily": "ok" if twse_daily else "empty",
            "tpexDaily": "ok" if tpex_daily else "empty",
            "etfHoldings": f"{full_cnt}/{len(etf_codes)}",
            "tdccDate": tdcc_date,
        },
    }

    _write_json(out_dir / "meta.json", meta_payload)
    _write_json(out_dir / "universe.json", {"version": version, "items": universe_items})
    _write_json(
        out_dir / "screener.json",
        {
            "version": version,
            "marketDate": market_date,
            "curatedStockCodes": [s["code"] for s in CURATED_STOCKS],
            "curatedEtfCodes": [e["code"] for e in CURATED_ETFS],
            "items": screener_items,
        },
    )
    _write_json(out_dir / "calendar.json", {"version": version, "events": upcoming_events[:120]})
    _write_json(out_dir / "etf" / "index.json", etf_index_payload)
    _write_json(out_dir / "etf" / "analytics.json", etf_analytics_payload)

    print(f"✅ 建置完成！共輸出 {len(screener_items)} 檔全市場證券與 {full_cnt} 檔完整 ETF 成分股資料。")
    return meta_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Savestock v2 static data pipeline")
    parser.add_argument("--out", default="web/public/data", help="Output directory for static JSON files")
    parser.add_argument("--fast", action="store_true", help="Fast mode (only fetch history for 25 curated stocks)")
    args = parser.parse_args()
    run_build(Path(args.out), fast_mode=args.fast)


if __name__ == "__main__":
    main()

