from django.urls import path
from . import views

urlpatterns = [
    # Loan management
    path('', views.create_loan, name='create-loan'),
    path('available/', views.available_loans, name='available-loans'),
    path('my-loans/', views.my_loans, name='my-loans'),
    path('<int:loan_id>/', views.loan_detail, name='loan-detail'),

    # Offer management
    path('<int:loan_id>/offer/', views.create_offer, name='create-offer'),
    path('<int:loan_id>/accept-offer/', views.accept_offer, name='accept-offer'),

    # Funding and payments
    path('<int:loan_id>/fund/', views.fund_loan, name='fund-loan'),
    path('<int:loan_id>/pay/', views.make_payment, name='make-payment'),
    path('<int:loan_id>/schedule/', views.payment_schedule, name='payment-schedule'),

    # Payment management
    path('pending-payments/', views.pending_payments, name='pending-payments'),
]