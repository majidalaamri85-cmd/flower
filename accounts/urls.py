from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),

    path('categories/', views.expense_category_list, name='expense_category_list'),
    path('categories/<int:pk>/edit/', views.expense_category_edit, name='expense_category_edit'),

    path('category/<int:category_id>/details/', views.get_category_details, name='get_category_details'),
    path('statistics/', views.get_expense_statistics, name='expense_statistics'),

    # Backward-compatible route
    path('expenses/category/', views.expense_category_list, name='expense_category_list_legacy'),
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_create, name='user_create'),
]