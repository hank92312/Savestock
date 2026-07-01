"""ETF 成分股 ETL：抓 16 檔 ETF 的 Top N 成分股權重寫入 DB，並補齊成分股個股收盤價。

流程（每次執行 = 當日一次快照）：
1. 逐檔 ETF 用 `etf_source.fetch_etf_holdings()` 抓成分股權重。
2. 寫 `ETF_Holdings`（先刪後插 = 當前快照）＋ append `ETF_Holding_History`（每日累積，供近10天權重趨勢）。
3. 蒐集所有成分股（跨 ETF 去重），並行補抓收盤價：
   * 新成分股（含美股 MU.US、韓股 005930.KS 等）以 stub 列寫入 `Stock_Master`（不覆蓋既有預設股的股利資料）。
   * 收盤價寫 `Daily_Prices`（抓約 4 個月，涵蓋 AI 選股模組要的近 3 月動能）。

可獨立執行（`python etl/fetch_etf.py`），亦可 `import` 後呼叫 `run()`（供未來 API/排程觸發）。
成分股收盤價沿用既有的並行抓取策略（ThreadPoolExecutor，max 5），與 watchlist/refresh 一致。
"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import yfinance as yf
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

from etf_source import ETF_UNIVERSE, fetch_etf_holdings, to_yahoo_symbol, SourceError
from name_resolver import resolve_name

# 資料庫連線（與 etl/fetch_data.py 同一套機制）
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)
DEFAULT_DB = "sqlite:///c:/Savestock/savestock.db"
DB_URL = os.getenv("DATABASE_URL", DEFAULT_DB).strip()  # .strip() 防 Secret Manager 值尾端換行
engine = create_engine(DB_URL)

PRICE_PERIOD = "4mo"       # 涵蓋近 3 月動能 + 緩衝
MAX_WORKERS = 5            # 並行抓價（與 watchlist/refresh 一致）


# ── 1. ETF 成分股寫入 ────────────────────────────────────────────────
def save_holdings(etf_id: str, holdings: list[dict]) -> None:
    """先刪後插當前快照，並 append 當日歷史權重。"""
    today = date.today().isoformat()
    with engine.begin() as conn:
        conn.execute(text("UPDATE ETF_Master SET Last_Updated = CURRENT_TIMESTAMP WHERE ETF_ID = :eid"),
                     {"eid": etf_id})
        # 當前快照：先刪後插（成分股可能換人，避免殘留舊 Top N）
        conn.execute(text("DELETE FROM ETF_Holdings WHERE ETF_ID = :eid"), {"eid": etf_id})
        for h in holdings:
            conn.execute(text("""
                INSERT INTO ETF_Holdings (ETF_ID, Stock_ID, Stock_Name, Weight, Snapshot_Date)
                VALUES (:eid, :sid, :name, :w, :d)
            """), {"eid": etf_id, "sid": h["stock_id"], "name": h["name"],
                   "w": h["weight"], "d": h["snapshot_date"]})
            # 歷史累積：同日重跑則覆蓋
            conn.execute(text("""
                INSERT INTO ETF_Holding_History (ETF_ID, Stock_ID, Date, Weight)
                VALUES (:eid, :sid, :d, :w)
                ON CONFLICT (ETF_ID, Stock_ID, Date) DO UPDATE SET Weight = EXCLUDED.Weight
            """), {"eid": etf_id, "sid": h["stock_id"], "d": today, "w": h["weight"]})


# ── 2. 成分股個股：入主檔（stub）＋ 抓收盤價 ──────────────────────────
def fetch_constituent_price(stock_id: str, name: str):
    """抓單一成分股近 4 個月收盤價；回傳 (stock_id, name, price_rows) 或 None。"""
    ysym = to_yahoo_symbol(stock_id)
    try:
        hist = yf.Ticker(ysym).history(period=PRICE_PERIOD)
        hist = hist.dropna(subset=["Close"])
        if hist.empty:
            print(f"  ⚠️ {stock_id} 無收盤價資料")
            return None
        rows = [{"date": ts.date(), "close": float(r["Close"]),
                 "volume": int(r["Volume"]) if r.get("Volume") == r.get("Volume") else 0}
                for ts, r in hist.iterrows()]
        return (stock_id, name, rows)
    except Exception as e:
        print(f"  ⚠️ {stock_id} 抓價失敗: {e!r}")
        return None


def save_constituent(stock_id: str, name: str, price_rows: list[dict]) -> None:
    """成分股入 Stock_Master（stub，不覆蓋既有列）＋ 收盤價入 Daily_Prices。"""
    with engine.begin() as conn:
        # 既有預設股（如 00929、2330）保留原本股利/產業資料，故 DO NOTHING
        conn.execute(text("""
            INSERT INTO Stock_Master (Stock_ID, Name, Sector)
            VALUES (:sid, :name, 'ETF成分')
            ON CONFLICT (Stock_ID) DO NOTHING
        """), {"sid": stock_id, "name": name})
        latest = price_rows[-1]["date"]
        for pr in price_rows:
            if pr["date"] == latest:
                # 只更新價量，保留 fetch_data 可能寫入的警示欄位
                conn.execute(text("""
                    INSERT INTO Daily_Prices (Stock_ID, Date, Close_Price, Volume)
                    VALUES (:sid, :d, :c, :v)
                    ON CONFLICT (Stock_ID, Date) DO UPDATE SET
                        Close_Price = EXCLUDED.Close_Price, Volume = EXCLUDED.Volume
                """), {"sid": stock_id, "d": pr["date"], "c": pr["close"], "v": pr["volume"]})
            else:
                conn.execute(text("""
                    INSERT INTO Daily_Prices (Stock_ID, Date, Close_Price, Volume)
                    VALUES (:sid, :d, :c, :v)
                    ON CONFLICT (Stock_ID, Date) DO NOTHING
                """), {"sid": stock_id, "d": pr["date"], "c": pr["close"], "v": pr["volume"]})


# ── 3. 主流程 ────────────────────────────────────────────────────────
def _load_custom_etfs() -> list[dict]:
    """從 DB 讀出使用者自訂的 ETF（Is_Custom），一併納入每日刷新。"""
    with engine.begin() as conn:
        rows = conn.execute(text(
            "SELECT ETF_ID, Name, Category FROM ETF_Master WHERE Is_Custom"
        )).fetchall()
    return [{"id": r[0], "name": r[1], "category": r[2] or "Custom"} for r in rows]


def run(etfs: list[dict] | None = None) -> dict:
    """跑完整 ETF ETL，回傳摘要（供 CLI / 未來 API 觸發共用）。

    未指定 etfs 時 = 固定 16 檔 + 資料庫中的自訂 ETF（依代號去重）。
    """
    if etfs is None:
        seen = {e["id"] for e in ETF_UNIVERSE}
        etfs = list(ETF_UNIVERSE) + [e for e in _load_custom_etfs() if e["id"] not in seen]
    ok_etf, fail_etf = 0, 0
    constituents: dict[str, str] = {}  # stock_id -> name（跨 ETF 去重）

    for etf in etfs:
        try:
            holdings = fetch_etf_holdings(etf["id"])
            # 台股成分股名稱轉中文（美股等海外維持英文）
            for h in holdings:
                h["name"] = resolve_name(h["stock_id"], h["name"])
            save_holdings(etf["id"], holdings)
            for h in holdings:
                constituents.setdefault(h["stock_id"], h["name"])
            print(f"✅ {etf['id']:>9} {etf['name']:<14} {len(holdings)} 檔成分股已寫入")
            ok_etf += 1
        except SourceError as e:
            print(f"❌ {etf['id']:>9} {etf['name']:<14} {e}")
            fail_etf += 1

    print(f"\n並行補抓 {len(constituents)} 檔成分股收盤價（max {MAX_WORKERS} threads）...")
    ok_px, fail_px = 0, 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_constituent_price, sid, name): sid
                   for sid, name in constituents.items()}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                sid, name, rows = res
                try:
                    save_constituent(sid, name, rows)
                    ok_px += 1
                except Exception as e:
                    print(f"  ⚠️ 寫入 {sid} 失敗: {e!r}")
                    fail_px += 1
            else:
                fail_px += 1

    summary = {"etf_ok": ok_etf, "etf_fail": fail_etf,
               "price_ok": ok_px, "price_fail": fail_px,
               "constituents": len(constituents)}
    print(f"\n=== 摘要：ETF {ok_etf}/{ok_etf + fail_etf} ・ "
          f"成分股價 {ok_px}/{len(constituents)} ===")
    return summary


if __name__ == "__main__":
    run()
