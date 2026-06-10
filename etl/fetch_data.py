import os
import yfinance as yf
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime, timedelta

# 載入環境變數
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

# 資料庫連線設定 (從環境變數讀取，預設改為 SQLite 以利測試)
DEFAULT_DB = "sqlite:///c:/Savestock/savestock.db"
DB_URL = os.getenv("DATABASE_URL", DEFAULT_DB)
engine = create_engine(DB_URL)

# 依產業別設定單日跌幅警示閾值（小數格式，例如 0.025 = 2.5%）
SECTOR_THRESHOLDS = {
    "ETF":           0.04,
    "Finance":       0.025,
    "Telecom":       0.025,
    "Construction":  0.06,
    "Food":          0.03,
    "Semiconductor": 0.05,
    "Other":         0.04,
}

# 預設追蹤的 25 檔股票，含名稱與產業別（由系統固定，不依賴 yfinance sector 欄位）
TARGET_STOCKS = [
    # ETF
    {"id": "0056.TW",  "name": "元大高股息",        "sector": "ETF"},
    {"id": "00878.TW", "name": "國泰永續高股息",     "sector": "ETF"},
    {"id": "00919.TW", "name": "群益台灣精選高息",   "sector": "ETF"},
    {"id": "00929.TW", "name": "復華台灣科技優息",   "sector": "ETF"},
    {"id": "00900.TW", "name": "富邦特選高股息30",   "sector": "ETF"},
    {"id": "00713.TW", "name": "元大台灣高息低波",   "sector": "ETF"},
    # Finance
    {"id": "2892.TW",  "name": "第一金",             "sector": "Finance"},
    {"id": "2838.TW",  "name": "聯邦銀",             "sector": "Finance"},
    {"id": "2887.TW",  "name": "台新金",             "sector": "Finance"},
    {"id": "2884.TW",  "name": "玉山金",             "sector": "Finance"},
    {"id": "2886.TW",  "name": "兆豐金",             "sector": "Finance"},
    {"id": "2890.TW",  "name": "永豐金",             "sector": "Finance"},
    {"id": "5880.TW",  "name": "合庫金",             "sector": "Finance"},
    # Construction
    {"id": "2542.TW",  "name": "興富發",             "sector": "Construction"},
    {"id": "5522.TW",  "name": "遠雄",               "sector": "Construction"},
    # Telecom
    {"id": "2412.TW",  "name": "中華電信",           "sector": "Telecom"},
    {"id": "3045.TW",  "name": "台灣大哥大",         "sector": "Telecom"},
    {"id": "4904.TW",  "name": "遠傳電信",           "sector": "Telecom"},
    # Food
    {"id": "1216.TW",  "name": "統一企業",           "sector": "Food"},
    {"id": "1210.TW",  "name": "大成長城",           "sector": "Food"},
    {"id": "2912.TW",  "name": "統一超",             "sector": "Food"},
    # Other
    {"id": "9917.TW",  "name": "中保科",             "sector": "Other"},
    {"id": "1102.TW",  "name": "亞泥",               "sector": "Other"},
    {"id": "2347.TW",  "name": "聯強",               "sector": "Other"},
    {"id": "2633.TW",  "name": "台灣高鐵",           "sector": "Other"},
]

