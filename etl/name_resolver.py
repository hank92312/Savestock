"""台股中文名稱解析（ETL 用）。

規則（依需求）：台股（.TW / .TWO）一律解析成中文名；美股（.US）等海外成分股維持英文。
作法對應 backend/routers/stocks.py 的 `_resolve_chinese_name`：
  先用 TWSE `STOCK_DAY_ALL` 批次快取（含上市＋ETF，一次請求解析全部台股），
  快取查無者（多為上櫃）再退回 mis `getStockInfo` 即時 API（tse→otc）。
"""
import requests as req_lib

_UA = {"User-Agent": "Mozilla/5.0"}
_twse_cache: dict[str, str] = {}   # code(無後綴) → 中文名
_loaded = False


def _has_chinese(s: str) -> bool:
    return any("一" <= c <= "鿿" for c in (s or ""))


def _load_twse_cache() -> None:
    """批次載入上市（含 ETF）中文名；非交易日退回公司主檔 t187ap03_L。"""
    global _loaded
    if _loaded:
        return
    try:
        r = req_lib.get(
            "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
            timeout=10, headers=_UA,
        )
        data = r.json()
        if len(data) > 100:
            for item in data:
                code = (item.get("Code") or "").strip()
                name = (item.get("Name") or "").strip()
                if code and name:
                    _twse_cache[code] = name
    except Exception:
        pass

    if not _twse_cache:
        try:
            r = req_lib.get(
                "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
                timeout=10, headers=_UA,
            )
            for item in r.json():
                code = (item.get("公司代號") or "").strip()
                name = (item.get("公司簡稱") or item.get("公司名稱") or "").strip()
                if code and name:
                    _twse_cache[code] = name
        except Exception:
            pass
    _loaded = True


def _mis_chinese_name(code_no_suffix: str) -> str | None:
    """mis 即時 API 抓中文名（tse→otc），供上櫃等快取查無者。"""
    for market in ("tse", "otc"):
        try:
            r = req_lib.get(
                "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
                params={"ex_ch": f"{market}_{code_no_suffix}.tw", "json": "1"},
                timeout=5, headers=_UA,
            )
            arr = r.json().get("msgArray")
            if arr and arr[0].get("n"):
                return arr[0]["n"]
        except Exception:
            continue
    return None


def resolve_name(stock_id: str, english_fallback: str = "") -> str:
    """台股回中文名（查無則沿用 fallback）；非台股（.US/.KS…）一律回 english_fallback。"""
    sid = (stock_id or "").strip().upper()
    fallback = english_fallback or stock_id
    if not (sid.endswith(".TW") or sid.endswith(".TWO")):
        return fallback  # 海外股維持英文

    code = sid.rsplit(".", 1)[0]
    _load_twse_cache()
    name = _twse_cache.get(code)
    if name and _has_chinese(name):
        return name
    realtime = _mis_chinese_name(code)
    return realtime if realtime and _has_chinese(realtime) else fallback
