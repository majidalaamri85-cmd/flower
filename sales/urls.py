from django.urls import path

from . import views
from . import views_offline

app_name = 'sales'

urlpatterns = [
    path('pos/', views.pos, name='pos'),
    path('pos-offline/', views.pos_offline, name='pos_offline'),
    path('search-product/', views.search_product, name='search_product'),
    path('search-by-barcode/', views.search_by_barcode, name='search_by_barcode'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoice/<str:invoice_number>/', views.invoice_detail, name='invoice_detail'),
    path('invoice/<str:invoice_number>/delete/', views.invoice_delete, name='invoice_delete'),
    path('invoice/<str:invoice_number>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.customer_create, name='customer_create'),
    path('bundles/', views.bundle_list, name='bundle_list'),
    path('bundles/add/', views.bundle_create, name='bundle_create'),
    path('offline-data/', views_offline.get_offline_data, name='offline_data'),
    path('sync-offline/', views_offline.sync_offline_sales, name='sync_offline_sales'),
]
