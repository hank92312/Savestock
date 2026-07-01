"""模板共用變數：讓每個頁面的頂部切換列都能取得存股 App 網址。"""
from django.conf import settings


def nav_urls(request):
    return {"STOCK_APP_URL": settings.STOCK_APP_URL}
