

# 專案架構文件：Savestock (長線存股防護系統)

## 1. 專案概述 (Project Overview)
* **專案名稱**：Savestock 
* **核心目標**：建立一個以「儲蓄股利」為主的股票追蹤系統，強調長期投資與風險對抗，非短期獲利。
* **目標受眾**：存股族、價值投資者、理財新手。
* **部署平台**：跨平台支援 (Android / iOS / Windows / Linux)。
* **核心理念**：透過「2年平均股息」計算真實報酬率，並利用「絕對數值」觸發異常警示，協助使用者避開高殖利率陷阱。

## 2. 開發環境與技術選型 (Tech Stack & Environment)
* **開發 IDE**：Visual Studio Code (VS Code)。
* **前端 (Frontend / UI)**：Flutter (Dart語言)。負責處理跨平台的高流暢度動畫、財經圖表繪製與使用者互動。
* **後端 API (Backend)**：Python (FastAPI 或 Flask)。提供 RESTful API 供 Flutter 呼叫。
* **資料抓取與運算 (ETL)**：Python (Pandas + Requests)。負責每日定時抓取台股盤後資料、清理資料並執行殖利率與防護警示邏輯的運算。
* **資料庫 (Database)**：SQLite (開發與測試階段) / PostgreSQL (生產環境)。透過 SQL 語法進行會員授權與股票清單的結構化管理。
* **快取 (Cache)**：Redis (選配，目前暫以 SQLite 效能為準)。
* **通知系統 (Notifications)**：Firebase Cloud Messaging (FCM) 負責跨平台 App 推播，SendGrid/AWS SES 負責郵件通知。

## 3. 功能模組 (Functional Modules)

### A. 權限與額度管理
* **訪客模式 (Guest)**：免註冊使用，資料存於本地端 (與 Device UUID 綁定)，卸載即遺失。
* **註冊模式 (Member)**：支援 Google/Apple 第三方快速登入，資料雲端同步。
* **買斷機制 (One-time Purchase)**：
    * **免費版**：預設 10 檔股票 (可設定為隱藏/屏蔽) + 3 檔自訂股票。
    * **付費買斷版**：總量擴充至 20 檔 (預設 10 檔可刪除並替換為自訂標的)，支援後續升級更高階的 Tier 擴充包。

### B. 資料計算邏輯 (Financial Logic)
* **基準股利計算**：
    * 上市 $\ge$ 2 年：採過去 2 年現金股利平均值。
    * 上市 $<$ 2 年：採上市至今平均值，前端觸發 `New_Listing` 視覺提示。
* **報酬率公式**：`預估殖利率 = (基準現金股利 / 最新股價) * 100%`。
* **排序邏輯**：當日符合目標報酬率 (預設 X%) 的股票，醒目顯示並置頂。

### C. 異常警示系統 (Alert System)
採用**絕對數值**與**產業分級**判定，防範高殖利率陷阱：
1.  **價格暴跌**：
    * 高波動產業 (如半導體/電子零組件)：單日跌幅 $\ge$ 5%。
    * 中波動產業 (如傳產/塑化)：單日跌幅 $\ge$ 4%。
    * 低波動產業 (如金融/電信)：單日跌幅 $\ge$ 2.5%。
2.  **交易量異常**：當日成交量 $\ge$ 過去20日均量 (月均量) 之 2.5 倍。
3.  **備註說明**：當觸發上述條件，系統自動強制附加醒目的紅色警告備註 (包含具體跌幅或爆量倍數)。

## 4. 資料庫 Schema 概覽 (Database Schema)

* **目前實作狀態**：已建立 SQLite 實體資料庫 `savestock.db`。
* **Users**：`User_ID`, `Email`, `OAuth_Provider`, `UUID` (訪客用)。
* **User_Licenses**：`User_ID`, `Tier_ID`, `Purchase_Date` (處理買斷授權紀錄)。
* **Plan_Configs**：`Tier_ID`, `Tier_Name`, `Max_Total_Stocks` (方案設定表)。
* **Stock_Master**：`Stock_ID`, `Name`, `Sector`, `Avg_Dividend_2Y`, `Last_Updated`。
* **User_Stocks**：`User_ID`, `Stock_ID`, `Status`, `Is_Default`。
* **Daily_Prices**：`Stock_ID`, `Date`, `Close_Price`, `Volume`, `Alert_Flag`, `Alert_Reason`。

## 5. 功能開發進度與修正紀錄 (Development Progress)

> 最後更新：2026-06-04

### 已完成 (Done)
- [x] **資料庫架構**：完成 SQLite 相容 Schema 轉換與實體初始化。
- [x] **ETL 邏輯修復**：修正 `yfinance` 欄位缺失與時區問題，成功抓取預設股票資料。
- [x] **環境設定**：建立 `.env` 檔案與資料庫連線字串。
- [x] **預設股票清單擴充**：從 10 檔擴充至 14 檔，新增電信（2412、3045）與食品（1216、1210）兩大產業。
- [x] **ETL 產業別警示閾值**：廢除統一 2.5% 閾值，改為依產業查表（詳見下方警示閾值表）。
- [x] **API 端點實作**：FastAPI 完成 7 支 RESTful 端點，含股票列表、詳情、歷史價格、用戶建立、自選清單 CRUD。
- [x] **Flutter 首頁**：完成響應式首頁，支援手機直／橫式與平板雙欄佈局，含產業篩選與警示顯示。

### 進行中 (WIP)

- [ ] **Flutter 首頁驗收**：程式碼完成，等待裝置實際確認畫面正常。
- [ ] **Flutter 詳情頁、自選清單頁、加入股票頁**：尚未開始。

## 6. 系統流程圖 (System Flow)


1.  **ETL 流程 (後端批次)**：每日台股收盤後執行 Python Pandas 腳本 -> 抓取證交所資料 -> 計算 2 年平均報酬率 -> 判定異常警示 -> 寫入資料庫/Redis。
2.  **通知流程 (非同步)**：判定完成後 -> 檢查 `User_Preferences` -> 透過 Message Queue 背景發送 FCM 推播或 Email。
3.  **前端流程 (Flutter UI)**：使用者開啟 App -> 驗證授權等級 (Tier) -> 讀取快取/自選清單 -> 渲染跨平台 UI (置頂達標股票、顯示紅色異常備註)。

## 6. 實驗性功能 (Experimental / Internal)
* **績效回測模組**：計算「若遵循系統的絕對數值警示過濾，過去 X 年可避開之跌幅成效」。*(內部測試評估中，暫不放入正式 UI)*

***

