"""ETF 成分股資料來源層（可切換來源）。

G0 交付：把「抓某檔 ETF 的成分股 + 權重」抽象成單一介面 `fetch_etf_holdings()`，
上層（ETL / API）不綁死來源。目前主來源為 yfinance（免費、免 Key、已在既有依賴），
未來遇到來源困難時，可把 cmoney / moneydj 爬蟲插進 `_SOURCES` 當備援，不需改上層。

回傳統一格式（list[dict]）：
    {"stock_id": "2330.TW", "name": "Taiwan ...", "weight": 41.72, "snapshot_date": date}

限制（見來源決策）：
* yfinance 只給 **Top 10** 成分股。
* 只有「當下快照」，**無歷史權重**——歷史折線由每日快照累積（ETF_Holding_History）。
"""
from __future__ import annotations

from datetime import date
from typing import Callable

import yfinance as yf


class SourceError(Exception):
    """單一來源抓取失敗（觸發 fallback 到下一個來源）。"""


# ── 追蹤的 16 檔 ETF（依 etf_tracker.md 規格書分兩大族群）──────────────
# category: "Tech" = 綜合型科技/資訊科技類；"AI" = AI/創新科技主題類
ETF_UNIVERSE = [
    # 第 1 族群：綜合型科技 / 資訊科技類
    {"id": "0052.TW",  "name": "富邦科技",              "category": "Tech"},
    {"id": "0053.TW",  "name": "元大電子",              "category": "Tech"},
    {"id": "00881.TW", "name": "國泰台灣科技龍頭",       "category": "Tech"},
    {"id": "00935.TW", "name": "野村臺灣創新科技50",     "category": "Tech"},
    {"id": "00943.TW", "name": "兆豐台灣電子成長高息等權重", "category": "Tech"},
    {"id": "00735.TW", "name": "國泰臺韓科技",           "category": "Tech"},
    {"id": "00905.TW", "name": "FT臺灣Smart",           "category": "Tech"},
    # 第 2 族群：AI / 創新科技主題類（含美股成分股）
    {"id": "00952.TW", "name": "凱基台灣AI50",          "category": "AI"},
    {"id": "00851.TW", "name": "台新全球AI",            "category": "AI"},
    {"id": "00762.TW", "name": "元大全球人工智慧",       "category": "AI"},
    {"id": "00947.TW", "name": "台新臺灣IC設計",         "category": "AI"},
    {"id": "00962.TW", "name": "台新AI優息動能",         "category": "AI"},
    {"id": "00946.TW", "name": "群益科技高息成長",       "category": "AI"},
    {"id": "00929.TW", "name": "復華台灣科技優息",       "category": "AI"},
    {"id": "00876.TW", "name": "元大全球5G關鍵科技",     "category": "AI"},
    {"id": "00861.TW", "name": "元大全球未來通訊",       "category": "AI"},
]


def normalize_symbol(raw: str) -> str:
    """把 yfinance 的成分股代號正規化為專案慣例。

    規則：已帶後綴者原樣保留（台股 `.TW`、上櫃 `.TWO`、海外如 `.AS`/`.T`）；
    無後綴者視為美股，補上 `.US`（規格書慣例，如 `MU` → `MU.US`）。
    """
    sym = (raw or "").strip().upper()
    if not sym:
        return sym
    return sym if "." in sym else f"{sym}.US"


def to_yahoo_symbol(stock_id: str) -> str:
    """把專案慣例代號轉回 yfinance 可查的 Yahoo 代號。

    `.US` 是本專案給美股補的假後綴，Yahoo 不吃 → 去掉（`MU.US` → `MU`）。
    其餘後綴（`.TW`/`.TWO`/`.KS`/`.AS`/`.T` …）Yahoo 原樣接受。
    """
    sid = (stock_id or "").strip()
    return sid[:-3] if sid.upper().endswith(".US") else sid


# ── 主來源：yfinance ─────────────────────────────────────────────────
def fetch_via_yfinance(etf_id: str) -> list[dict]:
    """用 yfinance `funds_data.top_holdings` 抓 Top 10 成分股權重。"""
    try:
        fd = yf.Ticker(etf_id).funds_data
        th = fd.top_holdings  # DataFrame: index=Symbol, cols=[Name, Holding Percent]
    except Exception as e:  # yfinance / 網路 / 該檔非基金
        raise SourceError(f"yfinance 取得 {etf_id} funds_data 失敗: {e!r}") from e

    if th is None or th.empty:
        raise SourceError(f"yfinance 無 {etf_id} 成分股資料")

    today = date.today()
    holdings: list[dict] = []
    for symbol, row in th.iterrows():
        pct = row.get("Holding Percent")
        if pct is None:
            continue
        holdings.append({
            "stock_id": normalize_symbol(str(symbol)),
            "name": (str(row.get("Name")).strip() if row.get("Name") is not None else ""),
            "weight": round(float(pct) * 100, 4),  # 小數 → 百分比
            "snapshot_date": today,
        })
    if not holdings:
        raise SourceError(f"yfinance {etf_id} 成分股權重欄位全空")
    return holdings


# ── 備援來源（尚未實作，待遇到 yfinance 困難時開發）──────────────────
def fetch_via_cmoney(etf_id: str) -> list[dict]:
    """備援：cmoney 成分股（需逆向其 XHR API）。目前為佔位。"""
    raise SourceError("cmoney 來源尚未實作（備援插槽）")


def fetch_via_moneydj(etf_id: str) -> list[dict]:
    """備援：moneydj 成分股。目前為佔位。"""
    raise SourceError("moneydj 來源尚未實作（備援插槽）")


# 來源優先序：主 yfinance，失敗依序 fallback
_SOURCES: list[tuple[str, Callable[[str], list[dict]]]] = [
    ("yfinance", fetch_via_yfinance),
    ("cmoney",   fetch_via_cmoney),
    ("moneydj",  fetch_via_moneydj),
]


def fetch_etf_holdings(etf_id: str, verbose: bool = False) -> list[dict]:
    """抓某檔 ETF 的成分股權重；依 `_SOURCES` 順序嘗試，前者失敗自動 fallback。

    全部來源皆失敗才 raise SourceError（fail loud，方便 ETL 記錄哪檔抓不到）。
    """
    errors = []
    for name, fn in _SOURCES:
        try:
            holdings = fn(etf_id)
            if verbose:
                print(f"  [{etf_id}] 來源 {name} 成功，{len(holdings)} 檔成分股")
            return holdings
        except SourceError as e:
            errors.append(f"{name}: {e}")
            if verbose:
                print(f"  [{etf_id}] 來源 {name} 失敗 → 嘗試下一個")
    raise SourceError(f"{etf_id} 所有來源皆失敗；{' | '.join(errors)}")


def _validate_all() -> None:
    """G0 驗證：跑過全部 16 檔，印出成分股與 pass/fail 摘要。"""
    ok, fail = 0, 0
    for etf in ETF_UNIVERSE:
        try:
            holdings = fetch_etf_holdings(etf["id"])
            top = ", ".join(f"{h['stock_id']}({h['weight']:.1f}%)" for h in holdings[:3])
            print(f"✅ {etf['id']:>9} {etf['name']:<16} {len(holdings):>2} 檔 | {top} ...")
            ok += 1
        except SourceError as e:
            print(f"❌ {etf['id']:>9} {etf['name']:<16} {e}")
            fail += 1
    print(f"\n=== 摘要：{ok} 成功 / {fail} 失敗（共 {len(ETF_UNIVERSE)} 檔）===")


if __name__ == "__main__":
    _validate_all()