def fetch_stock_data(stock_id: str, name: str, sector: str):
    """
    抓取指定股票的歷史資料與綜合股利資訊 (包含現金與配股)
    """
    print(f"正在抓取 {stock_id} 的資料...")
    ticker = yf.Ticker(stock_id)

    # 1. 抓取歷史股價（最多 1 年，剔除未收盤的 NaN 列）
    hist = ticker.history(period="1y")
    hist = hist.dropna(subset=["Close", "Volume"])
    if hist.empty:
        print(f"找不到 {stock_id} 的股價資料")
        return None
    
    # 2. 判斷上市迄今月數（不滿 2 年改用上市迄今年化）
    info = ticker.info
    epoch = None
    if info:
        ms = info.get("firstTradeDateMilliseconds")
        epoch = ms / 1000 if ms else info.get("firstTradeDateEpochUtc")
    listing_months = None
    if epoch:
        try:
            listing_date = datetime.fromtimestamp(epoch)
            listing_months = max(int((datetime.now() - listing_date).days / 30.44), 1)
        except (OverflowError, OSError, ValueError):
            listing_months = None
    is_new = listing_months is not None and listing_months < 24

    # 3. 抓取股息與配股
    actions = ticker.actions
    combined_dividend = 0
    avg_dividend_5y = 0

    def _calc_avg(src, divisor):
        """計算現金＋配股年均股利（src = 篩選後的 actions，divisor = 年數）。"""
        cash = src['Dividends'].sum() / divisor if 'Dividends' in src.columns else 0
        stock = 0
        if 'Stock Splits' in src.columns:
            splits = src[src['Stock Splits'] > 1]['Stock Splits']
            stock = sum((s - 1) * 10 for s in splits) / divisor
        return cash + stock

    if not actions.empty:
        # ── 2 年均 ──────────────────────────────────────────────
        if is_new:
            combined_dividend = _calc_avg(actions, (listing_months / 12) or 1)
        else:
            two_years_ago = datetime.now() - timedelta(days=365*2)
            if actions.index.tzinfo:
                two_years_ago = two_years_ago.replace(tzinfo=actions.index.tzinfo)
            combined_dividend = _calc_avg(actions[actions.index > two_years_ago], 2)

        # ── 5 年均 ──────────────────────────────────────────────
        is_under_5y = listing_months is not None and listing_months < 60
        if is_under_5y:
            avg_dividend_5y = _calc_avg(actions, (listing_months / 12) or 1)
        else:
            five_years_ago = datetime.now() - timedelta(days=365*5)
            if actions.index.tzinfo:
                five_years_ago = five_years_ago.replace(tzinfo=actions.index.tzinfo)
            avg_dividend_5y = _calc_avg(actions[actions.index > five_years_ago], 5)
    else:
        combined_dividend = 0
        avg_dividend_5y = 0

    # 近 12 個月現金股利合計（近一年殖利率用）
    dividend_1y = 0
    if not actions.empty and 'Dividends' in actions.columns:
        one_year_ago = datetime.now() - timedelta(days=365)
        if actions.index.tzinfo:
            one_year_ago = one_year_ago.replace(tzinfo=actions.index.tzinfo)
        else:
            one_year_ago = one_year_ago.replace(tzinfo=None)
        dividend_1y = float(actions[actions.index > one_year_ago]['Dividends'].sum())

    # 3. 獲取最新資料
    latest_day = hist.iloc[-1]
    prev_day = hist.iloc[-2] if len(hist) > 1 else latest_day
    
    price_change = ((latest_day['Close'] - prev_day['Close']) / prev_day['Close']) * 100
    avg_volume_20d = hist['Volume'].tail(20).mean()
    volume_ratio = latest_day['Volume'] / avg_volume_20d if avg_volume_20d > 0 else 1
    
    # 依產業別套用跌幅警示閾值
    drop_threshold = SECTOR_THRESHOLDS.get(sector, 0.04) * 100
    alert_flag = False
    alert_reason = []
    if price_change <= -drop_threshold:
        alert_reason.append(f"跌幅:{price_change:.2f}%")
    if volume_ratio >= 2.5:
        alert_reason.append(f"爆量:{volume_ratio:.2f}倍")
    if alert_reason:
        alert_flag = True

    # 所有歷史列（警示只標記最後一筆）
    price_rows = []
    latest_ts = hist.index[-1]
    for ts, row in hist.iterrows():
        is_latest = ts == latest_ts
        price_rows.append({
            "date":         ts.date(),
            "close":        float(row["Close"]),
            "volume":       int(row["Volume"]),
            "alert_flag":   alert_flag if is_latest else False,
            "alert_reason": ", ".join(alert_reason) if is_latest else "",
        })

    return {
        "stock_id":        stock_id,
        "name":            name,
        "sector":          sector,
        "avg_dividend_2y": float(combined_dividend),   # numpy float64 → Python float
        "avg_dividend_5y": float(avg_dividend_5y),
        "dividend_1y":     float(dividend_1y),
        "listing_months":  listing_months,
        "drop_threshold":  SECTOR_THRESHOLDS.get(sector, 0.04),
        "price_rows":      price_rows,
    }

