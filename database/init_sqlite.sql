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

-- 初始資料填充
INSERT INTO Plan_Configs (Tier_Name, Max_Total_Stocks) VALUES ('Free', 5);
INSERT INTO Plan_Configs (Tier_Name, Max_Total_Stocks) VALUES ('Premium_Tier_1', 20);
