-- Savestock Database Schema (PostgreSQL Compatible)

-- 1. 方案設定表 (Plan Configs)
CREATE TABLE Plan_Configs (
    Tier_ID SERIAL PRIMARY KEY,
    Tier_Name VARCHAR(50) NOT NULL,
    Max_Total_Stocks INTEGER NOT NULL DEFAULT 10
);

-- 2. 使用者資料表 (Users)
CREATE TABLE Users (
    User_ID SERIAL PRIMARY KEY,
    Email VARCHAR(255) UNIQUE,
    OAuth_Provider VARCHAR(50), -- e.g., 'google', 'apple'
    UUID UUID UNIQUE NOT NULL,    -- 用於訪客模式識別
    Created_At TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. 使用者授權紀錄 (User Licenses)
CREATE TABLE User_Licenses (
    License_ID SERIAL PRIMARY KEY,
    User_ID INTEGER REFERENCES Users(User_ID) ON DELETE CASCADE,
    Tier_ID INTEGER REFERENCES Plan_Configs(Tier_ID),
    Purchase_Date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. 股票主檔 (Stock Master)
CREATE TABLE Stock_Master (
    Stock_ID VARCHAR(20) PRIMARY KEY, -- e.g., '2330.TW'
    Name VARCHAR(100) NOT NULL,
    Sector VARCHAR(50),               -- 產業類別 (用於波動警示判定)
    Avg_Dividend_2Y DECIMAL(10, 2),   -- 過去 2 年平均股息
    Default_Drop_Threshold DECIMAL(5, 2), -- 預設跌幅警示門檻 (如 5.0 表示 5%)
    Last_Updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. 使用者自選股票 (User Stocks)
CREATE TABLE User_Stocks (
    User_Stock_ID SERIAL PRIMARY KEY,
    User_ID INTEGER REFERENCES Users(User_ID) ON DELETE CASCADE,
    Stock_ID VARCHAR(20) REFERENCES Stock_Master(Stock_ID),
    Status VARCHAR(20) DEFAULT 'Active', -- Active, Hidden
    Is_Default BOOLEAN DEFAULT FALSE,    -- 是否為系統預設的 10 檔
    Custom_Drop_Threshold DECIMAL(5, 2), -- 使用者自訂跌幅門檻
    Created_At TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(User_ID, Stock_ID)
);

-- 6. 每日股價資料 (Daily Prices)
CREATE TABLE Daily_Prices (
    Price_ID SERIAL PRIMARY KEY,
    Stock_ID VARCHAR(20) REFERENCES Stock_Master(Stock_ID) ON DELETE CASCADE,
    Date DATE NOT NULL,
    Close_Price DECIMAL(10, 2) NOT NULL,
    Volume BIGINT,
    Alert_Flag BOOLEAN DEFAULT FALSE,    -- 是否觸發異常警示
    Alert_Reason TEXT,                   -- 警示原因 (如：跌幅過大、爆量)
    UNIQUE(Stock_ID, Date)
);

-- 7. 使用者偏好設定 (User Preferences)
CREATE TABLE User_Preferences (
    User_ID INTEGER PRIMARY KEY REFERENCES Users(User_ID) ON DELETE CASCADE,
    Push_Enabled BOOLEAN DEFAULT FALSE,
    Email_Enabled BOOLEAN DEFAULT FALSE,
    Updated_At TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 初始資料填充
INSERT INTO Plan_Configs (Tier_Name, Max_Total_Stocks) VALUES ('Free', 5);
INSERT INTO Plan_Configs (Tier_Name, Max_Total_Stocks) VALUES ('Premium_Tier_1', 20);