def save_to_db(data):
    """
    將資料寫入資料庫 (Upsert 邏輯)
    """
    with engine.begin() as conn:
        # 1. 更新 Stock_Master
        upsert_stock_master = text("""
            INSERT INTO Stock_Master (Stock_ID, Name, Sector, Avg_Dividend_2Y, Avg_Dividend_5Y, Dividend_1Y, Default_Drop_Threshold, Listing_Months, Is_Default, Last_Updated)
            VALUES (:sid, :name, :sector, :avg_div, :avg_div_5y, :div_1y, :drop_threshold, :listing_months, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (Stock_ID) DO UPDATE SET
                Name = EXCLUDED.Name,
                Sector = EXCLUDED.Sector,
                Avg_Dividend_2Y = EXCLUDED.Avg_Dividend_2Y,
                Avg_Dividend_5Y = EXCLUDED.Avg_Dividend_5Y,
                Dividend_1Y = EXCLUDED.Dividend_1Y,
                Default_Drop_Threshold = EXCLUDED.Default_Drop_Threshold,
                Listing_Months = EXCLUDED.Listing_Months,
                Is_Default = TRUE,
                Last_Updated = CURRENT_TIMESTAMP;
        """)
        conn.execute(upsert_stock_master, {
            "sid": data['stock_id'],
            "name": data['name'],
            "sector": data['sector'],
            "avg_div": data['avg_dividend_2y'],
            "avg_div_5y": data['avg_dividend_5y'],
            "div_1y": data['dividend_1y'],
            "drop_threshold": data['drop_threshold'],
            "listing_months": data['listing_months']
        })

        # 2. 更新 Daily_Prices（所有歷史列）
        #    最新一筆用 UPSERT 覆蓋（確保今日警示最新）
        #    歷史列用 DO NOTHING 保留已有的警示資料
        latest_date = data['price_rows'][-1]['date']
        for pr in data['price_rows']:
            if pr['date'] == latest_date:
                conn.execute(text("""
                    INSERT INTO Daily_Prices (Stock_ID, Date, Close_Price, Volume, Alert_Flag, Alert_Reason)
                    VALUES (:sid, :date, :close, :volume, :alert_flag, :alert_reason)
                    ON CONFLICT (Stock_ID, Date) DO UPDATE SET
                        Close_Price = EXCLUDED.Close_Price,
                        Volume = EXCLUDED.Volume,
                        Alert_Flag = EXCLUDED.Alert_Flag,
                        Alert_Reason = EXCLUDED.Alert_Reason;
                """), {"sid": data['stock_id'], "date": pr['date'],
                       "close": pr['close'], "volume": pr['volume'],
                       "alert_flag": pr['alert_flag'], "alert_reason": pr['alert_reason']})
            else:
                conn.execute(text("""
                    INSERT INTO Daily_Prices (Stock_ID, Date, Close_Price, Volume, Alert_Flag, Alert_Reason)
                    VALUES (:sid, :date, :close, :volume, FALSE, '')
                    ON CONFLICT (Stock_ID, Date) DO NOTHING;
                """), {"sid": data['stock_id'], "date": pr['date'],
                       "close": pr['close'], "volume": pr['volume']})
    print(f"資料庫更新成功: {data['stock_id']}")

def main():
    for stock in TARGET_STOCKS:
        data = fetch_stock_data(stock["id"], stock["name"], stock["sector"])
        if data:
            try:
                save_to_db(data)
            except Exception as e:
                print(f"寫入資料庫失敗 {stock['id']}: {e}")

if __name__ == "__main__":
    main()
