from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("report", views.report, name="report"),
    path("etf", views.etf_dashboard, name="etf_dashboard"),
    path("etf/analytics", views.etf_analytics, name="etf_analytics"),
    path("etf/add", views.etf_add, name="etf_add"),
    path("etf/<str:etf_id>/delete", views.etf_delete, name="etf_delete"),
    path("etf/<str:etf_id>", views.etf_holdings, name="etf_holdings"),
]
