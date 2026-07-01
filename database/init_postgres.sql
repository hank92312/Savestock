-- Savestock Database Schema (PostgreSQL)

-- 1. 方案設定表
CREATE TABLE IF NOT EXISTS Plan_Configs (
    Tier_ID SERIAL PRIMARY KEY,
    Tier_Name VARCHAR(50) NOT NULL,
    Max_Total_Stocks INTEGER NOT NULL DEFAULT 10
);

-- 2. 使用者資料表
CREATE TABLE IF NOT EXISTS Users (
    User_ID SERIAL PRIMARY KEY,
    Email VARCHAR(255) UNIQUE,
    OAuth_Provider VARCHAR(50),
    UUID TEXT UNIQUE NOT NULL,
    Created_At TIMESTAMP DEFAULT NOW()
);

-- 3. 使用者授權紀錄
CREATE TABLE IF NOT EXISTS User_Licenses (
    License_ID SERIAL PRIMARY KEY,
    User_ID INTEGER REFERENCES Users(User_ID),
    Tier_ID INTEGER REFERENCES Plan_Configs(Tier_ID),
    Purchase_Date TIMESTAMP DEFAULT NOW()
);

-- 4. 股票主檔
CREATE TABLE IF NOT EXISTS Stock_Master (
    Stock_ID VARCHAR(20) PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Sector VARCHAR(50),
    Avg_Dividend_2Y REAL,
    Avg_Dividend_5Y REAL,
    Dividend_1Y REAL,
    Default_Drop_Threshold REAL,
    Listing_Months INTEGER,
    Is_Default BOOLEAN DEFAULT FALSE,
    Last_Updated TIMESTAMP DEFAULT NOW()
);

-- 5. 使用者自選股票
CREATE TABLE IF NOT EXISTS User_Stocks (
    User_Stock_ID SERIAL PRIMARY KEY,
    User_ID INTEGER REFERENCES Users(User_ID),
    Stock_ID VARCHAR(20) REFERENCES Stock_Master(Stock_ID),
    Status VARCHAR(20) DEFAULT 'Active',
    Is_Default BOOLEAN DEFAULT FALSE,
    Custom_Drop_Threshold REAL,
    Created_At TIMESTAMP DEFAULT NOW(),
    UNIQUE(User_ID, Stock_ID)
);

-- 6. 每日股價資料
CREATE TABLE IF NOT EXISTS Daily_Prices (
    Price_ID SERIAL PRIMARY KEY,
    Stock_ID VARCHAR(20) REFERENCES Stock_Master(Stock_ID),
    Date DATE NOT NULL,
    Close_Price REAL NOT NULL,
    Volume BIGINT,
    Alert_Flag BOOLEAN DEFAULT FALSE,
    Alert_Reason TEXT,
    UNIQUE(Stock_ID, Date)
);

-- 7. 使用者偏好設定
CREATE TABLE IF NOT EXISTS User_Preferences (
    User_ID INTEGER PRIMARY KEY REFERENCES Users(User_ID),
    Push_Enabled BOOLEAN DEFAULT FALSE,
    Email_Enabled BOOLEAN DEFAULT FALSE,
    Updated_At TIMESTAMP DEFAULT NOW()
);

-- 8. 股利發放紀錄
CREATE TABLE IF NOT EXISTS Dividends (
    Stock_ID VARCHAR(20) REFERENCES Stock_Master(Stock_ID),
    Ex_Date DATE NOT NULL,
    Cash_Dividend REAL DEFAULT 0,
    Stock_Dividend REAL DEFAULT 0,
    UNIQUE(Stock_ID, Ex_Date)
);

-- ── ETF 追蹤模組（etf_tracker）────────────────────────────────────

-- 9. ETF 主檔 — 追蹤的 ETF 清單（含使用者自訂）
CREATE TABLE IF NOT EXISTS ETF_Master (
    ETF_ID VARCHAR(20) PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Category VARCHAR(20),
    Is_Custom BOOLEAN DEFAULT FALSE,
    Owner_User_ID INTEGER REFERENCES Users(User_ID),
    Last_Updated TIMESTAMP DEFAULT NOW()
);

-- 10. ETF 成分股當前快照 — ETL 以「先刪後插」覆蓋為最新 Top N
CREATE TABLE IF NOT EXISTS ETF_Holdings (
    ETF_ID VARCHAR(20) REFERENCES ETF_Master(ETF_ID),
    Stock_ID VARCHAR(20),
    Stock_Name VARCHAR(100),
    Weight REAL,
    Snapshot_Date DATE,
    UNIQUE(ETF_ID, Stock_ID)
);

-- 11. ETF 成分股歷史權重 — 每日 append，供「近10天權重趨勢」折線圖
CREATE TABLE IF NOT EXISTS ETF_Holding_History (
    ETF_ID VARCHAR(20) REFERENCES ETF_Master(ETF_ID),
    Stock_ID VARCHAR(20),
    Date DATE NOT NULL,
    Weight REAL,
    UNIQUE(ETF_ID, Stock_ID, Date)
);

-- 初始資料
INSERT INTO Plan_Configs (Tier_Name, Max_Total_Stocks) VALUES ('Free', 10) ON CONFLICT DO NOTHING;
INSERT INTO Plan_Configs (Tier_Name, Max_Total_Stocks) VALUES ('Premium_Tier_1', 20) ON CONFLICT DO NOTHING;

-- ETF 種子（16 檔，依 etf_tracker.md 兩大族群）
INSERT INTO ETF_Master (ETF_ID, Name, Category) VALUES
  ('0052.TW',  '富邦科技',              'Tech'),
  ('0053.TW',  '元大電子',              'Tech'),
  ('00881.TW', '國泰台灣科技龍頭',       'Tech'),
  ('00935.TW', '野村臺灣創新科技50',     'Tech'),
  ('00943.TW', '兆豐台灣電子成長高息等權重', 'Tech'),
  ('00735.TW', '國泰臺韓科技',           'Tech'),
  ('00905.TW', 'FT臺灣Smart',           'Tech'),
  ('00952.TW', '凱基台灣AI50',          'AI'),
  ('00851.TW', '台新全球AI',            'AI'),
  ('00762.TW', '元大全球人工智慧',       'AI'),
  ('00947.TW', '台新臺灣IC設計',         'AI'),
  ('00962.TW', '台新AI優息動能',         'AI'),
  ('00946.TW', '群益科技高息成長',       'AI'),
  ('00929.TW', '復華台灣科技優息',       'AI'),
  ('00876.TW', '元大全球5G關鍵科技',     'AI'),
  ('00861.TW', '元大全球未來通訊',       'AI')
ON CONFLICT DO NOTHING;
