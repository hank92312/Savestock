-- Savestock Database Schema (SQLite Compatible)

-- 1. 方案設定表 (Plan Configs)
CREATE TABLE Plan_Configs (
    Tier_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Tier_Name VARCHAR(50) NOT NULL,
    Max_Total_Stocks INTEGER NOT NULL DEFAULT 10
);

-- 2. 使用者資料表 (Users)
CREATE TABLE Users (
    User_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Email VARCHAR(255) UNIQUE,
    OAuth_Provider VARCHAR(50), 
    UUID TEXT UNIQUE NOT NULL,    
    Created_At DATETIME DEFAULT (datetime('now', 'localtime'))
);

-- 3. 使用者授權紀錄 (User Licenses)
CREATE TABLE User_Licenses (
    License_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    User_ID INTEGER REFERENCES Users(User_ID),
    Tier_ID INTEGER REFERENCES Plan_Configs(Tier_ID),
    Purchase_Date DATETIME DEFAULT (datetime('now', 'localtime'))
);

-- 4. 股票主檔 (Stock Master)
CREATE TABLE Stock_Master (
    Stock_ID VARCHAR(20) PRIMARY KEY, 
    Name VARCHAR(100) NOT NULL,
    Sector VARCHAR(50),               
    Avg_Dividend_2Y REAL,             -- ≥24月：近2年股利年均；<24月：上市迄今年化
    Avg_Dividend_5Y REAL,             -- ≥60月：近5年股利年均；<60月：上市迄今年化
    Dividend_1Y REAL,                 -- 近12個月股利合計（近一年殖利率用）
    Default_Drop_Threshold REAL,
    Listing_Months INTEGER,           -- 上市迄今月數；< 24 視為新上市（NULL = 未知，視為已滿2年）
    Last_Updated DATETIME DEFAULT (datetime('now', 'localtime'))
);

-- 5. 使用者自選股票 (User Stocks)
CREATE TABLE User_Stocks (
    User_Stock_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    User_ID INTEGER REFERENCES Users(User_ID),
    Stock_ID VARCHAR(20) REFERENCES Stock_Master(Stock_ID),
    Status VARCHAR(20) DEFAULT 'Active', 
    Is_Default BOOLEAN DEFAULT 0,    
    Custom_Drop_Threshold REAL, 
    Created_At DATETIME DEFAULT (datetime('now', 'localtime')),
    UNIQUE(User_ID, Stock_ID)
);

-- 6. 每日股價資料 (Daily Prices)
CREATE TABLE Daily_Prices (
    Price_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Stock_ID VARCHAR(20) REFERENCES Stock_Master(Stock_ID),
    Date DATE NOT NULL,
    Close_Price REAL NOT NULL,
    Volume INTEGER,
    Alert_Flag BOOLEAN DEFAULT 0,    
    Alert_Reason TEXT,                   
    UNIQUE(Stock_ID, Date)
);

-- 7. 使用者偏好設定 (User Preferences)
CREATE TABLE User_Preferences (
    User_ID INTEGER PRIMARY KEY REFERENCES Users(User_ID),
    Push_Enabled BOOLEAN DEFAULT 0,
    Email_Enabled BOOLEAN DEFAULT 0,
    Updated_At DATETIME DEFAULT (datetime('now', 'localtime'))
);

-- 8. 股利發放紀錄 (Dividends) — 供詳情頁股利折線圖
CREATE TABLE Dividends (
    Stock_ID VARCHAR(20) REFERENCES Stock_Master(Stock_ID),
    Ex_Date DATE NOT NULL,         -- 除權息日（yfinance actions 索引日期）
    Cash_Dividend REAL DEFAULT 0,  -- 每股現金股利（元）
    Stock_Dividend REAL DEFAULT 0, -- 每股股票股利（配股，面額還原成元 =(配股比-1)×10）
    UNIQUE(Stock_ID, Ex_Date)
);

-- ── ETF 追蹤模組（etf_tracker）────────────────────────────────────

-- 9. ETF 主檔 (ETF Master) — 追蹤的 ETF 清單（含使用者自訂）
CREATE TABLE ETF_Master (
    ETF_ID VARCHAR(20) PRIMARY KEY,   -- 如 '00881.TW'
    Name VARCHAR(100) NOT NULL,
    Category VARCHAR(20),             -- 'Tech' 綜合型科技／'AI' 創新科技主題／'Custom' 使用者自訂
    Is_Custom BOOLEAN DEFAULT 0,      -- 1 = 使用者自行新增的 ETF
    Owner_User_ID INTEGER REFERENCES Users(User_ID),  -- 系統預設為 NULL；自訂 ETF 記擁有者
    Last_Updated DATETIME DEFAULT (datetime('now', 'localtime'))
);

-- 10. ETF 成分股當前快照 (ETF Holdings) — 每次 ETL 刷新以「先刪後插」覆蓋為最新 Top N
CREATE TABLE ETF_Holdings (
    ETF_ID VARCHAR(20) REFERENCES ETF_Master(ETF_ID),
    Stock_ID VARCHAR(20),             -- 成分股代號（可能為海外股，故不強制 FK 到 Stock_Master）
    Stock_Name VARCHAR(100),          -- 成分股名稱（海外股未必在 Stock_Master，就近保存）
    Weight REAL,                      -- 權重（百分比，如 41.72）
    Snapshot_Date DATE,               -- 此快照抓取日期
    UNIQUE(ETF_ID, Stock_ID)
);

-- 11. ETF 成分股歷史權重 (ETF Holding History) — 每日 append，供「近10天權重趨勢」折線圖
CREATE TABLE ETF_Holding_History (
    ETF_ID VARCHAR(20) REFERENCES ETF_Master(ETF_ID),
    Stock_ID VARCHAR(20),
    Date DATE NOT NULL,
    Weight REAL,
    UNIQUE(ETF_ID, Stock_ID, Date)
);

-- 初始資料填充
INSERT INTO Plan_Configs (Tier_Name, Max_Total_Stocks) VALUES ('Free', 10);
INSERT INTO Plan_Configs (Tier_Name, Max_Total_Stocks) VALUES ('Premium_Tier_1', 20);

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
  ('00861.TW', '元大全球未來通訊',       'AI');
