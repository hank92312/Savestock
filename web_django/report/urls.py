from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("report", views.report, name="report"),
]
