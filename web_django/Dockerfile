# 以 repo root 為 build context（才能納入與 FastAPI 共用的 backend/core）。
# 對應 cloudbuild.yaml：docker build -f web_django/Dockerfile .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=savestock_report.settings

WORKDIR /app

COPY web_django/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 共用純計算模組（與 backend/core/dividend_calc.py 同一份）
COPY backend/core /app/core
COPY web_django /app

# 預先收集 admin 等靜態檔（whitenoise 服務），不需 DB
RUN python manage.py collectstatic --noinput

# Cloud Run 透過 $PORT 注入埠號
CMD exec gunicorn savestock_report.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
