from typing import Optional, List
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Loan, Offer, Payment

User = get_user_model()


class LoanRepository:
    @staticmethod
    def create_loan(borrower: User, **kwargs) -> Loan:
        loan = Loan.objects.create(borrower=borrower, **kwargs)
        return loan

    @staticmethod
    def get_loan_by_id(loan_id: int) -> Optional[Loan]:
        try:
            return Loan.objects.select_related('borrower', 'lender').prefetch_related('offers', 'payments').get(id=loan_id)
        except Loan.DoesNotExist:
            return None

    @staticmethod
    def get_available_loans() -> List[Loan]:
        return Loan.objects.filter(status='REQUESTED').select_related('borrower').order_by('-created_at')

    @staticmethod
    def get_loans_by_borrower(borrower: User) -> List[Loan]:
        return Loan.objects.filter(borrower=borrower).select_related('lender').prefetch_related('offers', 'payments').order_by('-created_at')

    @staticmethod
    def get_loans_by_lender(lender: User) -> List[Loan]:
        return Loan.objects.filter(lender=lender).select_related('borrower').prefetch_related('payments').order_by('-created_at')

    @staticmethod
    def update_loan(loan: Loan, **kwargs) -> Loan:
        for field, value in kwargs.items():
            setattr(loan, field, value)
        loan.save()
        return loan

    @staticmethod
    def get_loans_by_status(status: str) -> List[Loan]:
        return Loan.objects.filter(status=status).select_related('borrower', 'lender').order_by('-created_at')


class OfferRepository:
    @staticmethod
    def create_offer(loan: Loan, lender: User, annual_interest_rate) -> Offer:
        offer = Offer.objects.create(
            loan=loan,
            lender=lender,
            annual_interest_rate=annual_interest_rate
        )
        return offer

    @staticmethod
    def get_offer_by_id(offer_id: int) -> Optional[Offer]:
        try:
            return Offer.objects.select_related('loan', 'lender').get(id=offer_id)
        except Offer.DoesNotExist:
            return None

    @staticmethod
    def get_offers_for_loan(loan: Loan) -> List[Offer]:
        return Offer.objects.filter(loan=loan).select_related('lender').order_by('annual_interest_rate')

    @staticmethod
    def get_offers_by_lender(lender: User) -> List[Offer]:
        return Offer.objects.filter(lender=lender).select_related('loan', 'loan__borrower').order_by('-created_at')

    @staticmethod
    def accept_offer(offer: Offer) -> Offer:
        offer.accepted = True
        offer.save()
        return offer

    @staticmethod
    def check_existing_offer(loan: Loan, lender: User) -> bool:
        return Offer.objects.filter(loan=loan, lender=lender).exists()


class PaymentRepository:
    @staticmethod
    def create_payment(loan: Loan, **kwargs) -> Payment:
        payment = Payment.objects.create(loan=loan, **kwargs)
        return payment

    @staticmethod
    def get_payment_by_id(payment_id: int) -> Optional[Payment]:
        try:
            return Payment.objects.select_related('loan').get(id=payment_id)
        except Payment.DoesNotExist:
            return None

    @staticmethod
    def get_payments_for_loan(loan: Loan) -> List[Payment]:
        return Payment.objects.filter(loan=loan).order_by('payment_number')

    @staticmethod
    def get_next_pending_payment(loan: Loan) -> Optional[Payment]:
        return Payment.objects.filter(loan=loan, status='PENDING').order_by('payment_number').first()

    @staticmethod
    def get_pending_payments_by_borrower(borrower: User) -> List[Payment]:
        return Payment.objects.filter(
            loan__borrower=borrower,
            status='PENDING'
        ).select_related('loan').order_by('due_date')

    @staticmethod
    def get_overdue_payments() -> List[Payment]:
        from datetime import date
        return Payment.objects.filter(
            status='PENDING',
            due_date__lt=date.today()
        ).select_related('loan', 'loan__borrower')

    @staticmethod
    def mark_payment_as_paid(payment: Payment) -> Payment:
        payment.mark_as_paid()
        return payment

    @staticmethod
    def get_all_payments_for_loan_status(loan: Loan) -> dict:
        payments = Payment.objects.filter(loan=loan)
        total_payments = payments.count()
        paid_payments = payments.filter(status='PAID').count()
        return {
            'total': total_payments,
            'paid': paid_payments,
            'remaining': total_payments - paid_payments,
            'all_paid': paid_payments == total_payments and total_payments > 0
        }