"""Savestock 報表服務 Django 設定。

此服務是 Savestock 的「網頁報表」面：伺服器端渲染可分享／可列印的年度股利報表，
並提供 Django Admin 管理股利資料。計算邏輯 import 自 backend/core（與 FastAPI 共用）。
"""

import os
import sys
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent  # web_django/

# 讓 Django 能 import 共用的純計算模組 core（位於 backend/，與 FastAPI 共用同一份口徑）
_BACKEND_DIR = BASE_DIR.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# 讓 Django 能 import ETL 的 ETF 來源層與名稱解析（新增自訂 ETF 時共用同一份抓取邏輯）
_ETL_DIR = BASE_DIR.parent / "etl"
if str(_ETL_DIR) not in sys.path:
    sys.path.insert(0, str(_ETL_DIR))

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-change-in-prod")

# 「存股追蹤」Flutter App 網址（頂部切換列用）；正式站預設 Netlify，本地開發可用環境變數覆蓋
STOCK_APP_URL = os.environ.get("STOCK_APP_URL", "https://savestock.netlify.app")
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "report",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # 在 Cloud Run 上服務 admin 靜態檔
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "savestock_report.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "report.context_processors.nav_urls",
            ],
        },
    },
]

WSGI_APPLICATION = "savestock_report.wsgi.application"

# ── 資料庫：與 backend/database.py 同邏輯，依 DATABASE_URL 前綴切換 ──
_DB_URL = os.environ.get("DATABASE_URL", "").strip()
if _DB_URL.startswith("postgres"):
    # 去掉 SQLAlchemy 專用的 +psycopg2，Django 用標準 postgres scheme
    _DB_URL = _DB_URL.replace("+psycopg2", "")
    DATABASES = {
        "default": dj_database_url.parse(
            _DB_URL, conn_max_age=600, ssl_require=True
        )
    }
else:
    # 本機開發：讀同一個 SQLite 開發庫（含 Stock_Master / Dividends）
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("SQLITE_PATH", r"C:\Savestock\savestock.db"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "zh-hant"
TIME_ZONE = "Asia/Taipei"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
