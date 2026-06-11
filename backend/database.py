import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

DEFAULT_DB = "sqlite:///c:/Savestock/savestock.db"
DB_URL = os.getenv("DATABASE_URL", DEFAULT_DB).strip()

# SQLite 需要 check_same_thread=False；PostgreSQL 不需要
if DB_URL.startswith("sqlite"):
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
else:
    # Neon 免費方案會關閉閒置連線，pool_pre_ping 在借出連線前先驗證，避免拿到死連線
    engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=300)

def get_db():
    with engine.begin() as conn:
        yield conn
