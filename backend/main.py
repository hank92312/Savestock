from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from routers.stocks import router as stocks_router
from routers.users import router as users_router
from routers.portfolio import router as portfolio_router
from routers.etf import router as etf_router

app = FastAPI(title="Savestock API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://savestock.netlify.app",
        "https://hank92312.github.io",
    ],
    allow_origin_regex=r"http://localhost(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.include_router(stocks_router)
app.include_router(users_router)
app.include_router(portfolio_router)
app.include_router(etf_router)


@app.get("/")
def root():
    return {"message": "Welcome to Savestock API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
