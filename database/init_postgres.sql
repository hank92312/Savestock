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

-- 初始資料
INSERT INTO Plan_Configs (Tier_Name, Max_Total_Stocks) VALUES ('Free', 5) ON CONFLICT DO NOTHING;
INSERT INTO Plan_Configs (Tier_Name, Max_Total_Stocks) VALUES ('Premium_Tier_1', 20) ON CONFLICT DO NOTHING;
