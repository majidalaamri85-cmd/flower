from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('daily/', views.daily_report, name='daily'),
    path('monthly/', views.monthly_report, name='monthly'),
    path('sales-analytics/', views.sales_analytics, name='sales_analytics'),
    path('profit-loss/', views.profit_loss, name='profit_loss'),
]