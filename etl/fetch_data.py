import os
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import datetime, timedelta

# 載入環境變數
load_dotenv()

def fetch_stock_data(stock_id: str):
    """
    抓取指定股票的歷史資料與綜合股利資訊 (包含現金與配股)
    """
    print(f"正在抓取 {stock_id} 的資料...")
    ticker = yf.Ticker(stock_id)
    
    # 1. 抓取歷史股價 (過去 1 個月，用於判定異常與最新收盤價)
    hist = ticker.history(period="1mo")
    if hist.empty:
        print(f"找不到 {stock_id} 的股價資料")
        return None
    
    # 2. 抓取股息與配股 (Actions 包含 Dividends 與 Stock Splits)
    actions = ticker.actions
    two_years_ago = datetime.now() - timedelta(days=365*2)
    recent_actions = actions[actions.index > two_years_ago.replace(tzinfo=actions.index.tzinfo)]
    
    # 計算兩年平均現金股利 (Dividends 欄位)
    total_cash = recent_actions['Dividends'].sum()
    avg_cash_2y = total_cash / 2
    
    # 計算兩年平均股票股利 (Stock Splits 欄位)
    # yfinance 的 Stock Splits 若為 1.1 表示配股 10%，在台灣相當於配股 1.0 元
    # 公式：(Split_Ratio - 1) * 10 = 配股元數
    stock_splits = recent_actions[recent_actions['Stock Splits'] > 0]
    total_stock_div = 0
    for split in stock_splits['Stock Splits']:
        if split > 0:
            total_stock_div += (split - 1) * 10
    avg_stock_2y = total_stock_div / 2
    
    # 綜合股利 (現金 + 配股折算)
    combined_dividend = avg_cash_2y + avg_stock_2y
    
    # 3. 獲取最新一筆交易資料
    latest_day = hist.iloc[-1]
    prev_day = hist.iloc[-2] if len(hist) > 1 else latest_day
    
    # 計算報酬率 (殖利率)
    yield_rate = (combined_dividend / latest_day['Close']) * 100
    
    # 計算跌幅與成交量倍數
    price_change = ((latest_day['Close'] - prev_day['Close']) / prev_day['Close']) * 100
    avg_volume_20d = hist['Volume'].tail(20).mean()
    volume_ratio = latest_day['Volume'] / avg_volume_20d if avg_volume_20d > 0 else 1
    
    # 異常警示判定
    alert_flag = False
    alert_reason = []
    
    if price_change <= -2.5: 
        alert_flag = True
        alert_reason.append(f"價格跌幅: {price_change:.2f}%")
        
    if volume_ratio >= 2.5:
        alert_flag = True
        alert_reason.append(f"成交量異常: {volume_ratio:.2f}倍")
        
    return {
        "stock_id": stock_id,
        "date": latest_day.name.date(),
        "close": latest_day['Close'],
        "avg_cash_2y": avg_cash_2y,
        "avg_stock_2y": avg_stock_2y,
        "combined_dividend": combined_dividend,
        "yield_rate": yield_rate,
        "alert_flag": alert_flag,
        "alert_reason": ", ".join(alert_reason)
    }

def main():
    # 範例股票清單 (台股需要加上 .TW)
    target_stocks = ["2330.TW", "2317.TW", "2454.TW"]
    
    results = []
    for sid in target_stocks:
        data = fetch_stock_data(sid)
        if data:
            results.append(data)
            print(f"Result for {sid}: {data}")

    # TODO: 寫入資料庫邏輯
    # engine = create_engine(os.getenv("DATABASE_URL"))
    # df = pd.DataFrame(results)
    # ...

if __name__ == "__main__":
    main()
