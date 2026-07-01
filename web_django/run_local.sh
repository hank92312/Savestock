#!/usr/bin/env bash
# 本地驗收：以 savestock_local.db（已抓齊 16 檔 ETF）啟動 Django ETF 平台
cd /media/halk/DATA/savestock/web_django
export DJANGO_SETTINGS_MODULE=savestock_report.settings
export DJANGO_DEBUG=true
export SQLITE_PATH=/media/halk/DATA/savestock/savestock_local.db
# 本機互跳：讓「存股追蹤」按鈕指向本機 flutter run 開發伺服器（預設埠 5000）
export STOCK_APP_URL=http://localhost:5000
exec python3 manage.py runserver 127.0.0.1:8010 --noreload
