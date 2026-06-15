"""Django Admin：股利資料管理（唯讀，避免誤改正式資料）。

註：Dividends 為複合主鍵表，Django Admin 不支援複合主鍵模型註冊，
故僅將 Stock_Master 納入 Admin；個股配息明細於報表頁呈現。
"""

from django.contrib import admin

from .models import StockMaster


@admin.register(StockMaster)
class StockMasterAdmin(admin.ModelAdmin):
    list_display = (
        "stock_id", "name", "sector",
        "dividend_1y", "avg_dividend_5y", "listing_months",
    )
    search_fields = ("stock_id", "name")
    list_filter = ("sector",)
    ordering = ("stock_id",)

    # 正式股利資料由 ETL / API 維護，Admin 僅供檢視
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
