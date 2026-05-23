from django.urls import path

from . import views

app_name = 'inventory'

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('products/<int:pk>/stock-adjust/', views.stock_adjust, name='stock_adjust'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_create, name='supplier_create'),
    path('stock-movements/', views.stock_movements, name='stock_movements'),
    path('low-stock/', views.low_stock_alert, name='low_stock'),
    path('expiring-flowers/', views.expiring_flowers, name='expiring_flowers'),
]