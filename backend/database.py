import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

DEFAULT_DB = "sqlite:///c:/Savestock/savestock.db"
DB_URL = os.getenv("DATABASE_URL", DEFAULT_DB)

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

def get_db():
    with engine.begin() as conn:
        yield conn
