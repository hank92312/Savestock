# Savestock Database Documentation

此目錄存放 Savestock 系統的資料庫定義與管理腳本。

## 1. 資料庫選型
*   **建議環境**：PostgreSQL 14+ (亦可調整為 SQL Server)。
*   **字元集**：UTF-8。

## 2. 快速開始
若要建立資料庫結構，請在安裝好 PostgreSQL 後執行以下指令：

```bash
psql -U your_username -d savestock -f init_schema.sql
```

## 3. 資料表說明 (Schema Overview)

| 資料表 | 用途 | 關鍵欄位 |
| :--- | :--- | :--- |
| `Users` | 儲存會員與訪客資訊 | `UUID` (訪客), `Email` (會員) |
| `Plan_Configs` | 定義不同等級的權限額度 | `Max_Total_Stocks` |
| `Stock_Master` | 股票清單與靜態數據 | `Avg_Dividend_2Y`, `Sector` |
| `Daily_Prices` | 每日行情與警示紀錄 | `Alert_Flag`, `Alert_Reason` |
| `User_Stocks` | 使用者自選清單 | `Custom_Drop_Threshold` |

## 4. 核心邏輯 SQL 範例

### A. 查詢達標股票 (殖利率 >= 5%)
```sql
SELECT Stock_ID, Name, 
       (Avg_Dividend_2Y / (SELECT Close_Price FROM Daily_Prices WHERE Stock_ID = SM.Stock_ID ORDER BY Date DESC LIMIT 1)) * 100 AS Yield
FROM Stock_Master SM
WHERE (Avg_Dividend_2Y / (SELECT Close_Price FROM Daily_Prices WHERE Stock_ID = SM.Stock_ID ORDER BY Date DESC LIMIT 1)) >= 0.05;
```

### B. 查詢今日觸發異常警示的股票
```sql
SELECT SM.Name, DP.Close_Price, DP.Alert_Reason
FROM Daily_Prices DP
JOIN Stock_Master SM ON DP.Stock_ID = SM.Stock_ID
WHERE DP.Date = CURRENT_DATE AND DP.Alert_Flag = TRUE;
```

## 5. 維護建議
*   **備份**：建議每日收盤後執行 ETL 完畢後進行 `pg_dump`。
*   **索引**：已針對 `Stock_ID` 與 `User_ID` 建立外鍵索引，若未來查詢變慢，可針對 `Daily_Prices.Date` 建立額外索引。
