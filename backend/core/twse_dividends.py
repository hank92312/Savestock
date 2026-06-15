"""證交所 OpenAPI：上市公司「已公告」股利（年配股全年配息）。

資料源：https://openapi.twse.com.tw/v1/opendata/t187ap45_L（上市公司股利分派情形）
官方、穩定、一次回傳全市場，免爬 MOPS。用 requests（內建 certifi，跨環境 SSL 穩定）；
FastAPI 與 Django 報表共用（兩者皆已含 requests 依賴）。

【只取年配股】資料按「股利年度／期別」記錄：
* 年配股 → 有一列「股利所屬年(季)度 = 年度」、期間涵蓋整年，即全年已公告配息。
* 季配/半年配股 → 只有「第N季」列，年中無法得知全年（後續季別尚未開會決議），
  故不納入，交回估算（近1年滾動值本就能合理涵蓋季配）。

【今年可領 = 去年度盈餘】台股年配股於今年股東會通過「去年度(earnings)」盈餘分配，
今年發放。故今年(民國 Y)可領的年配股利 = 股利年度 (Y-1) 的「年度」列。
"""

from datetime import date, datetime, timedelta, timezone

import requests

_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap45_L"
_TTL = timedelta(hours=12)
_UA = {"User-Agent": "Mozilla/5.0"}

_CASH_FIELDS = (
    "股東配發-盈餘分配之現金股利(元/股)",
    "股東配發-法定盈餘公積發放之現金(元/股)",
    "股東配發-資本公積發放之現金(元/股)",
)
_STOCK_FIELDS = (
    "股東配發-盈餘轉增資配股(元/股)",
    "股東配發-法定盈餘公積轉增資配股(元/股)",
    "股東配發-資本公積轉增資配股(元/股)",
)

_cache = None
_cache_at = None


def _target_roc_year() -> int:
    """今年可領之年配股利對應的『股利年度』（民國，= 今年民國 - 1）。"""
    return (date.today().year - 1911) - 1


def _f(row, key) -> float:
    try:
        return float(row.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def fetch_announced_annual(force: bool = False) -> dict:
    """{純代號: {'amount': 全年每股配息(元), 'progress': 決議進度}}，只含年配且今年可領者。

    一次抓全市場、快取 12 小時。任何失敗回傳上次快取或空 dict（不中斷估算）。
    """
    global _cache, _cache_at
    now = datetime.now(timezone.utc)
    if not force and _cache is not None and _cache_at and now - _cache_at < _TTL:
        return _cache

    try:
        resp = requests.get(_URL, headers=_UA, timeout=30)
        resp.raise_for_status()
        rows = resp.json()
    except Exception:
        return _cache or {}

    target = str(_target_roc_year())
    result = {}
    for r in rows:
        if r.get("股利年度") != target:
            continue
        if r.get("股利所屬年(季)度") != "年度":  # 只取年配（全年）列
            continue
        code = r.get("公司代號")
        if not code:
            continue
        total = round(
            sum(_f(r, k) for k in _CASH_FIELDS) + sum(_f(r, k) for k in _STOCK_FIELDS),
            4,
        )
        if total <= 0:
            continue
        issued = r.get("出表日期", "")
        prev = result.get(code)
        if prev is None or issued >= prev["_issued"]:  # 多列取最新出表
            result[code] = {
                "amount": total,
                "progress": r.get("決議（擬議）進度", ""),
                "_issued": issued,
            }

    for v in result.values():
        v.pop("_issued", None)

    _cache, _cache_at = result, now
    return result


def announced_for(code_no_suffix: str):
    """單檔查詢（純代號，如 '2412'）；無資料回傳 None。"""
    return fetch_announced_annual().get(code_no_suffix)
