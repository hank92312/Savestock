# 專案開發環境建置指南 (Development Setup Guide)

本指南旨在協助開發者在全新的裝置上快速建置 `Savestock` 的開發環境，並順利運行後端與資料處理任務。

## 1. 系統需求 (System Requirements)
- **Git**: 用於版本控制與同步程式碼。
- **Python**: 建議版本 3.10 或以上 (用於 Backend 與 ETL)。
- **Flutter SDK**: 用於 Frontend 跨平台開發 (若需開發前端)。
- **VS Code** (或其他 IDE): 建議安裝 Python, Flutter 等相關擴充套件。

## 2. 專案克隆與環境初始化 (Clone & Init)

### 2.1 取得專案程式碼
```bash
git clone https://github.com/hank92312/Savestock.git
cd Savestock
```

### 2.2 設定環境變數 (.env)
專案根目錄下有一個 `.env.example`，請將其複製並重新命名為 `.env`：
```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```
請根據開發環境需求，調整 `.env` 內的配置 (如資料庫路徑等)。

## 3. 後端與資料處理環境建置 (Python Backend & ETL)

### 3.1 建立並啟動虛擬環境 (Virtual Environment)
在專案根目錄下執行：
```bash
# 建立虛擬環境 (資料夾名稱為 .venv)
python -m venv .venv

# 啟動虛擬環境 (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 啟動虛擬環境 (macOS / Linux)
source .venv/bin/activate
```

### 3.2 安裝相依套件 (Dependencies)
*(備註：請確認專案中是否有 `requirements.txt`，如果尚未產生，請開發者後續補上並執行以下指令)*
```bash
pip install -r requirements.txt
```
> 目前專案主要依賴：`fastapi`, `uvicorn`, `yfinance`, `pandas`, `requests` 等。

### 3.3 初始化資料庫 (Database Initialization)
由於 `*.db` 檔案已加入 `.gitignore`，新環境需要重新產生 SQLite 資料庫。
1. 確保已啟動虛擬環境。
2. 執行初始化腳本 (依照實際資料夾結構，可能有類似 `python database/init_db.py` 的指令)。
3. 確認專案根目錄產生了 `savestock.db`。

## 4. 前端環境建置 (Flutter Frontend)
1. 進入 `frontend` 資料夾 (若已建立)：
   ```bash
   cd frontend
   flutter pub get
   ```
2. 透過模擬器或實體手機測試：
   ```bash
   flutter run
   ```

## 5. 開發工作流程 (Workflow)
- **ETL 腳本測試**：透過執行 `python etl/xxx.py` 來驗證每日盤後資料的抓取與更新邏輯。
- **API 伺服器啟動**：透過 `uvicorn backend.main:app --reload` (假設入口為 backend/main.py) 來啟動本機 API 測試。
- **分支與提交**：建議採用 Feature Branch 流程，開發完成後合併回 `main` 分支。
