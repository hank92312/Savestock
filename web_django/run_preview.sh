#!/usr/bin/env bash
# 本地預覽 ETF 頁面（讀 G2 測試 SQLite）
cd /media/halk/DATA/savestock/web_django
export DJANGO_SETTINGS_MODULE=savestock_report.settings
export DJANGO_DEBUG=true
export SQLITE_PATH=/tmp/claude-1000/-home-halk---/8f4400fa-27a6-4f8d-97a6-4857bebaaa46/scratchpad/g2test.db
exec python3 manage.py runserver 127.0.0.1:8010 --noreload
