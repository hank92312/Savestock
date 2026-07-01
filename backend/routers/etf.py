"""ETF 追蹤刷新端點：供 Cloud Scheduler 每日觸發，重用 etl/fetch_etf.py 的抓取邏輯。

與 routers/stocks.py 的 /stocks/refresh 同一慣例：無需驗證（Cloud Run 允許未驗證存取，
由 Cloud Scheduler 內部呼叫），單一端點觸發全部（16 檔固定 + 使用者自訂）ETF 更新。
"""
import os
import sys

from fastapi import APIRouter

# 讓 backend 能 import 同一份 etl 抓取邏輯（與 web_django/settings.py 加 etl 到
# sys.path 是同一個理由：一份成分股抓取/寫入邏輯，避免 API 端另外重寫一份）
_ETL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "etl")
_ETL_DIR = os.path.normpath(_ETL_DIR)
if _ETL_DIR not in sys.path:
    sys.path.insert(0, _ETL_DIR)

router = APIRouter(prefix="/etf", tags=["etf"])


@router.post("/refresh")
def refresh_etf():
    """重新抓取全部 ETF（16 檔固定 + 資料庫中使用者自訂）成分股與成分股收盤價。"""
    import fetch_etf  # 延遲 import：避免 etl 的重依賴（yfinance 等）拖慢 API 啟動

    return fetch_etf.run()
