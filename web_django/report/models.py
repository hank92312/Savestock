"""對應 Neon 既有資料表的唯讀模型（managed=False，不產生 migration）。

欄位名用小寫 db_column：Postgres 對 unquoted DDL 會 fold 成小寫，而 Django ORM
會替識別字加引號，故必須給實際的小寫名稱才對得上（SQLite 大小寫不敏感亦相容）。
"""

from django.db import models


class StockMaster(models.Model):
    stock_id = models.CharField(
        max_length=20, primary_key=True, db_column="stock_id"
    )
    name = models.CharField(max_length=100, db_column="name")
    sector = models.CharField(max_length=50, null=True, db_column="sector")
    avg_dividend_2y = models.FloatField(null=True, db_column="avg_dividend_2y")
    avg_dividend_5y = models.FloatField(null=True, db_column="avg_dividend_5y")
    dividend_1y = models.FloatField(null=True, db_column="dividend_1y")
    listing_months = models.IntegerField(null=True, db_column="listing_months")

    class Meta:
        managed = False
        db_table = "stock_master"
        verbose_name = "股票主檔"
        verbose_name_plural = "股票主檔"

    def __str__(self):
        return f"{self.name}（{self.stock_id}）"


class Dividend(models.Model):
    # Dividends 表為複合鍵（stock_id + ex_date），用 Django 5.2+ 的 CompositePrimaryKey
    pk = models.CompositePrimaryKey("stock_id", "ex_date")
    stock_id = models.CharField(max_length=20, db_column="stock_id")
    ex_date = models.DateField(db_column="ex_date")
    cash_dividend = models.FloatField(default=0, db_column="cash_dividend")
    stock_dividend = models.FloatField(default=0, db_column="stock_dividend")

    class Meta:
        managed = False
        db_table = "dividends"
        verbose_name = "股利紀錄"
        verbose_name_plural = "股利紀錄"
        ordering = ["-ex_date"]

    @property
    def total(self) -> float:
        return round((self.cash_dividend or 0) + (self.stock_dividend or 0), 4)

    def __str__(self):
        return f"{self.stock_id} {self.ex_date} 配 {self.total}"


class DailyPrice(models.Model):
    """每日收盤價（唯讀）；ETF 成分股頁用來取「最新收盤價」。"""
    pk = models.CompositePrimaryKey("stock_id", "date")
    stock_id = models.CharField(max_length=20, db_column="stock_id")
    date = models.DateField(db_column="date")
    close_price = models.FloatField(db_column="close_price")
    volume = models.BigIntegerField(null=True, db_column="volume")

    class Meta:
        managed = False
        db_table = "daily_prices"
        ordering = ["-date"]


# ── ETF 追蹤模組（etf_tracker）唯讀模型 ─────────────────────────────
class EtfMaster(models.Model):
    etf_id = models.CharField(max_length=20, primary_key=True, db_column="etf_id")
    name = models.CharField(max_length=100, db_column="name")
    category = models.CharField(max_length=20, null=True, db_column="category")
    is_custom = models.BooleanField(default=False, db_column="is_custom")
    owner_user_id = models.IntegerField(null=True, db_column="owner_user_id")

    class Meta:
        managed = False
        db_table = "etf_master"
        verbose_name = "ETF 主檔"
        verbose_name_plural = "ETF 主檔"

    def __str__(self):
        return f"{self.name}（{self.etf_id}）"


class EtfHolding(models.Model):
    """ETF 成分股當前快照（唯讀）。"""
    pk = models.CompositePrimaryKey("etf_id", "stock_id")
    etf_id = models.CharField(max_length=20, db_column="etf_id")
    stock_id = models.CharField(max_length=20, db_column="stock_id")
    stock_name = models.CharField(max_length=100, null=True, db_column="stock_name")
    weight = models.FloatField(null=True, db_column="weight")
    snapshot_date = models.DateField(null=True, db_column="snapshot_date")

    class Meta:
        managed = False
        db_table = "etf_holdings"
        ordering = ["-weight"]


class EtfHoldingHistory(models.Model):
    """ETF 成分股歷史權重（唯讀）；供近 N 天權重趨勢折線圖。"""
    pk = models.CompositePrimaryKey("etf_id", "stock_id", "date")
    etf_id = models.CharField(max_length=20, db_column="etf_id")
    stock_id = models.CharField(max_length=20, db_column="stock_id")
    date = models.DateField(db_column="date")
    weight = models.FloatField(null=True, db_column="weight")

    class Meta:
        managed = False
        db_table = "etf_holding_history"
        ordering = ["date"]
