from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_wallet, name='wallet-detail'),
    path('deposit/', views.deposit, name='wallet-deposit'),
    path('withdraw/', views.withdraw, name='wallet-withdraw'),
    path('balance/', views.balance, name='wallet-balance'),
    path('transactions/', views.transaction_history, name='wallet-transactions'),
]