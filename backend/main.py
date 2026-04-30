from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Savestock API", version="1.0.0")

# 設定 CORS (方便 Flutter 前端呼叫)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生產環境應限制來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Savestock API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": os.getlogin()}

# 預計開發的端點預留
# @app.get("/stocks/default")
# async def get_default_stocks():
#     pass

# @app.get("/stocks/{stock_id}/price")
# async def get_stock_price(stock_id: str):
#     pass
