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
}

# 預設追蹤的 14 檔股票，含名稱與產業別（由系統固定，不依賴 yfinance sector 欄位）
TARGET_STOCKS = [
    {"id": "0056.TW",  "name": "元大高股息",      "sector": "ETF"},
    {"id": "00878.TW", "name": "國泰永續高股息",   "sector": "ETF"},
    {"id": "00919.TW", "name": "群益台灣精選高息", "sector": "ETF"},
    {"id": "00929.TW", "name": "復華台灣科技優息", "sector": "ETF"},
    {"id": "00900.TW", "name": "富邦特選高股息30", "sector": "ETF"},
    {"id": "2892.TW",  "name": "第一金",           "sector": "Finance"},
    {"id": "2838.TW",  "name": "聯邦銀",           "sector": "Finance"},
    {"id": "2887.TW",  "name": "台新金",           "sector": "Finance"},
    {"id": "2542.TW",  "name": "興富發",           "sector": "Construction"},
    {"id": "5522.TW",  "name": "遠雄",             "sector": "Construction"},
    {"id": "2412.TW",  "name": "中華電信",         "sector": "Telecom"},
    {"id": "3045.TW",  "name": "台灣大哥大",       "sector": "Telecom"},
    {"id": "1216.TW",  "name": "統一企業",         "sector": "Food"},
    {"id": "1210.TW",  "name": "大成長城",         "sector": "Food"},
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
    
    # 2. 抓取股息與配股
    actions = ticker.actions
    avg_cash_2y = 0
    avg_stock_2y = 0
    
    if not actions.empty:
        # 處理時區問題，確保比較基準一致
        two_years_ago = datetime.now() - timedelta(days=365*2)
        if actions.index.tzinfo:
            two_years_ago = two_years_ago.replace(tzinfo=actions.index.tzinfo)
        else:
            two_years_ago = two_years_ago.replace(tzinfo=None)
            
        recent_actions = actions[actions.index > two_years_ago]
        
        if 'Dividends' in recent_actions.columns:
            avg_cash_2y = recent_actions['Dividends'].sum() / 2
        
        if 'Stock Splits' in recent_actions.columns:
            stock_splits = recent_actions[recent_actions['Stock Splits'] > 0]
            # 台股配股計算邏輯：(拆分比例 - 1) * 10 (面額)
            total_stock_div = sum([(split - 1) * 10 for split in stock_splits['Stock Splits']])
            avg_stock_2y = total_stock_div / 2
    
    combined_dividend = avg_cash_2y + avg_stock_2y
    
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
        "stock_id":       stock_id,
        "name":           name,
        "sector":         sector,
        "avg_dividend_2y": combined_dividend,
        "price_rows":     price_rows,
    }

def save_to_db(data):
    """
    將資料寫入資料庫 (Upsert 邏輯)
    """
    with engine.begin() as conn:
        # 1. 更新 Stock_Master
        upsert_stock_master = text("""
            INSERT INTO Stock_Master (Stock_ID, Name, Sector, Avg_Dividend_2Y, Is_Default, Last_Updated)
            VALUES (:sid, :name, :sector, :avg_div, 1, CURRENT_TIMESTAMP)
            ON CONFLICT (Stock_ID) DO UPDATE SET
                Name = EXCLUDED.Name,
                Sector = EXCLUDED.Sector,
                Avg_Dividend_2Y = EXCLUDED.Avg_Dividend_2Y,
                Is_Default = 1,
                Last_Updated = CURRENT_TIMESTAMP;
        """)
        conn.execute(upsert_stock_master, {
            "sid": data['stock_id'],
            "name": data['name'],
            "sector": data['sector'],
            "avg_div": data['avg_dividend_2y']
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
                    VALUES (:sid, :date, :close, :volume, 0, '')
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
