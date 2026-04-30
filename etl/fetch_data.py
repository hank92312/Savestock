import os
import pandas as pd
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

def fetch_stock_data(stock_id: str):
    """
    抓取指定股票的歷史資料與綜合股利資訊 (包含現金與配股)
    """
    print(f"正在抓取 {stock_id} 的資料...")
    ticker = yf.Ticker(stock_id)
    
    # 1. 抓取歷史股價
    hist = ticker.history(period="1mo")
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
    
    # 警示判定
    alert_flag = False
    alert_reason = []
    if price_change <= -2.5: alert_reason.append(f"跌幅:{price_change:.2f}%")
    if volume_ratio >= 2.5: alert_reason.append(f"爆量:{volume_ratio:.2f}倍")
    if alert_reason: alert_flag = True

    return {
        "stock_id": stock_id,
        "name": ticker.info.get('shortName', stock_id),
        "sector": ticker.info.get('sector', 'Unknown'),
        "date": latest_day.name.date(),
        "close": latest_day['Close'],
        "volume": latest_day['Volume'],
        "avg_dividend_2y": combined_dividend,
        "alert_flag": alert_flag,
        "alert_reason": ", ".join(alert_reason)
    }

def save_to_db(data):
    """
    將資料寫入資料庫 (Upsert 邏輯)
    """
    with engine.begin() as conn:
        # 1. 更新 Stock_Master
        upsert_stock_master = text("""
            INSERT INTO Stock_Master (Stock_ID, Name, Sector, Avg_Dividend_2Y, Last_Updated)
            VALUES (:sid, :name, :sector, :avg_div, CURRENT_TIMESTAMP)
            ON CONFLICT (Stock_ID) DO UPDATE SET
                Name = EXCLUDED.Name,
                Sector = EXCLUDED.Sector,
                Avg_Dividend_2Y = EXCLUDED.Avg_Dividend_2Y,
                Last_Updated = CURRENT_TIMESTAMP;
        """)
        conn.execute(upsert_stock_master, {
            "sid": data['stock_id'],
            "name": data['name'],
            "sector": data['sector'],
            "avg_div": data['avg_dividend_2y']
        })

        # 2. 更新 Daily_Prices
        upsert_daily_price = text("""
            INSERT INTO Daily_Prices (Stock_ID, Date, Close_Price, Volume, Alert_Flag, Alert_Reason)
            VALUES (:sid, :date, :close, :volume, :alert_flag, :alert_reason)
            ON CONFLICT (Stock_ID, Date) DO UPDATE SET
                Close_Price = EXCLUDED.Close_Price,
                Volume = EXCLUDED.Volume,
                Alert_Flag = EXCLUDED.Alert_Flag,
                Alert_Reason = EXCLUDED.Alert_Reason;
        """)
        conn.execute(upsert_daily_price, {
            "sid": data['stock_id'],
            "date": data['date'],
            "close": data['close'],
            "volume": data['volume'],
            "alert_flag": data['alert_flag'],
            "alert_reason": data['alert_reason']
        })
    print(f"資料庫更新成功: {data['stock_id']}")

def main():
    # 根據 Default Stock List.md 定義的 10 檔預設目標
    target_stocks = [
        "0056.TW",  # 元大高股息
        "00878.TW", # 國泰永續高股息
        "00919.TW", # 群益台灣精選高息
        "00929.TW", # 復華台灣科技優息
        "00900.TW", # 富邦特選高股息30
        "2892.TW",  # 第一金
        "2838.TW",  # 聯邦銀
        "2887.TW",  # 台新金
        "2542.TW",  # 興富發
        "5522.TW"   # 遠雄
    ]
    
    for sid in target_stocks:
        data = fetch_stock_data(sid)
        if data:
            try:
                save_to_db(data)
            except Exception as e:
                print(f"寫入資料庫失敗 {sid}: {e}")

if __name__ == "__main__":
    main()
