# 以 repo root 為 build context（保留 backend/ 與 etl/ 同層關係，
# 才能讓 routers/etf.py 的相對路徑找到 etl/fetch_etf.py）。
# 對應建置指令：docker build -f backend/Dockerfile .
FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴（psycopg2 需要）
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend /app/backend
COPY etl /app/etl

WORKDIR /app/backend

# Cloud Run 使用 PORT 環境變數
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
